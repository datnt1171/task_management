from django.urls import path
from .views import ProcessListAPIView, ProcessDetailAPIView

urlpatterns = [
    path('', ProcessListAPIView.as_view(), name='process-list'),
    path('<uuid:pk>/', ProcessDetailAPIView.as_view(), name='process-detail'),
]