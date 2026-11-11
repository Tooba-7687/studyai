from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.shortcuts import redirect, render
from datetime import date

from .forms import StudyAIUserCreationForm
from .models import StudentProfile


def landing(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return redirect("login")


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        dashboard = request.POST.get("dashboard", "general")
        if dashboard not in {"general", "mdcat"}:
            dashboard = "general"
        profile, _ = StudentProfile.objects.get_or_create(user=request.user)
        profile.student_type = dashboard
        profile.save(update_fields=["student_type"])
        return redirect("dashboard")

    return render(request, "studyai/auth.html", {
        "form": form,
        "heading": "Welcome back",
        "action": "Log in",
        "title": "Log in | StudyAI",
        "selected_dashboard": request.POST.get("dashboard", "general"),
    })


def signup_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    form = StudyAIUserCreationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Your account was created successfully.")
        return redirect("dashboard")

    return render(request, "studyai/auth.html", {
        "form": form,
        "heading": "Create your account",
        "action": "Sign up",
        "title": "Sign up | StudyAI",
        "is_signup": True,
    })


def logout_view(request):
    if request.method == "POST":
        logout(request)
    return redirect("login")


@login_required
def dashboard(request):
    profile, _ = StudentProfile.objects.get_or_create(user=request.user)
    if profile.student_type == 'mdcat':
        if request.method == 'POST':
            try:
                profile.target_date = date.fromisoformat(request.POST.get('target_date', ''))
                profile.save(update_fields=['target_date'])
                messages.success(request, 'Your MDCAT target date was saved.')
                return redirect('dashboard')
            except ValueError:
                messages.error(request, 'Please choose a valid target date.')
        return render(request, "studyai/mdcat_dashboard.html", {"profile": profile})
    return render(request, "studyai/dashboard.html")


@login_required
def study_tools(request):
    return render(request, "studyai/dashboard.html")


@login_required
def mdcat_tools(request):
    return render(request, "studyai/mdcat_tools.html")
