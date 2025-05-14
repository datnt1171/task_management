from django.urls import path
from . import views

urlpatterns = [
    path('sent/', views.SentTasksAPIView.as_view(), name='sent-tasks'),
    path('received/', views.ReceivedTasksAPIView.as_view(), name='received-tasks'),
    path('', views.TaskCreateView.as_view(), name='task-create'),
    path('<int:pk>/action/', views.TaskActionView.as_view(), name='task-action'),
    path('<int:pk>/', views.TaskDetailView.as_view(), name='task-detail'),
]

