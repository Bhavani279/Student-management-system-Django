# Education Management System

A web-based Education Management System built with Django. It helps schools and
institutions manage day-to-day academic work in one place, replacing manual
records with a simple, organized dashboard.

## Features
- Role-based login (Admin, Teacher, Student)
- Student and teacher management
- Course / class and subject management
- Attendance tracking
- Exam, marks and result management
- Fee and notice management (if included)
- Clean dashboard for each user role

## Tech Stack
- Backend: Python, Django
- Frontend: HTML, CSS, Bootstrap, JavaScript
- Database: SQLite / MySQL

## Installation
1. Clone the repository
   git clone https://github.com/<your-username>/<repo-name>.git
2. Create and activate a virtual environment
   python -m venv venv
   venv\Scripts\activate
3. Install dependencies
   pip install -r requirements.txt
4. Run migrations
   python manage.py migrate
5. Create an admin user
   python manage.py createsuperuser
6. Start the server
   python manage.py runserver

## Usage
Open http://127.0.0.1:8000/ in your browser and log in with your credentials.

## Future Improvements
- Online fee payment
- Parent portal
- Report card PDF export

## License
This project is open source and available under the MIT License.
