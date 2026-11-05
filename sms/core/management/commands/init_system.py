from datetime import date, timedelta
import random

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import (Attendance, Exam, Faculty, FeePayment, FeeStructure, Notice, Student, Subject, User)


class Command(BaseCommand):
    help = "Create the Super Admin account and the default fee years. Use --demo to add sample data."

    def add_arguments(self, parser):
        parser.add_argument("--username", default="admin")
        parser.add_argument("--password", default="ChangeMe@123")
        parser.add_argument("--demo", action="store_true", help="Add sample faculty, students, attendance, fees")

    def handle(self, *args, **o):
        if not User.objects.filter(username=o["username"]).exists():
            User.objects.create_superuser(o["username"], "", o["password"], first_name="Super", last_name="Admin")
            self.stdout.write(self.style.SUCCESS(f"Super Admin '{o['username']}' created. Change the password after login."))
        year = timezone.localdate().year
        for y, fee in ((year - 1, 1500), (year, 1800), (year + 1, 2000)):
            FeeStructure.objects.get_or_create(year=y, defaults={"monthly": fee})
        if o["demo"]:
            self.demo(year)

    def demo(self, year):
        random.seed(1)
        if Student.objects.exists():
            self.stdout.write("Demo skipped: students already exist.")
            return
        pw = "Demo@12345"
        ft = []
        for i, (fn, ln, sub) in enumerate([("Anita", "Rao", "Maths"), ("Ravi", "Kumar", "Science")]):
            u = User(role="faculty", first_name=fn, last_name=ln, phone="9000000%03d" % i, gender="Female" if i == 0 else "Male")
            u.set_password(pw)
            u.save()
            ft.append(Faculty.objects.create(user=u, dob=date(1988, 5, 1), subject=sub, qualification="M.Sc, B.Ed",
                                             experience=6 + i, doj=date(2018, 6, 1)))
        names = [("Arjun", "Reddy"), ("Sneha", "Varma"), ("Kiran", "Babu"), ("Divya", "Naidu"), ("Rahul", "Sharma"), ("Meena", "Iyer")]
        students = []
        for n, (fn, ln) in enumerate(names):
            u = User(role="student", first_name=fn, last_name=ln, phone="9100000%03d" % n, gender="Female" if n % 2 else "Male")
            u.set_password(pw)
            u.save()
            students.append(Student.objects.create(user=u, roll_no=n % 3 + 1, std=8 + n // 3, division="A", dob=date(2012, 1, 10 + n),
                                                   father_name=f"Mr. {ln}", mother_name=f"Mrs. {ln}"))
        from core.models import ClassSection
        sec = ClassSection.objects.get(std=8, division="A")
        sec.class_teacher = ft[0]
        sec.save()
        today = timezone.localdate()
        days = [today - timedelta(days=d) for d in range(1, 30) if (today - timedelta(days=d)).weekday() < 5]
        for s in students:
            for d in days:
                Attendance.objects.create(student=s, date=d, present=random.random() > 0.12)
            for m in range(1, today.month):
                FeePayment.objects.create(student=s, year=year, month=m, amount=1800)
        for std in (8, 9):
            for name in ("Maths", "Science", "English"):
                Subject.objects.create(name=name, std=std)
            Exam.objects.create(name="Unit Test 1", std=std, date=today)
        Notice.objects.create(title="Welcome to EduManage", body="This is the new web-based student management system.", audience="all")
        self.stdout.write(self.style.SUCCESS(f"Demo data added. Faculty/student logins use password {pw}"))
