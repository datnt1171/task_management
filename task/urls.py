from django.urls import path
from . import views

urlpatterns = [
    path('sent/', views.SentTasksAPIView.as_view(), name='sent-tasks'),
    path('received/', views.ReceivedTasksAPIView.as_view(), name='received-tasks'),
    path('', views.TaskCreateView.as_view(), name='task-create'),
    path('<uuid:pk>/action/', views.TaskActionView.as_view(), name='task-action'),
    path('<uuid:pk>/', views.TaskDetailView.as_view(), name='task-detail'),
    path('<uuid:task_id>/data/<uuid:field_id>/', views.TaskDataRetrieveUpdateView.as_view(), name='task-data-detail'),
    path('data-detail/', views.TaskDataDetailListView.as_view(), name='data-detail-list'),
    path('data-detail/<uuid:task_id>/', views.TaskDataDetailView.as_view(), name='data-detail'),
    path('action-detail/', views.TaskActionDetailView.as_view(), name='action-detail'),
    path('onsite-transfer-absence/', views.OnsiteTransferAbsenceView.as_view(), name='onsite-transfer-absence'),
    path('transfer-absence/', views.TransferAbsenceView.as_view(), name='transfer-absence'),
    path('overtime/', views.OvertimeView.as_view(), name='overtime')
]

