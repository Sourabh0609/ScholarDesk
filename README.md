# ScholarDesk

Production-ready role-based academic management SaaS built with Django.

## Features
- Custom user roles: Student, Staff, HOD
- Role-based dashboards & access control
- Bulk attendance with enrollment validation
- Bulk marks upload with 0–100 validation
- Notice board, Feedback, Timetable
- Chart.js analytics
- Secure CSRF-protected JSON APIs
- Permission checks on every endpoint (subject ownership + enrollment)

## Setup

```bash
python -m venv venv
source venv/bin/activate           # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py makemigrations core
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000/

## Initial Setup
1. Login to `/admin` with superuser
2. Create **Departments**
3. Create **Subjects** (assign department + semester)
4. Register users via `/register` (student / staff / hod)
5. Open Subjects in admin → add **Enrollments** (assign students)
6. Open Staff in admin → assign **subjects** they teach

## Security Highlights
- ✅ No `@csrf_exempt` anywhere
- ✅ Session auth + CSRF token validation on APIs
- ✅ Staff cannot access subjects they don't teach
- ✅ Marks/attendance only for enrolled students
- ✅ Role-based decorators on every view

## API Usage (CSRF-protected)
Frontend must send `X-CSRFToken` header.

```javascript
fetch('/api/staff/attendance/bulk/', {
    method: 'POST',
    credentials: 'same-origin',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCSRFToken(),  // from main.js
    },
    body: JSON.stringify({
        subject_id: 1,
        date: '2025-01-20',
        entries: [
            {student_id: 5, status: 'Present'},
            {student_id: 6, status: 'Absent'}
        ]
    })
}).then(r => r.json()).then(console.log);
```

## Endpoints
| Method | URL | Purpose |
|---|---|---|
| GET | `/api/student/dashboard/` | Student stats |
| GET | `/api/subject/<id>/students/?date=YYYY-MM-DD` | Enrolled students + attendance |
| POST | `/api/staff/attendance/bulk/` | Bulk attendance |
| POST | `/api/staff/marks/bulk/` | Bulk marks |