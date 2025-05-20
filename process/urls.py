from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProcessViewSet

router = DefaultRouter()
router.register(r'', ProcessViewSet, basename='process')

urlpatterns = [
    path('', include(router.urls)),
]