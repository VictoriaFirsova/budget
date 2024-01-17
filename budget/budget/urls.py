import django.contrib.auth.views
from django.urls import path, re_path
from . import views
from .views import UploadPaymentFileView, registration_view

urlpatterns = [
    path('', views.home, name='home'),
    path('home/', views.home, name='home'),
    re_path(r'^categories_list', views.categories_list, name='categories_list'),
    path('', views.statements_list, name='home'),
    path('create/', views.create),
    path('edit/<int:id>/', views.edit),
    path('delete/<int:id>/', views.delete),
    path('drop/', UploadPaymentFileView.as_view(), name='drop'),
    path('statements_list/', views.statements_list, name='statements_list'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('register/', registration_view, name='register'),
    ]