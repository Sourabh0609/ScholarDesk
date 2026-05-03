"""
Secure API endpoints — uses Django session auth + CSRF protection.
- NO @csrf_exempt
- All endpoints validate role, subject ownership, and student enrollment
"""
import json
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET, require_POST
from django.shortcuts import get_object_or_404
from django.db.models import Avg

from .models import Student, Staff, Subject, Attendance, Marks, Notice
from .decorators import student_required, staff_required
from .permissions import (
    get_staff, get_student, staff_teaches_subject,
    student_enrolled_in_subject, json_error, json_forbidden
)


@login_required
@student_required
@require_GET
def api_student_dashboard(request):
    student = get_student(request.user)
    if not student:
        return json_error('Student profile not found.', 404)

    total = Attendance.objects.filter(student=student).count()
    present = Attendance.objects.filter(student=student, status='Present').count()
    avg = Marks.objects.filter(student=student).aggregate(a=Avg('marks'))['a'] or 0

    return JsonResponse({
        'success': True,
        'student': {
            'roll_number': student.roll_number,
            'name': student.user.get_full_name() or student.user.username,
            'department': student.department.name if student.department else None,
            'semester': student.semester,
        },
        'stats': {
            'attendance_percentage': round((present/total)*100, 2) if total else 0,
            'average_marks': round(avg, 2),
            'notices_count': Notice.objects.count(),
        },
        'subjects': [{'code': s.code, 'name': s.name} for s in student.subjects.all()],
    })


@login_required
@staff_required
@require_GET
def api_subject_students(request, subject_id):
    """Returns students enrolled in a subject (only if staff teaches it)."""
    staff = get_staff(request.user)
    if not staff:
        return json_forbidden('Staff profile not found.')

    subject = get_object_or_404(Subject, id=subject_id)

    # ✅ Permission check
    if not staff_teaches_subject(staff, subject):
        return json_forbidden('You do not teach this subject.')

    students = Student.objects.filter(subjects=subject).select_related('user')
    date = request.GET.get('date')
    existing = {}
    if date:
        existing = {
            a.student_id: a.status
            for a in Attendance.objects.filter(subject=subject, date=date)
        }

    return JsonResponse({
        'success': True,
        'subject': {'id': subject.id, 'code': subject.code, 'name': subject.name},
        'students': [{
            'id': s.id,
            'roll_number': s.roll_number,
            'name': s.user.get_full_name() or s.user.username,
            'status': existing.get(s.id, 'Present'),
        } for s in students],
    })


@login_required
@staff_required
@require_POST
def api_bulk_attendance(request):
    """
    Bulk attendance — CSRF protected (no @csrf_exempt).
    Frontend must send X-CSRFToken header.

    Payload:
    {
        "subject_id": 1,
        "date": "2025-01-20",
        "entries": [{"student_id": 5, "status": "Present"}, ...]
    }
    """
    staff = get_staff(request.user)
    if not staff:
        return json_forbidden('Staff profile not found.')

    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return json_error('Invalid JSON.')

    subject_id = payload.get('subject_id')
    date = payload.get('date')
    entries = payload.get('entries', [])

    if not (subject_id and date and isinstance(entries, list) and entries):
        return json_error('Missing or invalid fields.')

    subject = get_object_or_404(Subject, id=subject_id)

    # ✅ Permission: staff must teach the subject
    if not staff_teaches_subject(staff, subject):
        return json_forbidden('You do not teach this subject.')

    # ✅ Pre-fetch enrolled student IDs once
    enrolled_ids = set(
        Student.objects.filter(subjects=subject).values_list('id', flat=True)
    )

    saved, rejected = 0, []
    for e in entries:
        sid = e.get('student_id')
        status = e.get('status', 'Absent')

        if status not in ('Present', 'Absent'):
            rejected.append({'student_id': sid, 'reason': 'invalid_status'})
            continue

        if sid not in enrolled_ids:  # ✅ enrollment validation
            rejected.append({'student_id': sid, 'reason': 'not_enrolled'})
            continue

        Attendance.objects.update_or_create(
            student_id=sid, subject=subject, date=date,
            defaults={'status': status, 'marked_by': staff}
        )
        saved += 1

    return JsonResponse({'success': True, 'saved': saved, 'rejected': rejected})


@login_required
@staff_required
@require_POST
def api_bulk_marks(request):
    """
    Bulk marks upload — CSRF protected.

    Payload:
    {
        "subject_id": 1, "exam_type": "Internal 1",
        "entries": [{"student_id": 5, "marks": 78}, ...]
    }
    """
    staff = get_staff(request.user)
    if not staff:
        return json_forbidden('Staff profile not found.')

    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return json_error('Invalid JSON.')

    subject_id = payload.get('subject_id')
    exam_type = payload.get('exam_type')
    entries = payload.get('entries', [])

    if not (subject_id and exam_type and isinstance(entries, list) and entries):
        return json_error('Missing or invalid fields.')

    valid_exam_types = [c[0] for c in Marks.EXAM_CHOICES]
    if exam_type not in valid_exam_types:
        return json_error('Invalid exam_type.')

    subject = get_object_or_404(Subject, id=subject_id)

    # ✅ Permission
    if not staff_teaches_subject(staff, subject):
        return json_forbidden('You do not teach this subject.')

    enrolled_ids = set(
        Student.objects.filter(subjects=subject).values_list('id', flat=True)
    )

    saved, rejected = 0, []
    for e in entries:
        sid = e.get('student_id')

        if sid not in enrolled_ids:  # ✅ enrollment validation
            rejected.append({'student_id': sid, 'reason': 'not_enrolled'})
            continue

        try:
            m = float(e.get('marks'))
        except (TypeError, ValueError):
            rejected.append({'student_id': sid, 'reason': 'invalid_marks'})
            continue

        if not (0 <= m <= 100):
            rejected.append({'student_id': sid, 'reason': 'out_of_range'})
            continue

        Marks.objects.update_or_create(
            student_id=sid, subject=subject, exam_type=exam_type,
            defaults={'marks': m, 'uploaded_by': staff}
        )
        saved += 1

    return JsonResponse({'success': True, 'saved': saved, 'rejected': rejected})