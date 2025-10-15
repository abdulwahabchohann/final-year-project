from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('trending/', views.trending, name='trending'),
    path('categories/', views.categories, name='categories'),
    path('recommendations/', views.recommendations, name='recommendations'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('personalize/', views.personalize, name='personalize'),
    path('signup/', views.signup_view, name='signup'),
]