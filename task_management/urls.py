from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from user.views import CustomTokenObtainPairView
from rest_framework_simplejwt.views import (
    TokenRefreshView,
)
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),
    # path('silk/', include('silk.urls', namespace='silk')),
    path('api/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    path('api/processes/', include('process.urls')),
    path('api/users/', include('user.urls')),
    # path('workflow_engine/', include('workflow_engine.urls')),
    path('api/tasks/', include('task.urls')),
    # path('api/edms/', include('edms.urls')),
    path('api/sheet', include('sheet.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
