from django.contrib import admin
from django.urls import path, include


urlpatterns = [

    # path('admin/', admin.site.urls),
    # path('accounts/', include('django.contrib.auth.urls')),
    # path('', include('budget.urls', namespace='budget')),
    path('api/v1/', include('budget.API.v1.urls')),
    path('api/v1/docs/', include('budget.API.v1.urls')),
]