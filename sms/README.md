# EduManage - Student Management System (Django)

Web upgrade of the Tkinter "Student Management System in Python".
Stack: **Python 3.12+, Django 5.2 LTS, MySQL/MariaDB, Bootstrap 5, JavaScript, HTML, CSS, Chart.js**.

## Setup (Windows / XAMPP or any MySQL)

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env          &:: edit DB_* values
```

1. In phpMyAdmin / MySQL create an empty database:
   `CREATE DATABASE students_django CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;`
2. Create tables and the first account:
```bat
python manage.py makemigrations core
python manage.py migrate
python manage.py init_system --username admin --password "ChangeMe@123" --demo
python manage.py runserver
```
3. Open http://127.0.0.1:8000 and log in with `admin` / `ChangeMe@123` (drop `--demo` for a clean database).

Demo logins use password `Demo@12345`; find the IDs (FT10000, ST10000 ...) in the Faculty / Students lists.

**Version notes**
- Django 5.2 needs MySQL 8.0+ or MariaDB 10.5+. If your XAMPP MariaDB is older, either upgrade it or
  run `pip install "Django>=4.2,<5.0"` (the code works on 4.2 LTS).
- If `mysqlclient` fails to install on Windows, use `pip install pymysql` and add these two lines at the top of
  `sms_project/__init__.py`: `import pymysql; pymysql.install_as_MySQLdb()`

## Roles and features

| Role | Can do |
|---|---|
| Super Admin | Everything an Admin can, plus add/edit/delete Admin accounts |
| Admin | Faculty + student CRUD, search/filter/CSV export, fee structure, collect fees, receipts, fees-due report, notices |
| Faculty | View students, claim a class (class teacher), mark/edit attendance, attendance report, enter exam marks |
| Student | Dashboard, profile, attendance history + chart, fee history + receipts, results with grades |

Carried over from the old app: all four logins, auto-generated IDs (AD/FT/ST), class teacher self-assignment,
daily attendance, monthly fee tracking per year, forgot-password.

New: web UI that works on phones, dark mode, dashboards with charts, generated temporary passwords with forced
change on first login, salted PBKDF2 password hashing (old app used plain SHA-256), CSRF protection, role-based
access, search + pagination, CSV exports, printable receipts, low-attendance (<75%) alerts, fee defaulter list,
exam marks + grades, notice board, Django admin site at `/django-admin/` for back-office edits (subjects, exams).

## Project layout
```
sms_project/   settings, root urls
core/models.py        all tables (User, Faculty, Student, ClassSection, FeeStructure, FeePayment,
                      Attendance, Subject, Exam, Mark, Notice)
core/views.py         all screens          core/forms.py   forms (also create the login account)
core/templates/       Bootstrap 5 pages    static/         css + js
core/management/commands/init_system.py   first-run + demo data
```

## Before going live
- Set `DJANGO_DEBUG=0`, a long `DJANGO_SECRET_KEY`, and real `DJANGO_ALLOWED_HOSTS` in `.env`.
- Configure SMTP (`EMAIL_BACKEND` etc. in settings) so password-reset e-mails are really sent.
- Serve with gunicorn/waitress behind HTTPS; run `python manage.py collectstatic`.
- Back up the database regularly.
