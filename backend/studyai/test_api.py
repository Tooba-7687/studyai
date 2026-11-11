import json
from datetime import date, timedelta
from unittest.mock import patch

from django.core.cache import cache
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse


class ApiAuthenticationTests(TestCase):
    def test_private_data_apis_require_login(self):
        endpoints = [
            ("saved_plans", "get"),
        ]
        for endpoint, method in endpoints:
            with self.subTest(endpoint=endpoint):
                url = reverse(endpoint)
                if method == "get":
                    response = self.client.get(url)
                elif method == "delete":
                    response = self.client.delete(url)
                else:
                    response = self.client.post(url, data="{}", content_type="application/json")
                self.assertEqual(response.status_code, 401)


class QuizApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="learner", password="Test-password-2026!")
        self.client.force_login(self.user)
        self.url = reverse("quiz")

    def post_json(self, payload):
        return self.client.post(self.url, data=json.dumps(payload), content_type="application/json")

    def test_invalid_quiz_inputs_are_rejected_without_calling_ai(self):
        invalid_payloads = [
            ({"topic": ""}, "Topic is required."),
            ({"topic": "Biology", "count": 0}, "Choose between 1 and 20 questions."),
            ({"topic": "Biology", "count": 21}, "Choose between 1 and 20 questions."),
            ({"topic": "Biology", "count": "many"}, "Question count must be a whole number."),
            ({"topic": "Biology", "type": "essay"}, "Choose MCQ, written, or Q&A test."),
        ]

        with patch("studyai.views.generate_quiz") as generate_quiz:
            for payload, expected_error in invalid_payloads:
                with self.subTest(payload=payload):
                    response = self.post_json(payload)
                    self.assertEqual(response.status_code, 400)
                    self.assertEqual(response.json()["error"], expected_error)
            generate_quiz.assert_not_called()

    def test_valid_quiz_returns_generated_questions(self):
        questions = [{"question": "What is a cell?", "options": ["A", "B"], "correct": "A"}]
        with patch("studyai.views.generate_quiz", return_value=questions) as generate_quiz:
            response = self.post_json({"topic": "Biology", "count": 1, "type": "mcq"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["questions"], questions)
        generate_quiz.assert_called_once_with("Biology", 1)

    def test_malformed_json_is_a_client_error(self):
        response = self.client.post(self.url, data="{invalid", content_type="application/json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_non_object_and_oversized_topics_are_rejected_before_ai(self):
        with patch("studyai.views.generate_quiz") as generate_quiz:
            non_object = self.client.post(self.url, data="[]", content_type="application/json")
            oversized = self.post_json({"topic": "B" * 201, "count": 1})

        self.assertEqual(non_object.status_code, 400)
        self.assertEqual(oversized.status_code, 400)
        generate_quiz.assert_not_called()

    def test_expired_exam_date_is_rejected(self):
        response = self.client.post(
            reverse("study_plan"),
            data=json.dumps({"topics": "Biology", "exam_date": (date.today() - timedelta(days=1)).isoformat()}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

    def test_invalid_study_hours_are_rejected_without_calling_ai(self):
        with patch("studyai.views.generate_study_plan") as generate_plan:
            response = self.client.post(
                reverse("study_plan"),
                data=json.dumps({
                    "topics": "Biology",
                    "exam_date": (date.today() + timedelta(days=1)).isoformat(),
                    "hours_per_day": 25,
                }),
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 400)
        generate_plan.assert_not_called()

    def test_quiz_requires_csrf_token(self):
        client = Client(enforce_csrf_checks=True)
        login_page = client.get(reverse("login"))
        csrf_token = login_page.cookies["csrftoken"].value
        payload = json.dumps({"topic": "Biology", "count": 1})

        with patch("studyai.views.generate_quiz", return_value=[]) as generate_quiz:
            rejected = client.post(self.url, data=payload, content_type="application/json")
            accepted = client.post(
                self.url,
                data=payload,
                content_type="application/json",
                HTTP_X_CSRFTOKEN=csrf_token,
            )

        self.assertEqual(rejected.status_code, 403)
        self.assertEqual(accepted.status_code, 200)
        generate_quiz.assert_called_once_with("Biology", 1)

    def test_ocr_rejects_unsupported_file_types_before_processing(self):
        upload = SimpleUploadedFile("notes.gif", b"not-an-image", content_type="image/gif")

        with patch("studyai.views.extract_text") as extract_text:
            response = self.client.post(reverse("ocr"), {"image": upload})

        self.assertEqual(response.status_code, 400)
        self.assertIn("JPG, PNG, or WebP", response.json()["error"])
        extract_text.assert_not_called()

    def test_ai_requests_are_rate_limited_per_client(self):
        cache.clear()
        with patch("studyai.views.generate_quiz", return_value=[]) as generate_quiz:
            for _ in range(20):
                response = self.post_json({"topic": "Biology", "count": 1})
                self.assertEqual(response.status_code, 200)

            limited = self.post_json({"topic": "Biology", "count": 1})

        self.assertEqual(limited.status_code, 429)
        self.assertEqual(limited["Retry-After"], "60")
        self.assertEqual(generate_quiz.call_count, 20)
        cache.clear()
