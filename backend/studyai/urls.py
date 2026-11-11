from django.urls import path
from . import views

urlpatterns = [

    path('solve/',          views.solve,           name='solve'),
    path('ocr/',            views.ocr,             name='ocr'),
    path('flashcards/',     views.flashcards,      name='flashcards'),
    path('quiz/',           views.quiz,            name='quiz'),
    path('topic-study-guide/', views.topic_study_guide, name='topic_study_guide'),
    path('mdcat-chat/',       views.mdcat_chat,       name='mdcat_chat'),
    path('history/',        views.history,         name='history'),
    path('history/clear/',  views.clear_history,   name='clear_history'),

  
    path('study-plan/',     views.study_plan,      name='study_plan'),
    path('study-plans/',    views.saved_plans,    name='saved_plans'),
    path('study-plans/<int:plan_id>/', views.saved_plan_detail, name='saved_plan_detail'),
    path('summarize/',      views.summarize,       name='summarize'),
    path('formulas/',       views.formula_sheet,   name='formula_sheet'),
    path('explain/',        views.explain_like_five, name='explain'),
]