from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("home/", views.home, name="home"),
    path("categories_list/", views.categories_list, name="categories_list"),
    path("categories_list/create/", views.create, name="create"),
    path("categories_list/<int:id>/edit/", views.edit, name="edit"),
    path("categories_list/<int:id>/delete/", views.delete, name="delete"),
    path("drop/", views.UploadPaymentFileView.as_view(), name="drop"),
    path("statements_list/", views.statements_list, name="statements_list"),
    path("login/", views.login, name="login"),
    path("logout/", views.logout, name="logout"),
    path("register/", views.registration_view, name="register"),
]
