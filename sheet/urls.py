from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'finishing-sheets', views.FinishingSheetViewSet, basename='finishing-sheet')
router.register(r'sheet-blueprints', views.SheetBlueprintViewSet, basename='sheet-blueprint')

urlpatterns = [
    path('', include(router.urls)),
    path('step-templates/', views.StepTemplateListView.as_view(), name='step-template'),
    path('formular-templates/', views.FormularTemplateListView.as_view(), name='formular-template'),
]