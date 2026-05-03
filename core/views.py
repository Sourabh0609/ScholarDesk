from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Avg
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import timedelta, datetime
import json

from .models import (
    Student, Staff, Subject, Attendance, Marks,
    Notice, Feedback, Timetable
)
from .forms import (
    RegisterForm, LoginForm, NoticeForm, FeedbackForm,
    FeedbackUpdateForm, TimetableForm
)
from .decorators import student_required, staff_required, hod_required
from .permissions import staff_teaches_subject, student_enrolled_in_subject


# ========== AUTH ==========

def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard_redirect')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Account created successfully. Please login.')
            return redirect('login')
        messages.error(request, 'Please correct the errors below.')
    else:
        form = RegisterForm()
    return render(request, 'registration/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard_redirect')
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            return redirect('dashboard_redirect')
        messages.error(request, 'Invalid credentials.')
    else:
        form = LoginForm()
    return render(request, 'registration/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, 'You have logged out.')
    return redirect('login')


@login_required
def dashboard_redirect(request):
    if request.user.is_student:
        return redirect('student_dashboard')
    elif request.user.is_staff_role:
        return redirect('staff_dashboard')
    elif request.user.is_hod:
        return redirect('hod_dashboard')
    return redirect('login')


# ========== STUDENT ==========

@student_required
def student_dashboard(request):
    student = get_object_or_404(Student, user=request.user)

    total = Attendance.objects.filter(student=student).count()
    present = Attendance.objects.filter(student=student, status='Present').count()
    attendance_percentage = round((present / total) * 100, 2) if total else 0

    avg_marks = round(Marks.objects.filter(student=student).aggregate(avg=Avg('marks'))['avg'] or 0, 2)
    notices_count = Notice.objects.count()
    recent_notices = Notice.objects.all()[:5]

    timetable = Timetable.objects.filter(
        department=student.department, semester=student.semester
    ) if student.department else Timetable.objects.none()

    enrolled_subjects = student.subjects.all()
    attendance_chart, marks_chart = [], []
    for sub in enrolled_subjects:
        t = Attendance.objects.filter(student=student, subject=sub).count()
        p = Attendance.objects.filter(student=student, subject=sub, status='Present').count()
        if t:
            attendance_chart.append({'subject': sub.code, 'percent': round((p/t)*100, 2)})
        avg = Marks.objects.filter(student=student, subject=sub).aggregate(avg=Avg('marks'))['avg']
        if avg is not None:
            marks_chart.append({'subject': sub.code, 'marks': round(avg, 2)})

    return render(request, 'student/dashboard.html', {
        'student': student,
        'attendance_percentage': attendance_percentage,
        'avg_marks': avg_marks,
        'notices_count': notices_count,
        'recent_notices': recent_notices,
        'timetable': timetable,
        'attendance_chart': json.dumps(attendance_chart),
        'marks_chart': json.dumps(marks_chart),
    })


@student_required
def student_attendance(request):
    student = get_object_or_404(Student, user=request.user)
    qs = Attendance.objects.filter(student=student).select_related('subject')
    page = Paginator(qs, 15).get_page(request.GET.get('page'))
    return render(request, 'student/attendance.html', {'attendances': page})


@student_required
def student_marks(request):
    student = get_object_or_404(Student, user=request.user)
    marks = Marks.objects.filter(student=student).select_related('subject')
    return render(request, 'student/marks.html', {'marks': marks})


@student_required
def student_notices(request):
    page = Paginator(Notice.objects.all(), 10).get_page(request.GET.get('page'))
    return render(request, 'student/notices.html', {'notices': page})


@student_required
def student_timetable(request):
    student = get_object_or_404(Student, user=request.user)
    tt = Timetable.objects.filter(
        department=student.department, semester=student.semester
    ) if student.department else []
    return render(request, 'student/timetable.html', {'timetable': tt})


@student_required
def student_feedback(request):
    student = get_object_or_404(Student, user=request.user)
    if request.method == 'POST':
        form = FeedbackForm(request.POST)
        if form.is_valid():
            fb = form.save(commit=False)
            fb.student = student
            fb.save()
            messages.success(request, 'Feedback submitted.')
            return redirect('student_feedback')
    else:
        form = FeedbackForm()
    return render(request, 'student/feedback.html', {
        'form': form,
        'feedbacks': Feedback.objects.filter(student=student)
    })


# ========== STAFF ==========

@staff_required
def staff_dashboard(request):
    staff = get_object_or_404(Staff, user=request.user)
    # Only count students enrolled in the staff's subjects
    student_count = Student.objects.filter(subjects__in=staff.subjects.all()).distinct().count()
    return render(request, 'staff/dashboard.html', {
        'staff': staff,
        'total_students': student_count,
        'classes_handled': staff.subjects.count(),
        'pending_feedbacks': Feedback.objects.filter(status='pending').count(),
        'recent_notices': Notice.objects.all()[:5],
    })


@staff_required
def staff_attendance(request):
    """Bulk attendance: subject scope strictly limited to staff's subjects."""
    staff = get_object_or_404(Staff, user=request.user)
    subjects = staff.subjects.all()  # ✅ NO fallback to all subjects

    if not subjects.exists():
        messages.warning(request, 'You have no subjects assigned. Contact admin.')
        return render(request, 'staff/attendance.html', {
            'subjects': subjects, 'students_data': [], 'recent': []
        })

    selected_subject = None
    selected_date = request.GET.get('date') or timezone.now().date().isoformat()
    students_data = []

    subject_id = request.GET.get('subject')
    if subject_id:
        try:
            sid = int(subject_id)
        except (TypeError, ValueError):
            messages.error(request, 'Invalid subject id.')
            return redirect('staff_attendance')

        # ✅ Permission check: must be staff's own subject
        if not staff.subjects.filter(id=sid).exists():
            messages.error(request, 'You do not teach this subject.')
            return redirect('staff_attendance')

        selected_subject = get_object_or_404(Subject, id=sid)
        students = Student.objects.filter(subjects=selected_subject).select_related('user')
        existing = {
            a.student_id: a.status
            for a in Attendance.objects.filter(subject=selected_subject, date=selected_date)
        }
        students_data = [{
            'id': s.id,
            'roll_number': s.roll_number,
            'name': s.user.get_full_name() or s.user.username,
            'status': existing.get(s.id, 'Present'),
        } for s in students]

    if request.method == 'POST':
        try:
            post_subject_id = int(request.POST.get('subject_id'))
        except (TypeError, ValueError):
            messages.error(request, 'Invalid form data.')
            return redirect('staff_attendance')

        # ✅ Permission re-check on POST
        if not staff.subjects.filter(id=post_subject_id).exists():
            messages.error(request, 'Permission denied for this subject.')
            return redirect('staff_attendance')

        subject_obj = get_object_or_404(Subject, id=post_subject_id)
        post_date = request.POST.get('date')
        try:
            date_obj = datetime.strptime(post_date, '%Y-%m-%d').date()
        except (TypeError, ValueError):
            messages.error(request, 'Invalid date.')
            return redirect('staff_attendance')

        # ✅ Only enrolled students for this subject
        enrolled_ids = set(
            Student.objects.filter(subjects=subject_obj).values_list('id', flat=True)
        )

        student_ids = request.POST.getlist('student_ids')
        created, updated, skipped = 0, 0, 0
        for sid in student_ids:
            try:
                sid_int = int(sid)
            except ValueError:
                skipped += 1
                continue
            if sid_int not in enrolled_ids:  # ✅ enrollment validation
                skipped += 1
                continue
            status = request.POST.get(f'status_{sid_int}', 'Absent')
            if status not in ('Present', 'Absent'):
                skipped += 1
                continue
            _, was_created = Attendance.objects.update_or_create(
                student_id=sid_int, subject=subject_obj, date=date_obj,
                defaults={'status': status, 'marked_by': staff}
            )
            if was_created:
                created += 1
            else:
                updated += 1
        msg = f'Attendance saved: {created} new, {updated} updated.'
        if skipped:
            msg += f' {skipped} skipped (not enrolled or invalid).'
        messages.success(request, msg)
        return redirect(f"{request.path}?subject={post_subject_id}&date={post_date}")

    recent = Attendance.objects.filter(marked_by=staff).select_related('student__user', 'subject')[:20]
    return render(request, 'staff/attendance.html', {
        'subjects': subjects,
        'selected_subject': selected_subject,
        'selected_date': selected_date,
        'students_data': students_data,
        'recent': recent,
    })


@staff_required
def staff_marks(request):
    """Bulk marks upload, scoped to staff's subjects + enrolled students."""
    staff = get_object_or_404(Staff, user=request.user)
    subjects = staff.subjects.all()  # ✅ NO fallback
    exam_types = [c[0] for c in Marks.EXAM_CHOICES]

    if not subjects.exists():
        messages.warning(request, 'You have no subjects assigned. Contact admin.')
        return render(request, 'staff/marks.html', {
            'subjects': subjects, 'exam_types': exam_types,
            'students_data': [], 'recent': []
        })

    selected_subject = None
    selected_exam = request.GET.get('exam_type', '')
    students_data = []

    subject_id = request.GET.get('subject')
    if subject_id and selected_exam:
        try:
            sid = int(subject_id)
        except (TypeError, ValueError):
            return redirect('staff_marks')

        if not staff.subjects.filter(id=sid).exists():
            messages.error(request, 'You do not teach this subject.')
            return redirect('staff_marks')

        if selected_exam not in exam_types:
            messages.error(request, 'Invalid exam type.')
            return redirect('staff_marks')

        selected_subject = get_object_or_404(Subject, id=sid)
        students = Student.objects.filter(subjects=selected_subject).select_related('user')
        existing = {
            m.student_id: m.marks
            for m in Marks.objects.filter(subject=selected_subject, exam_type=selected_exam)
        }
        students_data = [{
            'id': s.id,
            'roll_number': s.roll_number,
            'name': s.user.get_full_name() or s.user.username,
            'marks': existing.get(s.id, ''),
        } for s in students]

    if request.method == 'POST':
        try:
            post_subject_id = int(request.POST.get('subject_id'))
        except (TypeError, ValueError):
            return redirect('staff_marks')

        if not staff.subjects.filter(id=post_subject_id).exists():
            messages.error(request, 'Permission denied for this subject.')
            return redirect('staff_marks')

        post_subject = get_object_or_404(Subject, id=post_subject_id)
        exam_type = request.POST.get('exam_type')
        if exam_type not in exam_types:
            messages.error(request, 'Invalid exam type.')
            return redirect('staff_marks')

        enrolled_ids = set(
            Student.objects.filter(subjects=post_subject).values_list('id', flat=True)
        )

        student_ids = request.POST.getlist('student_ids')
        saved, errors = 0, 0
        for sid in student_ids:
            try:
                sid_int = int(sid)
            except ValueError:
                errors += 1
                continue
            if sid_int not in enrolled_ids:
                errors += 1
                continue
            raw = request.POST.get(f'marks_{sid_int}', '').strip()
            if raw == '':
                continue
            try:
                value = float(raw)
                if 0 <= value <= 100:
                    Marks.objects.update_or_create(
                        student_id=sid_int, subject=post_subject, exam_type=exam_type,
                        defaults={'marks': value, 'uploaded_by': staff}
                    )
                    saved += 1
                else:
                    errors += 1
            except ValueError:
                errors += 1
        messages.success(request, f'{saved} marks saved.' + (f' {errors} errors.' if errors else ''))
        return redirect(f"{request.path}?subject={post_subject.id}&exam_type={exam_type}")

    recent = Marks.objects.filter(uploaded_by=staff).select_related('student__user', 'subject')[:20]
    return render(request, 'staff/marks.html', {
        'subjects': subjects,
        'exam_types': exam_types,
        'selected_subject': selected_subject,
        'selected_exam': selected_exam,
        'students_data': students_data,
        'recent': recent,
    })


@staff_required
def staff_notices(request):
    if request.method == 'POST':
        form = NoticeForm(request.POST)
        if form.is_valid():
            n = form.save(commit=False)
            n.created_by = request.user
            n.save()
            messages.success(request, 'Notice posted.')
            return redirect('staff_notices')
    else:
        form = NoticeForm()
    return render(request, 'staff/notices.html', {'form': form, 'notices': Notice.objects.all()})


@staff_required
def staff_feedback(request):
    return render(request, 'staff/feedback.html', {
        'feedbacks': Feedback.objects.all().select_related('student__user')
    })


@staff_required
def update_feedback(request, pk):
    feedback = get_object_or_404(Feedback, pk=pk)
    if request.method == 'POST':
        form = FeedbackUpdateForm(request.POST, instance=feedback)
        if form.is_valid():
            form.save()
            messages.success(request, 'Feedback updated.')
            return redirect('staff_feedback')
    else:
        form = FeedbackUpdateForm(instance=feedback)
    return render(request, 'staff/feedback.html', {
        'feedbacks': Feedback.objects.all().select_related('student__user'),
        'edit_form': form,
        'edit_id': pk,
    })


@staff_required
def staff_timetable(request):
    if request.method == 'POST':
        form = TimetableForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Timetable entry created.')
            return redirect('staff_timetable')
    else:
        form = TimetableForm()
    return render(request, 'staff/timetable.html', {'form': form, 'timetable': Timetable.objects.all()})


# ========== HOD ==========

@hod_required
def hod_dashboard(request):
    total_att = Attendance.objects.count()
    present = Attendance.objects.filter(status='Present').count()
    avg_attendance = round((present / total_att) * 100, 2) if total_att else 0

    total_marks = Marks.objects.count()
    pass_count = Marks.objects.filter(marks__gte=40).count()
    pass_percent = round((pass_count / total_marks) * 100, 2) if total_marks else 0

    today = timezone.now().date()
    trend_labels, trend_data = [], []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        t = Attendance.objects.filter(date=day).count()
        p = Attendance.objects.filter(date=day, status='Present').count()
        trend_labels.append(day.strftime('%b %d'))
        trend_data.append(round((p / t) * 100, 2) if t else 0)

    distribution = {
        '0-40': Marks.objects.filter(marks__lt=40).count(),
        '40-60': Marks.objects.filter(marks__gte=40, marks__lt=60).count(),
        '60-80': Marks.objects.filter(marks__gte=60, marks__lt=80).count(),
        '80-100': Marks.objects.filter(marks__gte=80, marks__lte=100).count(),
    }

    return render(request, 'hod/dashboard.html', {
        'avg_attendance': avg_attendance,
        'pass_percent': pass_percent,
        'total_students': Student.objects.count(),
        'total_staff': Staff.objects.count(),
        'trend_labels': json.dumps(trend_labels),
        'trend_data': json.dumps(trend_data),
        'distribution': json.dumps(distribution),
    })


@hod_required
def hod_students(request):
    return render(request, 'hod/students.html', {
        'students': Student.objects.select_related('user', 'department').all()
    })


@hod_required
def hod_staff(request):
    return render(request, 'hod/staff.html', {
        'staff_list': Staff.objects.select_related('user', 'department').all()
    })


@hod_required
def hod_attendance(request):
    page = Paginator(
        Attendance.objects.select_related('student__user', 'subject').all(), 25
    ).get_page(request.GET.get('page'))
    return render(request, 'hod/attendance.html', {'attendances': page})


@hod_required
def hod_marks(request):
    page = Paginator(
        Marks.objects.select_related('student__user', 'subject').all(), 25
    ).get_page(request.GET.get('page'))
    return render(request, 'hod/marks.html', {'marks': page})


@hod_required
def hod_notices(request):
    if request.method == 'POST':
        form = NoticeForm(request.POST)
        if form.is_valid():
            n = form.save(commit=False)
            n.created_by = request.user
            n.save()
            messages.success(request, 'Notice posted.')
            return redirect('hod_notices')
    else:
        form = NoticeForm()
    return render(request, 'hod/notices.html', {'form': form, 'notices': Notice.objects.all()})