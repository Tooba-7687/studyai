import json
from datetime import date
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from .models import Flashcard, ProblemHistory, StudyPlan


class UserDataIsolationTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(username="alice", password="Test-password-2026!")
        self.bob = User.objects.create_user(username="bob", password="Test-password-2026!")

    def test_history_only_returns_the_signed_in_users_records(self):
        alice_record = ProblemHistory.objects.create(
            user=self.alice, problem="Alice question", solution="Alice answer", subject="Math"
        )
        ProblemHistory.objects.create(
            user=self.bob, problem="Bob question", solution="Bob answer", subject="Science"
        )
        client = Client()
        client.force_login(self.alice)

        response = client.get(reverse("history"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.json()["history"]], [alice_record.id])

    def test_anonymous_history_is_empty_and_clear_does_not_delete_user_records(self):
        record = ProblemHistory.objects.create(
            user=self.alice, problem="Private question", solution="Private answer", subject="Math"
        )

        history = self.client.get(reverse("history"))
        cleared = self.client.delete(reverse("clear_history"))

        self.assertEqual(history.status_code, 200)
        self.assertEqual(history.json()["history"], [])
        self.assertEqual(cleared.status_code, 200)
        self.assertTrue(ProblemHistory.objects.filter(pk=record.pk, user=self.alice).exists())

    def test_clearing_history_deletes_only_the_signed_in_users_records(self):
        ProblemHistory.objects.create(user=self.alice, problem="A", solution="A", subject="Math")
        ProblemHistory.objects.create(user=self.bob, problem="B", solution="B", subject="Science")
        Flashcard.objects.create(user=self.alice, topic="A", question="A?", answer="A")
        bob_card = Flashcard.objects.create(user=self.bob, topic="B", question="B?", answer="B")
        client = Client()
        client.force_login(self.alice)

        response = client.delete(reverse("clear_history"))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(ProblemHistory.objects.filter(user=self.alice).exists())
        self.assertTrue(ProblemHistory.objects.filter(user=self.bob).exists())
        self.assertFalse(Flashcard.objects.filter(user=self.alice).exists())
        self.assertTrue(Flashcard.objects.filter(pk=bob_card.pk).exists())

    @patch("studyai.views.solve_problem", return_value="A private solution")
    @patch("studyai.views.detect_subject", return_value="Math")
    def test_solved_problem_is_saved_to_the_current_user(self, detect_subject, solve_problem):
        client = Client()
        client.force_login(self.alice)

        response = client.post(
            reverse("solve"),
            data=json.dumps({"problem": "2 + 2"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        record = ProblemHistory.objects.get(problem="2 + 2")
        self.assertEqual(record.user, self.alice)
        detect_subject.assert_called_once_with("2 + 2")
        solve_problem.assert_called_once_with("2 + 2")

    @patch("studyai.views.generate_flashcards", return_value=[{"question": "Q?", "answer": "A"}])
    def test_generated_flashcards_are_saved_to_the_current_user(self, generate_flashcards):
        client = Client()
        client.force_login(self.alice)

        response = client.post(
            reverse("flashcards"),
            data=json.dumps({"notes": "Private notes", "topic": "Biology"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Flashcard.objects.get(question="Q?").user, self.alice)
        generate_flashcards.assert_called_once_with("Private notes")

    def test_saved_plans_cannot_be_read_or_modified_by_another_user(self):
        plan = StudyPlan.objects.create(
            user=self.alice,
            title="Alice plan",
            topics="Biology",
            exam_date=date(2026, 12, 1),
            hours_per_day=2,
            plan="Study cells",
        )
        client = Client()
        client.force_login(self.bob)

        detail = client.delete(reverse("saved_plan_detail", args=[plan.id]))

        self.assertEqual(detail.status_code, 404)
        self.assertTrue(StudyPlan.objects.filter(pk=plan.pk, user=self.alice).exists())


class ApiCsrfTests(TestCase):
    def test_saved_plan_changes_require_a_valid_csrf_token(self):
        user = User.objects.create_user(username="learner", password="Test-password-2026!")
        client = Client(enforce_csrf_checks=True)
        client.force_login(user)
        page = client.get(reverse("dashboard"))
        csrf_token = page.cookies["csrftoken"].value
        payload = {
            "title": "Exam prep",
            "topics": "Biology",
            "exam_date": "2026-12-01",
            "hours_per_day": 2,
            "plan": "Study cells",
        }

        rejected = client.post(
            reverse("saved_plans"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        accepted = client.post(
            reverse("saved_plans"),
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(rejected.status_code, 403)
        self.assertEqual(accepted.status_code, 201)

    @patch("studyai.views.generate_flashcards", return_value=[{"question": "Q?", "answer": "A"}])
    @patch("studyai.views.solve_problem", return_value="Private solution")
    @patch("studyai.views.detect_subject", return_value="Math")
    def test_learning_record_writes_require_csrf(self, detect_subject, solve_problem, generate_flashcards):
        user = User.objects.create_user(username="learner", password="Test-password-2026!")
        client = Client(enforce_csrf_checks=True)
        client.force_login(user)
        page = client.get(reverse("dashboard"))
        csrf_token = page.cookies["csrftoken"].value
        solve_payload = json.dumps({"problem": "2 + 2"})
        flashcard_payload = json.dumps({"notes": "Private notes", "topic": "Biology"})

        rejected_solve = client.post(reverse("solve"), data=solve_payload, content_type="application/json")
        accepted_solve = client.post(
            reverse("solve"), data=solve_payload, content_type="application/json", HTTP_X_CSRFTOKEN=csrf_token
        )
        rejected_flashcards = client.post(
            reverse("flashcards"), data=flashcard_payload, content_type="application/json"
        )
        accepted_flashcards = client.post(
            reverse("flashcards"),
            data=flashcard_payload,
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(rejected_solve.status_code, 403)
        self.assertEqual(accepted_solve.status_code, 200)
        self.assertEqual(rejected_flashcards.status_code, 403)
        self.assertEqual(accepted_flashcards.status_code, 200)
        self.assertTrue(ProblemHistory.objects.filter(user=user, problem="2 + 2").exists())
        self.assertTrue(Flashcard.objects.filter(user=user, question="Q?").exists())
        detect_subject.assert_called_once_with("2 + 2")
        solve_problem.assert_called_once_with("2 + 2")
        generate_flashcards.assert_called_once_with("Private notes")
