from django.urls import path
from .views import ListProcessAPIView, ProcessDetailAPIView

urlpatterns = [
    path('', ListProcessAPIView.as_view(), name='process-list'),
    path('<uuid:pk>/', ProcessDetailAPIView.as_view(), name='process-detail'),
]