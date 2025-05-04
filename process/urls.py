from django.urls import path
from . import views

urlpatterns = [
    path('processes/', views.ProcessListAPIView.as_view(), name='process-list'),
    
]