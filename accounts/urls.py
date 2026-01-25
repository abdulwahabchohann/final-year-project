from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),

    path('api/categories/', views.CategoryListView.as_view(), name='api_category_list'),
    path('api/categories/<slug:slug>/books/', views.CategoryBooksView.as_view(), name='api_category_books'),
    path('api/recommendations/mood/', views.MoodRecommendationsAPIView.as_view(), name='api_mood_recommendations'),
    path('api/recommendations/dataset/', views.DatasetRecommendationsAPIView.as_view(), name='api_dataset_recommendations'),

    path('login/', views.login_view, name='login'),
    path('login/google/', views.google_login, name='google_login'),
    path('oauth2callback/', views.google_callback, name='google_callback'),
    path('logout/', views.logout_view, name='logout'),
    path('signup/', views.signup_view, name='signup'),
    path('search/', views.search_books, name='search'),

    path('personalize/', views.personalize, name='personalize'),
    path('trending/', views.trending, name='trending'),
    path('categories/', views.categories, name='categories'),
    path('categories/<slug:slug>/', views.category_detail, name='category_detail'),
    path('books/<slug:slug>/', views.book_detail, name='book_detail'),
    path('recommendations/', views.recommendations, name='recommendations'),

    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('profile/change-password/', views.change_password, name='change_password'),
]
