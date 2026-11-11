from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import StudentProfile


class StudyAIUserCreationForm(UserCreationForm):
    student_type = forms.ChoiceField(
        label="I am preparing for",
        choices=StudentProfile.STUDENT_TYPES,
        widget=forms.Select(attrs={"class": "profile-select"}),
    )

    class Meta:
        model = User
        fields = ("username", "student_type", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            StudentProfile.objects.create(
                user=user,
                student_type=self.cleaned_data["student_type"],
            )
        return user
