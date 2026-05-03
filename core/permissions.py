"""Centralized permission helpers for views & APIs."""
from django.http import JsonResponse
from .models import Staff, Student, Subject, Enrollment


def get_staff(user):
    """Returns Staff instance or None."""
    return getattr(user, 'staff_profile', None)


def get_student(user):
    return getattr(user, 'student_profile', None)


def staff_teaches_subject(staff, subject):
    """Returns True if the staff teaches this subject."""
    if not staff or not subject:
        return False
    return staff.subjects.filter(id=subject.id).exists()


def student_enrolled_in_subject(student, subject):
    """Returns True if student is enrolled in subject."""
    if not student or not subject:
        return False
    return Enrollment.objects.filter(student=student, subject=subject).exists()


def json_error(message, status=400):
    return JsonResponse({'success': False, 'error': message}, status=status)


def json_forbidden(message='Permission denied.'):
    return json_error(message, status=403)