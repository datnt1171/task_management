from django.db.models import Prefetch, F
from django.db import connection
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Task, TaskActionLog, TaskData, TaskPermission
from .serializers import (ReceivedTaskSerializer, SentTaskSerializer,
                          TaskActionSerializer, TaskDetailSerializer, TaskCreateSerializer,
                          SPRReportRowSerializer, TaskDataSerializer)
from drf_spectacular.utils import extend_schema
from django.utils.translation import get_language
from user.permissions import HasJWTPermission
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.shortcuts import get_object_or_404
from process.models import FieldType
from rest_framework.exceptions import PermissionDenied


class SentTasksAPIView(generics.ListAPIView):
    serializer_class = SentTaskSerializer
    filterset_fields = {
        'state__state_type': ['exact', 'in']
    }
    search_fields = ['title']

    def get_queryset(self):
        # Add prefetching for better performance in serializers
        return Task.objects.filter(
            created_by=self.request.user
        ).select_related(
            'process', 'state', 'created_by'
        ).prefetch_related(
            'taskpermission_set__user',
            'taskpermission_set__action'
        )


class ReceivedTasksAPIView(generics.ListAPIView):
    serializer_class = ReceivedTaskSerializer
    filterset_fields = {
        'state__state_type': ['exact', 'in']
    }
    search_fields = ['title']

    def get_queryset(self):
        user = self.request.user
        
        # Single complex query to get all tasks user can act on from current state
        return Task.objects.filter(
            # User has permission for this task
            id__in=TaskPermission.objects.filter(user=user).values_list('task_id', flat=True)
        ).filter(
            # And the action is available from current state
            taskpermission__user=user,
            taskpermission__action__actiontransition__transition__current_state=F('state')
        ).select_related(
            'process', 'state', 'created_by'
        ).prefetch_related(
            'taskpermission_set__user',
            'taskpermission_set__action'
        ).distinct()


class TaskCreateView(generics.CreateAPIView):
    serializer_class = TaskCreateSerializer
    
    
class TaskActionView(generics.GenericAPIView):
    serializer_class = TaskActionSerializer

    def post(self, request, pk):
        try:
            task = Task.objects.get(pk=pk)
        except Task.DoesNotExist:
            return Response({"detail": "Task not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(data=request.data, context={'request': request, 'task': task})
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
    permission_classes = [HasJWTPermission]
    required_permission = 'read.task.sample-request'
    
    @extend_schema(
        responses=SPRReportRowSerializer(many=True),
        description="Returns a report of tasks for a specific process using raw SQL."
    )
    def get(self, request):
        lang = get_language()  # e.g. 'vi', 'en'
        if lang == 'zh-hant':
            lang = 'zh_hant'
        translated_column = f"wes.name_{lang}"  # Use modeltranslation's convention

        allowed_columns = {'wes.name_en', 'wes.name_vi','wes.name_zh_hant'}
        if translated_column not in allowed_columns:
            translated_column = "wes.name"

        with connection.cursor() as cursor:
            cursor.execute(f"""
                SELECT 
                    tt.id AS task_id,
                    tt.title,
                    tt.created_at,
                    uu.username as created_by,
                    uu.id as user_id,
                    {translated_column} AS state,
                    wes.state_type AS state_type,
                    MAX(CASE WHEN pp2.name = 'Name of customer' THEN td.value END) AS customer_name,
                    MAX(CASE WHEN pp2.name = 'Finishing code' THEN td.value END) AS finishing_code,
                    MAX(CASE WHEN pp2.name = 'Customer''s color name' THEN td.value END) AS customer_color_name,
                    MAX(CASE WHEN pp2.name = 'Collection' THEN td.value END) AS collection,
                    MAX(CASE WHEN pp2.name = 'Quantity requirement' THEN td.value END) AS quantity,
                    MAX(CASE WHEN pp2.name = 'Deadline request' THEN td.value END) AS deadline
                FROM task_task tt
                JOIN user_user uu ON tt.created_by_id = uu.id
                JOIN workflow_engine_state wes ON tt.state_id = wes.id
                LEFT JOIN task_taskdata td ON td.task_id = tt.id
                join process_process pp on tt.process_id = pp.id
                join process_processfield pp2 on td.field_id = pp2.id
                WHERE pp.prefix = 'SP'
                GROUP BY tt.id, tt.title, tt.created_at, tt.created_by_id, uu.username, uu.id, wes.state_type, {translated_column}
                ORDER BY tt.created_at DESC
            """)
            columns = [col[0] for col in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]

        return Response(results, status=status.HTTP_200_OK)
        
        
class TaskDataRetrieveUpdateView(generics.RetrieveUpdateAPIView):
    serializer_class = TaskDataSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def get_object(self):
        task = get_object_or_404(Task, id=self.kwargs['task_id'])
        
        # Only task creator can edit task data
        if task.created_by != self.request.user:
            raise PermissionDenied("Only task creator can edit task data")
        
        task_data = get_object_or_404(TaskData, task=task, field_id=self.kwargs['field_id'])
        return task_data
    
    def get_queryset(self):
        # Prefetch history for performance
        return TaskData.objects.prefetch_related('history__updated_by')
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Handle file upload for FILE type fields  
        if instance.field.field_type == FieldType.FILE:
            file = request.FILES.get('file')
            data = {'file': file} if file else {}
            if 'value' in request.data:
                data['value'] = request.data['value']
        else:
            data = request.data
        
        serializer = self.get_serializer(instance, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        # Return fresh data after update
        return Response(self.get_serializer(instance).data)