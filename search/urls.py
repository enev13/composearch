from django.urls import path

from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('search/', views.search_view, name='search'),
    path('search/fallback/', views.search_fallback_view, name='search_fallback'),
]
