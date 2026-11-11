from django.db import models
from django.contrib.auth.models import User


class ProblemHistory(models.Model):

    SUBJECT_CHOICES = [
        ('Math',    'Math'),
        ('Science', 'Science'),
        ('History', 'History'),
        ('English', 'English'),
        ('General', 'General'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='problem_history', null=True, blank=True)
    problem    = models.TextField()
    solution   = models.TextField()
    subject    = models.CharField(max_length=20, choices=SUBJECT_CHOICES, default='General')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.subject}] {self.problem[:60]}"


class Flashcard(models.Model):

    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='flashcards', null=True, blank=True)
    topic      = models.CharField(max_length=200, default='General')
    question   = models.TextField()
    answer     = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Q: {self.question[:60]}"


class StudyPlan(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='study_plans')
    title = models.CharField(max_length=200)
    topics = models.TextField()
    exam_date = models.DateField()
    hours_per_day = models.PositiveSmallIntegerField(default=2)
    plan = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.title} ({self.user.username})"


class StudentProfile(models.Model):
    STUDENT_TYPES = [
        ('general', 'General student'),
        ('mdcat', 'MDCAT student'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    student_type = models.CharField(max_length=20, choices=STUDENT_TYPES, default='general')
    target_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} ({self.student_type})"