from django.urls import path
from drf_spectacular.views import SpectacularSwaggerView, SpectacularAPIView
from django.conf import settings
from django.conf.urls.static import static
from .budget_api.views import (
    BudgetAnalyticsView,
    StatementViewSet,
    CategoryViewSet,
    StatementImportView,
    StatementManualImportView,
    StatementImportPreviewView,
    ImportTemplateViewSet,
    LoginView,
    LogoutView,
    RegisterView,
)

urlpatterns = [
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    path("api/auth/login/", LoginView.as_view(), name="api-login"),
    path("api/auth/logout/", LogoutView.as_view(), name="api-logout"),
    path("api/auth/register/", RegisterView.as_view(), name="api-register"),
    path(
        "api/import/statements/",
        StatementImportView.as_view(),
        name="statements-import",
    ),
    path(
        "api/import/manual/",
        StatementManualImportView.as_view(),
        name="statements-manual-import",
    ),
    path(
        "api/import/preview/",
        StatementImportPreviewView.as_view(),
        name="statements-import-preview",
    ),
    path(
        "api/statements/",
        StatementViewSet.as_view({"get": "list"}),
        name="api-statements-list",
    ),
    path("api/analytics/", BudgetAnalyticsView.as_view(), name="api-budget-analytics"),
    path(
        "api/categories/",
        CategoryViewSet.as_view({"get": "list", "post": "create"}),
        name="api-category-list",
    ),
    path(
        "api/categories/<int:pk>/",
        CategoryViewSet.as_view(
            {
                "get": "retrieve",
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
        name="api-category-detail",
    ),
    path(
        "api/statements/<int:pk>/",
        StatementViewSet.as_view(
            {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
        ),
        name="api-statement-detail",
    ),
    path(
        "api/import/templates/",
        ImportTemplateViewSet.as_view({"get": "list", "post": "create"}),
        name="api-import-template-list",
    ),
    path(
        "api/import/templates/<int:pk>/",
        ImportTemplateViewSet.as_view(
            {
                "get": "retrieve",
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
        name="api-import-template-detail",
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
