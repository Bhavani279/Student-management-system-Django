from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from . import models

@admin.register(models.User)
class SmsUserAdmin(UserAdmin):
    list_display = ("username", "code", "first_name", "last_name", "role", "is_active")
    list_filter = ("role", "is_active")
    fieldsets = UserAdmin.fieldsets + (
        ("School", {"fields": ("role", "code", "phone", "address", "gender", "must_change_password")}),
    )

for m in (models.Faculty, models.Student, models.ClassSection, models.FeeStructure, models.FeePayment,
          models.Attendance, models.Subject, models.Exam, models.Mark, models.Notice):
    admin.site.register(m)
