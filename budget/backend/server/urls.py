from django.contrib import admin
from django.urls import path, include


urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('', include(('budget.backend.apps.budget.urls', 'budget'), namespace='budget')),
    path('', include('budget.backend.apps.api.v1.urls')),


]