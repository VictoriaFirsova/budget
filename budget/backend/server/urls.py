from django.contrib import admin
from django.urls import path, include


urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path(
        "", include(("apps.budget.urls", "budget"), namespace="budget")
    ),
    path("", include("apps.api.v1.urls")),
]
