from django.contrib import admin
from django.urls import path, include
from studyai import web_views

urlpatterns = [
    path('', web_views.landing, name='landing'),
    path('login/', web_views.login_view, name='login'),
    path('signup/', web_views.signup_view, name='signup'),
    path('logout/', web_views.logout_view, name='logout'),
    path('dashboard/', web_views.dashboard, name='dashboard'),
    path('study-tools/', web_views.study_tools, name='study_tools'),
    path('mdcat-tools/', web_views.mdcat_tools, name='mdcat_tools'),
    path('admin/',  admin.site.urls),
    path('api/',    include('studyai.urls')),
]