from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import routers
from budget.API.v1.budget_api.views import StatementViewSet, CategoryViewSet

router = routers.DefaultRouter()
router.register(r'statements', StatementViewSet)
router.register(r'categories', CategoryViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='docs'),
    path('', include('app.urls')),
    path('statements/', StatementViewSet.as_view({'get': 'list'}), name='statements-list'),
    path('categories/', CategoryViewSet.as_view({'get': 'list'}), name='category-list'),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += router.urls
