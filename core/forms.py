from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import (
    CustomUser, Notice, Feedback, Timetable, Enrollment
)


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    role = forms.ChoiceField(choices=CustomUser.ROLE_CHOICES, required=True)

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'role', 'password1', 'password2')


class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))


class NoticeForm(forms.ModelForm):
    class Meta:
        model = Notice
        fields = ['title', 'content']
        widgets = {'content': forms.Textarea(attrs={'rows': 4})}


class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ['subject_text', 'message']
        widgets = {'message': forms.Textarea(attrs={'rows': 4})}


class FeedbackUpdateForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ['status', 'response']
        widgets = {'response': forms.Textarea(attrs={'rows': 4})}


class TimetableForm(forms.ModelForm):
    class Meta:
        model = Timetable
        fields = ['subject', 'staff', 'day', 'start_time', 'end_time', 'classroom', 'department', 'semester']
        widgets = {
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
        }


class EnrollmentForm(forms.ModelForm):
    class Meta:
        model = Enrollment
        fields = ['student', 'subject']