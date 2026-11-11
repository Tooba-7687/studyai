from django.contrib import admin

from .models import ProblemHistory, Flashcard


@admin.register(ProblemHistory)
class ProblemHistoryAdmin(admin.ModelAdmin):
    list_display = ('problem', 'subject', 'created_at')
    list_filter = ('subject',)
    search_fields = ('problem', 'solution')
    readonly_fields = ('created_at',)


@admin.register(Flashcard)
class FlashcardAdmin(admin.ModelAdmin):
    list_display = ('question', 'topic', 'created_at')
    list_filter = ('topic',)
    search_fields = ('question', 'answer')
    readonly_fields = ('created_at',)
