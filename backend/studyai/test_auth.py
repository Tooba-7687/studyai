from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import StudentProfile


class AuthenticationFlowTests(TestCase):
    def test_signup_creates_account_profile_and_authenticated_session(self):
        response = self.client.post(
            reverse("signup"),
            {
                "username": "mdcat_student",
                "student_type": "mdcat",
                "password1": "Test-password-2026!",
                "password2": "Test-password-2026!",
            },
        )

        self.assertRedirects(response, reverse("dashboard"))
        user = User.objects.get(username="mdcat_student")
        self.assertTrue(user.is_authenticated)
        self.assertTrue(self.client.session.get("_auth_user_id"))
        self.assertEqual(user.student_profile.student_type, "mdcat")

    def test_dashboard_redirects_anonymous_users_to_login(self):
        response = self.client.get(reverse("dashboard"))

        self.assertRedirects(response, f"{reverse('login')}?next={reverse('dashboard')}")

    def test_logout_requires_post_and_ends_the_session(self):
        user = User.objects.create_user(username="learner", password="Test-password-2026!")
        self.client.force_login(user)

        get_response = self.client.get(reverse("logout"))
        self.assertRedirects(get_response, reverse("login"), fetch_redirect_response=False)
        self.assertIn("_auth_user_id", self.client.session)

        post_response = self.client.post(reverse("logout"))
        self.assertRedirects(post_response, reverse("login"))
        self.assertNotIn("_auth_user_id", self.client.session)


class ProfileSelectionTests(TestCase):
    def test_login_saves_selected_dashboard(self):
        user = User.objects.create_user(username="learner", password="Test-password-2026!")

        response = self.client.post(
            reverse("login"),
            {"username": user.username, "password": "Test-password-2026!", "dashboard": "mdcat"},
        )

        self.assertRedirects(response, reverse("dashboard"))
        self.assertEqual(StudentProfile.objects.get(user=user).student_type, "mdcat")
        dashboard_response = self.client.get(reverse("dashboard"))
        self.assertContains(dashboard_response, "MDCAT PREP DESK")
