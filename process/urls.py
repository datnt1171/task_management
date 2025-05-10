from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProcessViewSet

router = DefaultRouter()
router.register(r'', ProcessViewSet, basename='process')  # No prefix needed, already under /api/processes/

urlpatterns = [
    path('', include(router.urls)),
]