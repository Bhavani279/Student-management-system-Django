import calendar
import csv
from collections import defaultdict
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import PasswordChangeView
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .decorators import role_required
from .forms import AdminUserForm, FacultyForm, FeeStructureForm, NoticeForm, StudentForm
from .models import (Attendance, ClassSection, Exam, Faculty, FeePayment, FeeStructure, Mark, Notice,
                     Student, Subject, User)

MONTHS = [calendar.month_abbr[m] for m in range(1, 13)]


def pct(part, total):
    return round(part * 100 / total, 1) if total else 0


def grade(percent):
    for limit, g in ((90, "A+"), (80, "A"), (70, "B"), (60, "C"), (50, "D"), (40, "E")):
        if percent >= limit:
            return g
    return "F"


def notices_for(user, limit=5):
    qs = Notice.objects.all()
    if user.role in ("faculty", "student"):
        qs = qs.filter(audience__in=["all", user.role])
    return qs[:limit]


# ---------------------------------------------------------------- auth
class ForcedPasswordChangeView(PasswordChangeView):
    success_url = reverse_lazy("dashboard")

    def form_valid(self, form):
        response = super().form_valid(form)
        self.request.user.must_change_password = False
        self.request.user.save(update_fields=["must_change_password"])
        messages.success(self.request, "Password updated.")
        return response


# ------------------------------------------------------------- dashboard
@role_required("superadmin", "admin", "faculty", "student")
def dashboard(request):
    user = request.user
    today = timezone.localdate()
    ctx = {"notices": notices_for(user)}

    if user.role in ("superadmin", "admin"):
        year = today.year
        by_month = defaultdict(Decimal)
        for row in FeePayment.objects.filter(year=year).values("month").annotate(t=Sum("amount")):
            by_month[row["month"]] = row["t"]
        per_class = Student.objects.values("std").annotate(n=Count("id")).order_by("std")
        todays = Attendance.objects.filter(date=today)
        ctx.update(
            template="core/dashboard_admin.html",
            students=Student.objects.count(),
            faculty=Faculty.objects.count(),
            sections=ClassSection.objects.count(),
            collected=sum(by_month.values()),
            attendance_today=pct(todays.filter(present=True).count(), todays.count()),
            fee_chart={"labels": MONTHS, "data": [float(by_month[m]) for m in range(1, 13)]},
            class_chart={"labels": [f"Class {r['std']}" for r in per_class], "data": [r["n"] for r in per_class]},
            year=year,
        )
    elif user.role == "faculty":
        sections = ClassSection.objects.filter(class_teacher=user.faculty)
        cards = []
        for s in sections:
            marked = Attendance.objects.filter(student__in=s.students, date=today).exists()
            cards.append({"section": s, "count": s.students.count(), "marked": marked})
        ctx.update(template="core/dashboard_faculty.html", cards=cards)
    else:
        student = user.student
        records = student.attendance_records.all()
        paid = student.payments.filter(year=today.year).count()
        ctx.update(
            template="core/dashboard_student.html", student=student,
            att_pct=pct(records.filter(present=True).count(), records.count()),
            att_total=records.count(), paid=paid, months_due=max(today.month - paid, 0),
        )
    return render(request, ctx.pop("template"), ctx)


# ------------------------------------------------- people: list/create/edit/delete
class RoleMixin(LoginRequiredMixin, UserPassesTestMixin):
    roles = ()

    def test_func(self):
        role = self.request.user.role
        return role in self.roles or (role == "superadmin" and "admin" in self.roles)


class PersonListView(RoleMixin, ListView):
    template_name = "core/person_list.html"
    paginate_by = 15
    title = ""
    key = ""                    # url-name prefix: <key>_add / <key>_edit / <key>_delete / <key>_detail
    headers = ()
    search_fields = ()
    detail = False

    def row(self, obj):
        raise NotImplementedError

    def filter_fields(self):
        return []

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q", "").strip()
        if q:
            cond = Q()
            for f in self.search_fields:
                cond |= Q(**{f"{f}__icontains": q})
            qs = qs.filter(cond)
        return qs

    def get(self, request, *args, **kwargs):
        if request.GET.get("export") == "csv":
            self.object_list = self.get_queryset()
            resp = HttpResponse(content_type="text/csv")
            resp["Content-Disposition"] = f'attachment; filename="{self.key}s.csv"'
            w = csv.writer(resp)
            w.writerow(self.headers)
            for obj in self.object_list:
                w.writerow(self.row(obj))
            return resp
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        params = self.request.GET.copy()
        params.pop("page", None)
        params.pop("export", None)
        ctx.update(
            title=self.title, key=self.key, headers=self.headers, detail=self.detail,
            rows=[{"pk": o.pk, "cells": self.row(o)} for o in ctx["page_obj"]],
            querystring=params.urlencode(), q=self.request.GET.get("q", ""),
            filter_fields=self.filter_fields(),
        )
        return ctx


class AccountCreateView(RoleMixin, CreateView):
    template_name = "core/form_page.html"
    title = ""
    key = ""

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        ctx.update(title=f"Add {self.title}", back=reverse(f"{self.key}_list"))
        return ctx

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request,
                         f"{self.title} created. Login ID: {self.object_user().username}  |  "
                         f"Temporary password: {form.generated_password}  (shown once - share it securely)")
        return redirect(self.get_success_url())

    def object_user(self):
        return getattr(self.object, "user", self.object)

    def get_success_url(self):
        return reverse(f"{self.key}_list")


class AccountUpdateView(RoleMixin, UpdateView):
    template_name = "core/form_page.html"
    title = ""
    key = ""

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        ctx.update(title=f"Edit {self.title}", back=reverse(f"{self.key}_list"))
        return ctx

    def form_valid(self, form):
        form.save()
        messages.success(self.request, f"{self.title} updated.")
        return redirect(reverse(f"{self.key}_list"))


class AccountDeleteView(RoleMixin, DeleteView):
    template_name = "core/confirm_delete.html"
    key = ""

    def form_valid(self, form):
        obj = self.get_object()
        getattr(obj, "user", obj).delete()          # cascades to the profile row
        messages.success(self.request, "Record deleted.")
        return redirect(reverse(f"{self.key}_list"))

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        ctx["back"] = reverse(f"{self.key}_list")
        return ctx


# Admin accounts (Super Admin only)
class AdminList(PersonListView):
    roles = ("superadmin",)
    model = User
    title, key = "Admins", "admin"
    headers = ("ID", "Name", "Phone", "Email")
    search_fields = ("first_name", "last_name", "username", "phone")

    def get_queryset(self):
        return super().get_queryset().filter(role="admin").order_by("code")

    def row(self, u):
        return [u.code, u.get_full_name(), u.phone, u.email]


class AdminAdd(AccountCreateView):
    roles = ("superadmin",)
    model, form_class, title, key = User, AdminUserForm, "Admin", "admin"


class AdminEdit(AccountUpdateView):
    roles = ("superadmin",)
    model, form_class, title, key = User, AdminUserForm, "Admin", "admin"


class AdminDelete(AccountDeleteView):
    roles = ("superadmin",)
    model, key = User, "admin"


# Faculty
class FacultyList(PersonListView):
    roles = ("admin",)
    model = Faculty
    title, key = "Faculty", "faculty"
    headers = ("ID", "Name", "Subject", "Experience (yrs)", "Phone", "Email")
    search_fields = ("user__first_name", "user__last_name", "user__code", "subject")

    def get_queryset(self):
        return super().get_queryset().select_related("user").order_by("user__code")

    def row(self, f):
        return [f.user.code, f.full_name, f.subject, f.experience, f.user.phone, f.user.email]


class FacultyAdd(AccountCreateView):
    roles = ("admin",)
    model, form_class, title, key = Faculty, FacultyForm, "Faculty", "faculty"


class FacultyEdit(AccountUpdateView):
    roles = ("admin",)
    model, form_class, title, key = Faculty, FacultyForm, "Faculty", "faculty"


class FacultyDelete(AccountDeleteView):
    roles = ("admin",)
    model, key = Faculty, "faculty"


# Students
class StudentList(PersonListView):
    roles = ("admin", "faculty")
    model = Student
    title, key, detail = "Students", "student", True
    headers = ("ID", "Name", "Class", "Div", "Roll", "Phone", "Father")
    search_fields = ("user__first_name", "user__last_name", "user__code", "father_name", "roll_no")

    def get_queryset(self):
        qs = super().get_queryset().select_related("user")
        std, div = self.request.GET.get("std"), self.request.GET.get("division")
        if std and std.isdigit():
            qs = qs.filter(std=int(std))
        if div:
            qs = qs.filter(division=div.upper())
        return qs

    def filter_fields(self):
        stds = Student.objects.order_by().values_list("std", flat=True).distinct().order_by("std")
        divs = Student.objects.order_by().values_list("division", flat=True).distinct().order_by("division")
        g = self.request.GET
        return [
            {"name": "std", "label": "Class", "options": list(stds), "current": g.get("std", "")},
            {"name": "division", "label": "Division", "options": list(divs), "current": g.get("division", "")},
        ]

    def row(self, s):
        return [s.user.code, s.full_name, s.std, s.division, s.roll_no, s.user.phone, s.father_name]


class StudentAdd(AccountCreateView):
    roles = ("admin",)
    model, form_class, title, key = Student, StudentForm, "Student", "student"


class StudentEdit(AccountUpdateView):
    roles = ("admin",)
    model, form_class, title, key = Student, StudentForm, "Student", "student"


class StudentDelete(AccountDeleteView):
    roles = ("admin",)
    model, key = Student, "student"


@role_required("admin", "faculty", "student")
def student_detail(request, pk=None):
    if request.user.role == "student":
        student = request.user.student
    else:
        student = get_object_or_404(Student.objects.select_related("user"), pk=pk)
    records = student.attendance_records.all()
    present = records.filter(present=True).count()
    year = timezone.localdate().year
    return render(request, "core/student_detail.html", {
        "s": student, "att_pct": pct(present, records.count()), "att_total": records.count(),
        "paid": student.payments.filter(year=year).count(), "year": year,
    })


# ------------------------------------------------------------------ fees
@role_required("admin", "student")
def fees_view(request, pk=None):
    if request.user.role == "student":
        student = request.user.student
    else:
        if pk is None:
            raise PermissionDenied
        student = get_object_or_404(Student, pk=pk)
    can_pay = request.user.role != "student"
    try:
        year = int(request.GET.get("year", timezone.localdate().year))
    except ValueError:
        year = timezone.localdate().year
    structure = FeeStructure.objects.filter(year=year).first()
    paid = {p.month: p for p in student.payments.filter(year=year)}

    if request.method == "POST" and can_pay:
        if not structure:
            messages.error(request, f"No fee structure set for {year}. Add it under Fee Structure first.")
        else:
            mode = request.POST.get("mode", "Cash")
            months = {int(m) for m in request.POST.getlist("months") if m.isdigit() and 1 <= int(m) <= 12}
            with transaction.atomic():
                for m in sorted(months - set(paid)):
                    FeePayment.objects.create(student=student, year=year, month=m, amount=structure.monthly,
                                              mode=mode, collected_by=request.user)
            messages.success(request, f"Recorded {len(months - set(paid))} payment(s).")
        return redirect(f"{request.path}?year={year}")

    rows = [{"n": m, "name": calendar.month_name[m], "payment": paid.get(m)} for m in range(1, 13)]
    return render(request, "core/fees_student.html", {
        "student": student, "year": year, "structure": structure, "rows": rows, "can_pay": can_pay,
        "paid_total": sum(p.amount for p in paid.values()),
        "due_total": (structure.monthly * (12 - len(paid))) if structure else None,
    })


@role_required("admin", "student")
def receipt(request, pk):
    payment = get_object_or_404(FeePayment.objects.select_related("student__user"), pk=pk)
    if request.user.role == "student" and payment.student.user_id != request.user.id:
        raise PermissionDenied
    return render(request, "core/receipt.html", {"p": payment})


@role_required("admin")
def fee_structure(request):
    form = FeeStructureForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        FeeStructure.objects.update_or_create(year=form.cleaned_data["year"],
                                              defaults={"monthly": form.cleaned_data["monthly"]})
        messages.success(request, "Fee structure saved.")
        return redirect("fee_structure")
    return render(request, "core/fee_structure.html", {"form": form, "items": FeeStructure.objects.all()})


@role_required("admin")
def fees_due(request):
    today = timezone.localdate()
    structure = FeeStructure.objects.filter(year=today.year).first()
    rows = []
    if structure:
        qs = Student.objects.select_related("user").annotate(
            paid=Count("payments", filter=Q(payments__year=today.year)))
        for s in qs:
            due = today.month - s.paid
            if due > 0:
                rows.append({"s": s, "due": due, "amount": due * structure.monthly})
        rows.sort(key=lambda r: -r["due"])
    if request.GET.get("export") == "csv":
        resp = HttpResponse(content_type="text/csv")
        resp["Content-Disposition"] = 'attachment; filename="fees_due.csv"'
        w = csv.writer(resp)
        w.writerow(["ID", "Name", "Class", "Division", "Months due", "Amount due"])
        for r in rows:
            w.writerow([r["s"].user.code, r["s"].full_name, r["s"].std, r["s"].division, r["due"], r["amount"]])
        return resp
    return render(request, "core/fees_due.html", {"rows": rows, "structure": structure, "today": today})


# ------------------------------------------------------------ attendance
def sections_for(user):
    if user.role == "faculty":
        return ClassSection.objects.filter(class_teacher=user.faculty)
    return ClassSection.objects.all()


@role_required("faculty", "admin")
def class_claim(request):
    if request.user.role != "faculty":
        raise PermissionDenied
    free = ClassSection.objects.filter(class_teacher__isnull=True)
    if request.method == "POST":
        sec = free.filter(pk=request.POST.get("section")).first()
        if sec:
            sec.class_teacher = request.user.faculty
            sec.save()
            messages.success(request, f"You are now class teacher of {sec}.")
            return redirect("attendance_mark")
        messages.error(request, "That class already has a teacher.")
    return render(request, "core/class_claim.html", {"free": free, "mine": sections_for(request.user)})


@role_required("faculty", "admin")
def attendance_mark(request):
    sections = sections_for(request.user)
    if not sections.exists():
        messages.info(request, "You are not a class teacher yet. Pick a class to take responsibility for.")
        return redirect("class_claim" if request.user.role == "faculty" else "dashboard")
    raw = request.POST if request.method == "POST" else request.GET
    section = sections.filter(pk=raw.get("section")).first() or sections.first()
    day = parse_date(raw.get("date") or "") or timezone.localdate()
    students = list(section.students.select_related("user"))

    if request.method == "POST":
        if day > timezone.localdate():
            messages.error(request, "You cannot mark attendance for a future date.")
        else:
            with transaction.atomic():
                for s in students:
                    Attendance.objects.update_or_create(
                        student=s, date=day,
                        defaults={"present": f"present_{s.pk}" in request.POST, "marked_by": request.user})
            messages.success(request, f"Attendance saved for {section} on {day:%d %b %Y}.")
        return redirect(f"{request.path}?section={section.pk}&date={day.isoformat()}")

    existing = {a.student_id: a.present for a in Attendance.objects.filter(date=day, student__in=students)}
    rows = [{"s": s, "present": existing.get(s.pk, True)} for s in students]
    return render(request, "core/attendance_mark.html", {
        "sections": sections, "section": section, "day": day, "rows": rows,
        "already": bool(existing), "today": timezone.localdate()})


@role_required("faculty", "admin")
def attendance_report(request):
    sections = sections_for(request.user)
    today = timezone.localdate()
    section = sections.filter(pk=request.GET.get("section")).first() or sections.first()
    start = parse_date(request.GET.get("from") or "") or today.replace(day=1)
    end = parse_date(request.GET.get("to") or "") or today
    rows = []
    if section:
        qs = section.students.select_related("user").annotate(
            total=Count("attendance_records", filter=Q(attendance_records__date__range=(start, end))),
            present=Count("attendance_records", filter=Q(attendance_records__date__range=(start, end),
                                                         attendance_records__present=True)))
        rows = [{"s": s, "total": s.total, "present": s.present, "absent": s.total - s.present,
                 "pct": pct(s.present, s.total)} for s in qs]
    if request.GET.get("export") == "csv" and section:
        resp = HttpResponse(content_type="text/csv")
        resp["Content-Disposition"] = f'attachment; filename="attendance_{section.std}{section.division}.csv"'
        w = csv.writer(resp)
        w.writerow(["ID", "Name", "Roll", "Days", "Present", "Absent", "%"])
        for r in rows:
            w.writerow([r["s"].user.code, r["s"].full_name, r["s"].roll_no, r["total"], r["present"],
                        r["total"] - r["present"], r["pct"]])
        return resp
    return render(request, "core/attendance_report.html", {
        "sections": sections, "section": section, "rows": rows, "start": start, "end": end,
        "low": [r for r in rows if r["total"] and r["pct"] < 75]})


@role_required("student")
def attendance_mine(request):
    student = request.user.student
    records = list(student.attendance_records.all())
    monthly = defaultdict(lambda: [0, 0])
    for r in records:
        key = (r.date.year, r.date.month)
        monthly[key][0] += 1
        monthly[key][1] += int(r.present)
    keys = sorted(monthly)
    present = sum(r.present for r in records)
    return render(request, "core/attendance_mine.html", {
        "records": records[:60], "total": len(records), "present": present, "absent": len(records) - present,
        "pct": pct(present, len(records)),
        "chart": {"labels": [f"{calendar.month_abbr[m]} {y}" for y, m in keys],
                  "data": [pct(monthly[k][1], monthly[k][0]) for k in keys]}})


# ----------------------------------------------------------------- marks
@role_required("faculty", "admin")
def marks_home(request):
    exams = Exam.objects.all()
    items = [{"exam": e, "subjects": Subject.objects.filter(std=e.std)} for e in exams]
    return render(request, "core/marks_home.html", {"items": items})


@role_required("faculty", "admin")
def marks_entry(request, exam_id, subject_id):
    exam = get_object_or_404(Exam, pk=exam_id)
    subject = get_object_or_404(Subject, pk=subject_id, std=exam.std)
    students = list(Student.objects.filter(std=exam.std).select_related("user").order_by("division", "roll_no"))
    existing = {m.student_id: m.obtained for m in Mark.objects.filter(exam=exam, subject=subject)}
    if request.method == "POST":
        errors = 0
        with transaction.atomic():
            for s in students:
                raw = request.POST.get(f"m_{s.pk}", "").strip()
                if raw == "":
                    continue
                try:
                    val = Decimal(raw)
                except InvalidOperation:
                    errors += 1
                    continue
                if not (0 <= val <= exam.max_marks):
                    errors += 1
                    continue
                Mark.objects.update_or_create(exam=exam, student=s, subject=subject, defaults={"obtained": val})
        if errors:
            messages.warning(request, f"{errors} value(s) skipped - marks must be between 0 and {exam.max_marks}.")
        else:
            messages.success(request, "Marks saved.")
        return redirect(request.path)
    rows = [{"s": s, "value": existing.get(s.pk, "")} for s in students]
    return render(request, "core/marks_entry.html", {"exam": exam, "subject": subject, "rows": rows})


@role_required("student")
def results(request):
    student = request.user.student
    blocks = []
    for exam in Exam.objects.filter(std=student.std):
        marks = list(Mark.objects.filter(exam=exam, student=student).select_related("subject"))
        if not marks:
            continue
        total = sum(m.obtained for m in marks)
        maximum = exam.max_marks * len(marks)
        p = pct(float(total), maximum)
        blocks.append({"exam": exam, "marks": marks, "total": total, "max": maximum, "pct": p, "grade": grade(p)})
    return render(request, "core/results.html", {"blocks": blocks, "student": student})


# --------------------------------------------------------------- notices
@role_required("superadmin", "admin", "faculty", "student")
def notice_list(request):
    return render(request, "core/notices.html", {"notices": notices_for(request.user, limit=100)})


@role_required("admin")
def notice_add(request):
    form = NoticeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        n = form.save(commit=False)
        n.created_by = request.user
        n.save()
        messages.success(request, "Notice published.")
        return redirect("notice_list")
    return render(request, "core/form_page.html", {"form": form, "title": "Publish Notice", "back": reverse("notice_list")})


@role_required("admin")
def notice_delete(request, pk):
    notice = get_object_or_404(Notice, pk=pk)
    if request.method == "POST":
        notice.delete()
        messages.success(request, "Notice deleted.")
        return redirect("notice_list")
    return render(request, "core/confirm_delete.html", {"object": notice, "back": reverse("notice_list")})
