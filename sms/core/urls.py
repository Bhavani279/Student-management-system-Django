from django.contrib.auth import views as auth
from django.urls import path, reverse_lazy

from . import views as v

urlpatterns = [
    # auth
    path("login/", auth.LoginView.as_view(redirect_authenticated_user=True), name="login"),
    path("logout/", auth.LogoutView.as_view(), name="logout"),
    path("password/change/", v.ForcedPasswordChangeView.as_view(
        template_name="registration/auth_form.html", extra_context={"title": "Change password"}),
        name="password_change"),
    path("password/reset/", auth.PasswordResetView.as_view(
        template_name="registration/auth_form.html", extra_context={"title": "Reset password"},
        success_url=reverse_lazy("password_reset_done")), name="password_reset"),
    path("password/reset/sent/", auth.PasswordResetDoneView.as_view(
        template_name="registration/auth_message.html",
        extra_context={"title": "Check your e-mail", "text": "If that address belongs to an account, a reset link has been sent."}),
        name="password_reset_done"),
    path("password/reset/<uidb64>/<token>/", auth.PasswordResetConfirmView.as_view(
        template_name="registration/auth_form.html", extra_context={"title": "Choose a new password"},
        success_url=reverse_lazy("password_reset_complete")), name="password_reset_confirm"),
    path("password/reset/done/", auth.PasswordResetCompleteView.as_view(
        template_name="registration/auth_message.html",
        extra_context={"title": "Password changed", "text": "You can now log in with your new password."}),
        name="password_reset_complete"),

    path("", v.dashboard, name="dashboard"),

    # people
    path("admins/", v.AdminList.as_view(), name="admin_list"),
    path("admins/add/", v.AdminAdd.as_view(), name="admin_add"),
    path("admins/<int:pk>/edit/", v.AdminEdit.as_view(), name="admin_edit"),
    path("admins/<int:pk>/delete/", v.AdminDelete.as_view(), name="admin_delete"),

    path("faculty/", v.FacultyList.as_view(), name="faculty_list"),
    path("faculty/add/", v.FacultyAdd.as_view(), name="faculty_add"),
    path("faculty/<int:pk>/edit/", v.FacultyEdit.as_view(), name="faculty_edit"),
    path("faculty/<int:pk>/delete/", v.FacultyDelete.as_view(), name="faculty_delete"),

    path("students/", v.StudentList.as_view(), name="student_list"),
    path("students/add/", v.StudentAdd.as_view(), name="student_add"),
    path("students/<int:pk>/", v.student_detail, name="student_detail"),
    path("students/<int:pk>/edit/", v.StudentEdit.as_view(), name="student_edit"),
    path("students/<int:pk>/delete/", v.StudentDelete.as_view(), name="student_delete"),
    path("profile/", v.student_detail, name="my_profile"),

    # fees
    path("fees/structure/", v.fee_structure, name="fee_structure"),
    path("fees/due/", v.fees_due, name="fees_due"),
    path("fees/student/<int:pk>/", v.fees_view, name="fees_student"),
    path("fees/mine/", v.fees_view, name="my_fees"),
    path("fees/receipt/<int:pk>/", v.receipt, name="receipt"),

    # attendance
    path("attendance/mark/", v.attendance_mark, name="attendance_mark"),
    path("attendance/claim/", v.class_claim, name="class_claim"),
    path("attendance/report/", v.attendance_report, name="attendance_report"),
    path("attendance/mine/", v.attendance_mine, name="attendance_mine"),

    # marks
    path("marks/", v.marks_home, name="marks_home"),
    path("marks/<int:exam_id>/<int:subject_id>/", v.marks_entry, name="marks_entry"),
    path("results/", v.results, name="results"),

    # notices
    path("notices/", v.notice_list, name="notice_list"),
    path("notices/add/", v.notice_add, name="notice_add"),
    path("notices/<int:pk>/delete/", v.notice_delete, name="notice_delete"),
]
