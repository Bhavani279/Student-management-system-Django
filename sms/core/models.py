import calendar

from django.contrib.auth.models import AbstractUser
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.utils import timezone

phone_validator = RegexValidator(r"^\d{10,15}$", "Enter 10-15 digits, numbers only.")


class User(AbstractUser):
    class Role(models.TextChoices):
        SUPERADMIN = "superadmin", "Super Admin"
        ADMIN = "admin", "Admin"
        FACULTY = "faculty", "Faculty"
        STUDENT = "student", "Student"

    GENDERS = [("Male", "Male"), ("Female", "Female"), ("Other", "Other")]
    PREFIX = {"superadmin": "SA", "admin": "AD", "faculty": "FT", "student": "ST"}

    role = models.CharField(max_length=12, choices=Role.choices, default=Role.STUDENT)
    code = models.CharField("ID", max_length=12, unique=True, null=True, blank=True)
    phone = models.CharField(max_length=15, blank=True, validators=[phone_validator])
    address = models.TextField(blank=True)
    gender = models.CharField(max_length=10, choices=GENDERS, blank=True)
    must_change_password = models.BooleanField(default=False)

    @classmethod
    def next_code(cls, role):
        prefix = cls.PREFIX[role]
        base = 1000 if role in ("admin", "superadmin") else 10000
        existing = cls.objects.filter(code__startswith=prefix).values_list("code", flat=True)
        nums = [int(c[2:]) for c in existing if c[2:].isdigit()]
        return f"{prefix}{max(nums, default=base - 1) + 1}"

    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.role = self.Role.SUPERADMIN
            self.is_staff = True
        if not self.code:
            self.code = self.next_code(self.role)
        if not self.username:
            self.username = self.code
        super().save(*args, **kwargs)

    @property
    def display_name(self):
        return self.get_full_name() or self.username

    def __str__(self):
        return f"{self.display_name} ({self.code})"


class Person(models.Model):
    """Shared helpers for Faculty and Student profiles."""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    middle_name = models.CharField(max_length=45, blank=True)
    dob = models.DateField("Date of birth")

    class Meta:
        abstract = True

    @property
    def full_name(self):
        parts = [self.user.first_name, self.middle_name, self.user.last_name]
        return " ".join(p for p in parts if p)

    @property
    def age(self):
        today = timezone.localdate()
        return today.year - self.dob.year - ((today.month, today.day) < (self.dob.month, self.dob.day))

    def __str__(self):
        return f"{self.full_name} ({self.user.code})"


class Faculty(Person):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="faculty")
    subject = models.CharField(max_length=255)
    qualification = models.TextField()
    experience = models.PositiveIntegerField("Experience (years)", default=0)
    doj = models.DateField("Date of joining")

    class Meta:
        verbose_name_plural = "faculty"


class ClassSection(models.Model):
    std = models.PositiveSmallIntegerField("Class")
    division = models.CharField(max_length=1)
    class_teacher = models.ForeignKey(Faculty, null=True, blank=True, on_delete=models.SET_NULL,
                                      related_name="sections")

    class Meta:
        unique_together = ("std", "division")
        ordering = ["std", "division"]

    def __str__(self):
        return f"Class {self.std}-{self.division}"

    @property
    def students(self):
        return Student.objects.filter(std=self.std, division=self.division).order_by("roll_no")


class Student(Person):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="student")
    roll_no = models.PositiveIntegerField()
    std = models.PositiveSmallIntegerField("Class")
    division = models.CharField(max_length=1)
    father_name = models.CharField(max_length=100)
    mother_name = models.CharField(max_length=100)
    father_occ = models.CharField("Father's occupation", max_length=100, blank=True)
    mother_occ = models.CharField("Mother's occupation", max_length=100, blank=True)
    blood_group = models.CharField(max_length=4, blank=True)
    doa = models.DateField("Date of admission", default=timezone.localdate)

    class Meta:
        unique_together = ("std", "division", "roll_no")
        ordering = ["std", "division", "roll_no"]

    def save(self, *args, **kwargs):
        self.division = self.division.upper()
        super().save(*args, **kwargs)
        ClassSection.objects.get_or_create(std=self.std, division=self.division)

    @property
    def section(self):
        return ClassSection.objects.filter(std=self.std, division=self.division).first()


class FeeStructure(models.Model):
    year = models.PositiveSmallIntegerField(unique=True)
    monthly = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ["-year"]

    @property
    def yearly(self):
        return self.monthly * 12

    def __str__(self):
        return f"{self.year}: {self.monthly}/month"


class FeePayment(models.Model):
    MODES = [("Cash", "Cash"), ("UPI", "UPI"), ("Card", "Card"), ("Bank", "Bank transfer")]
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="payments")
    year = models.PositiveSmallIntegerField()
    month = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(12)])
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    mode = models.CharField(max_length=10, choices=MODES, default="Cash")
    paid_on = models.DateField(default=timezone.localdate)
    receipt_no = models.CharField(max_length=20, blank=True, db_index=True)
    collected_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)

    class Meta:
        unique_together = ("student", "year", "month")
        ordering = ["-year", "-month"]

    @property
    def month_name(self):
        return calendar.month_name[self.month]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.receipt_no:
            self.receipt_no = f"RC{self.pk:06d}"
            super().save(update_fields=["receipt_no"])


class Attendance(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="attendance_records")
    date = models.DateField()
    present = models.BooleanField(default=True)
    marked_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)

    class Meta:
        unique_together = ("student", "date")
        ordering = ["-date"]


class Subject(models.Model):
    name = models.CharField(max_length=60)
    std = models.PositiveSmallIntegerField("Class")

    class Meta:
        unique_together = ("name", "std")
        ordering = ["std", "name"]

    def __str__(self):
        return f"{self.name} (Class {self.std})"


class Exam(models.Model):
    name = models.CharField(max_length=80)
    std = models.PositiveSmallIntegerField("Class")
    date = models.DateField(default=timezone.localdate)
    max_marks = models.PositiveSmallIntegerField(default=100)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.name} - Class {self.std}"


class Mark(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="marks")
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="marks")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    obtained = models.DecimalField(max_digits=6, decimal_places=2)

    class Meta:
        unique_together = ("exam", "student", "subject")


class Notice(models.Model):
    AUDIENCES = [("all", "Everyone"), ("faculty", "Faculty only"), ("student", "Students only")]
    title = models.CharField(max_length=150)
    body = models.TextField()
    audience = models.CharField(max_length=10, choices=AUDIENCES, default="all")
    created_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
