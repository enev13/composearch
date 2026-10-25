from django.urls import path

from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('search/', views.loading_view, name='loading'),
    path('search/results/', views.results_view, name='results'),
]
