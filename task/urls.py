from django.urls import path
from . import views

urlpatterns = [
    path('sent/', views.SentTasksAPIView.as_view(), name='sent-tasks'),
    path('received/', views.ReceivedTasksAPIView.as_view(), name='received-tasks'),
    path('', views.TaskCreateView.as_view(), name='task-create'),
    path('<uuid:pk>/action/', views.TaskActionView.as_view(), name='task-action'),
    path('<uuid:pk>/', views.TaskDetailView.as_view(), name='task-detail'),
    
    path('spr-report/', views.SPRReportView.as_view(), name='spr-report')
]

