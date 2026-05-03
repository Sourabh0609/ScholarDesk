from django.contrib import admin
from .models import (
    CustomUser, Department, Subject, Student, Staff,
    Attendance, Marks, Notice, Feedback, Timetable, Enrollment
)

admin.site.site_header = "ScholarDesk Admin"
admin.site.site_title = "ScholarDesk"
admin.site.index_title = "Welcome to ScholarDesk Administration"


class EnrollmentInline(admin.TabularInline):
    model = Enrollment
    extra = 1


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'role', 'first_name', 'last_name', 'is_active')
    list_filter = ('role', 'is_active')
    search_fields = ('username', 'email')


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'code')


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'department', 'semester')
    search_fields = ('code', 'name')
    inlines = [EnrollmentInline]


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('roll_number', 'user', 'department', 'semester', 'section')
    search_fields = ('roll_number',)
    inlines = [EnrollmentInline]


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ('employee_id', 'user', 'department', 'designation')
    search_fields = ('employee_id',)
    filter_horizontal = ('subjects',)


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'subject', 'enrolled_at')
    list_filter = ('subject',)


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('student', 'subject', 'date', 'status', 'marked_by')
    list_filter = ('status', 'date', 'subject')


@admin.register(Marks)
class MarksAdmin(admin.ModelAdmin):
    list_display = ('student', 'subject', 'exam_type', 'marks', 'uploaded_by')
    list_filter = ('exam_type', 'subject')


@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_by', 'created_at')


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('student', 'subject_text', 'status', 'created_at')
    list_filter = ('status',)


@admin.register(Timetable)
class TimetableAdmin(admin.ModelAdmin):
    list_display = ('day', 'subject', 'staff', 'start_time', 'end_time', 'classroom')
    list_filter = ('day',)