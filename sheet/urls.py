from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'finishing-sheets', views.FinishingSheetViewSet)

urlpatterns = [
    path('', include(router.urls)),
]