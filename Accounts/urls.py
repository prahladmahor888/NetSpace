from django.urls import path
from . import views

urlpatterns = [
    path('', views.login, name='login'),
    path("register", views.register, name="register"),
    path('logout/', views.logout, name='logout'),
    path('check-username/', views.check_username, name='check_username'),
]