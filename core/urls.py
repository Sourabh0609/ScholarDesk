from django.urls import path
from . import views, api

urlpatterns = [
    # Auth
    path('', views.login_view, name='login'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('dashboard/', views.dashboard_redirect, name='dashboard_redirect'),

    # Student
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    path('student/attendance/', views.student_attendance, name='student_attendance'),
    path('student/marks/', views.student_marks, name='student_marks'),
    path('student/notices/', views.student_notices, name='student_notices'),
    path('student/timetable/', views.student_timetable, name='student_timetable'),
    path('student/feedback/', views.student_feedback, name='student_feedback'),

    # Staff
    path('staff/dashboard/', views.staff_dashboard, name='staff_dashboard'),
    path('staff/attendance/', views.staff_attendance, name='staff_attendance'),
    path('staff/marks/', views.staff_marks, name='staff_marks'),
    path('staff/notices/', views.staff_notices, name='staff_notices'),
    path('staff/feedback/', views.staff_feedback, name='staff_feedback'),
    path('staff/feedback/<int:pk>/update/', views.update_feedback, name='update_feedback'),
    path('staff/timetable/', views.staff_timetable, name='staff_timetable'),

    # HOD
    path('hod/dashboard/', views.hod_dashboard, name='hod_dashboard'),
    path('hod/students/', views.hod_students, name='hod_students'),
    path('hod/staff/', views.hod_staff, name='hod_staff'),
    path('hod/attendance/', views.hod_attendance, name='hod_attendance'),
    path('hod/marks/', views.hod_marks, name='hod_marks'),
    path('hod/notices/', views.hod_notices, name='hod_notices'),

    # API (CSRF-protected, session auth)
    path('api/student/dashboard/', api.api_student_dashboard, name='api_student_dashboard'),
    path('api/subject/<int:subject_id>/students/', api.api_subject_students, name='api_subject_students'),
    path('api/staff/attendance/bulk/', api.api_bulk_attendance, name='api_bulk_attendance'),
    path('api/staff/marks/bulk/', api.api_bulk_marks, name='api_bulk_marks'),
]