from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("home/", views.home, name="home"),
    path("categories_list/", views.categories_list, name="categories_list"),
    # path('create/', views.create, name='create'),
    # path('edit/<int:id>/', views.edit, name='edit'),
    # path('delete/<int:id>/', views.delete, name='delete'),
    path("drop/", views.UploadPaymentFileView.as_view(), name="drop"),
    path("statements_list/", views.statements_list, name="statements_list"),
    path("login/", views.login, name="login"),
    path("logout/", views.logout, name="logout"),
    path("register/", views.registration_view, name="register"),
]
