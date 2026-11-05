from django import forms
from django.db import transaction
from django.utils.crypto import get_random_string

from .models import (Exam, Faculty, FeeStructure, Notice, Student, Subject, User, phone_validator)

USER_FIELDS = ["first_name", "last_name", "email", "phone", "address", "gender"]


class BootstrapMixin:
    """Adds Bootstrap classes to every widget."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            w = field.widget
            if isinstance(w, forms.CheckboxInput):
                w.attrs["class"] = "form-check-input"
            elif isinstance(w, forms.Select):
                w.attrs["class"] = "form-select"
            else:
                w.attrs["class"] = "form-control"


def date_widget():
    return forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")


class AccountForm(BootstrapMixin, forms.ModelForm):
    """ModelForm that also creates/updates the linked login account.

    A random first password is generated for new accounts and exposed as
    `generated_password` so the view can show it once.
    """
    ROLE = None
    first_name = forms.CharField(max_length=45)
    last_name = forms.CharField(max_length=45)
    email = forms.EmailField(required=False)
    phone = forms.CharField(max_length=15, validators=[phone_validator])
    address = forms.CharField(widget=forms.Textarea(attrs={"rows": 2}))
    gender = forms.ChoiceField(choices=[("", "---------")] + User.GENDERS)
    generated_password = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        profile_user = self._profile_user()
        if profile_user:
            for f in USER_FIELDS:
                self.fields[f].initial = getattr(profile_user, f)

    def _profile_user(self):
        return self.instance.user if self.instance.pk else None

    def _build_user(self):
        user = self._profile_user()
        if user is None:
            user = User(role=self.ROLE, must_change_password=True)
            self.generated_password = get_random_string(10)
            user.set_password(self.generated_password)
        for f in USER_FIELDS:
            setattr(user, f, self.cleaned_data[f])
        return user

    @transaction.atomic
    def save(self, commit=True):
        profile = super().save(commit=False)
        user = self._build_user()
        user.save()
        profile.user = user
        profile.save()
        return profile


class FacultyForm(AccountForm):
    ROLE = "faculty"
    field_order = USER_FIELDS[:2] + ["middle_name"] + USER_FIELDS[2:]

    class Meta:
        model = Faculty
        fields = ["middle_name", "dob", "subject", "qualification", "experience", "doj"]
        widgets = {"dob": date_widget(), "doj": date_widget(), "qualification": forms.Textarea(attrs={"rows": 2})}


class StudentForm(AccountForm):
    ROLE = "student"
    field_order = USER_FIELDS[:2] + ["middle_name"] + USER_FIELDS[2:]

    class Meta:
        model = Student
        fields = ["middle_name", "roll_no", "std", "division", "dob", "doa", "blood_group",
                  "father_name", "mother_name", "father_occ", "mother_occ"]
        widgets = {"dob": date_widget(), "doa": date_widget()}

    def clean_division(self):
        return self.cleaned_data["division"].upper()


class AdminUserForm(BootstrapMixin, forms.ModelForm):
    """Super Admin manages Admin accounts (User rows with role=admin)."""
    generated_password = None
    phone = forms.CharField(max_length=15, validators=[phone_validator])

    class Meta:
        model = User
        fields = USER_FIELDS
        widgets = {"address": forms.Textarea(attrs={"rows": 2})}

    def save(self, commit=True):
        user = super().save(commit=False)
        if not user.pk:
            user.role = "admin"
            user.must_change_password = True
            self.generated_password = get_random_string(10)
            user.set_password(self.generated_password)
        user.save()
        return user


class FeeStructureForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = FeeStructure
        fields = ["year", "monthly"]


class NoticeForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Notice
        fields = ["title", "audience", "body"]
        widgets = {"body": forms.Textarea(attrs={"rows": 5})}
