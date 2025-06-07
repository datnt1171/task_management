from django.db.models import Prefetch
from django.db import connection
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .permission_service import PermissionService
from .models import Task, TaskActionLog, TaskData
from .serializers import (ReceivedTaskSerializer, SentTaskSerializer,
                          TaskActionSerializer, TaskDetailSerializer, TaskCreateSerializer)
from process.models import Action


class SentTasksAPIView(generics.ListAPIView):
    serializer_class = SentTaskSerializer

    def get_queryset(self):
        return Task.objects.filter(created_by=self.request.user)


class ReceivedTasksAPIView(generics.ListAPIView):
    serializer_class = ReceivedTaskSerializer

    def get_queryset(self):
        user = self.request.user
        tasks = Task.objects.all()
        allowed_tasks = []

        for task in tasks:
            # Check if user has permission to perform any action on this task from current state
            possible_actions = Action.objects.filter(
                actiontransition__transition__current_state=task.state,
                process=task.process
            ).distinct()

            for action in possible_actions:
                if PermissionService.user_can_perform_action(user, task, action):
                    allowed_tasks.append(task)
                    break  # No need to check more actions for this task

        return allowed_tasks


class TaskCreateView(generics.CreateAPIView):
    serializer_class = TaskCreateSerializer
    
    
class TaskActionView(APIView):

    def post(self, request, pk):
        try:
            task = Task.objects.get(pk=pk)
        except Task.DoesNotExist:
            return Response({"detail": "Task not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = TaskActionSerializer(data=request.data, context={'request': request, 'task': task})
        if serializer.is_valid():
            serializer.save()
            return Response({"detail": "Action performed successfully."})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    
class TaskDetailView(generics.RetrieveAPIView):
    serializer_class = TaskDetailSerializer

    def get_queryset(self):
        return Task.objects.select_related(
            'process', 'state', 'created_by'
        ).prefetch_related(
            Prefetch('action_logs', queryset=TaskActionLog.objects.select_related('user', 'action')),
            Prefetch('data', queryset=TaskData.objects.select_related('field').order_by('field__order'))
        )
        

class SPRReportView(APIView):

    def get(self, request):
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    tt.id AS task_id,
                    tt.title,
                    tt.created_at,
                    uu.username,
                    uu.id as user_id,
                    wes.state_type AS state_type,
                    MAX(CASE WHEN td.field_id = '7eab39b2-4f57-4dec-ac2e-d659386d3b22' THEN td.value END) AS "Name of customer",
                    MAX(CASE WHEN td.field_id = '500c2fe9-4101-43a2-b99a-eeee0f617489' THEN td.value END) AS "Finishing code",
                    MAX(CASE WHEN td.field_id = '97786485-e4ba-48e4-87d4-1e4c84dd316d' THEN td.value END) AS "Customer's color name",
                    MAX(CASE WHEN td.field_id = '628cd098-df28-4c90-9045-d3d1b2d35395' THEN td.value END) AS "Customer/Collection",
                    MAX(CASE WHEN td.field_id = '68abbf7f-a8a4-4501-9ebc-c6e70b7db91e' THEN td.value END) AS "Quantity requirement",
                    MAX(CASE WHEN td.field_id = 'd096260a-d19e-4750-b444-9ea6a1173e2f' THEN td.value END) AS "Deadline"
                FROM task_task tt
                JOIN user_user uu ON tt.created_by_id = uu.id
                JOIN workflow_engine_state wes ON tt.state_id = wes.id
                LEFT JOIN task_taskdata td ON td.task_id = tt.id
                WHERE tt.process_id = '593b22b4-e91d-4fdc-8351-88861b1cd50e'
                GROUP BY tt.id, tt.title, tt.created_at, tt.created_by_id, uu.username, uu.id, wes.state_type
                ORDER BY tt.created_at DESC
            """)
            columns = [col[0] for col in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]

        return Response(results, status=status.HTTP_200_OK)
        
        
