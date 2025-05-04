from django.urls import path
from . import views

urlpatterns = [
    path('sent/', views.SentTaskListAPIView.as_view(), name='task-sent'),
    path('received/', views.ReceivedTasksAPIView.as_view(), name='task-received'),
    path('<int:pk>/', views.TaskDetailAPIView.as_view(), name='task-detail'),
    path('create/', views.TaskCreateAPIView.as_view(), name='task-create'),
    path('<int:pk>/status/', views.TaskStatusUpdateAPIView.as_view(), name='task-update-status'),   
]

