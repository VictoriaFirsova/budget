from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularSwaggerView, SpectacularAPIView
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import routers
from budget.backend.apps.api.v1.budget_api.views import StatementViewSet, CategoryViewSet

router = routers.DefaultRouter()
router.register(r'statements', StatementViewSet)
router.register(r'categories', CategoryViewSet)

urlpatterns = [
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='docs'),
    path('', include('budget.backend.apps.budget.urls')),
    path('statements/', StatementViewSet.as_view({'get': 'list'}), name='statements-list'),
    path('categories/', CategoryViewSet.as_view({'get': 'list'}), name='category-list'),
    path('categories/<int:id>/', CategoryViewSet.as_view({'get': 'list'}), name='category-list'),
    path('statements/<int:pk>/', StatementViewSet.as_view({'get': 'retrieve', 'delete': 'destroy'}), name='statement-detail'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += router.urls
