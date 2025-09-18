from django.db.models import Prefetch, F
from django.db import connection
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Task, TaskActionLog, TaskData, TaskPermission
from .serializers import (ReceivedTaskSerializer, SentTaskSerializer,
                          TaskActionSerializer, TaskDetailSerializer, TaskCreateSerializer,
                          TaskDataSerializer, 
                          TaskDataDetailSerializer, TaskActionDetailSerializer)
from drf_spectacular.utils import extend_schema
from core.translation import get_localized_column
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
    

class TaskDataDetailView(APIView):
    
    @extend_schema(
        responses=TaskDataDetailSerializer(many=True),
    )
    def get(self, request):
        wes_name = get_localized_column('wes.name')

        # Parse and validate query parameters
        state_type__in = request.query_params.get('state_type__in')
        name_of_customer__in = request.query_params.get('name_of_customer__in')
        retailer__in = request.query_params.get('retailer__in')
        sampler__in = request.query_params.get('sampler__in')

        # Build main CTE query
        main_cte = f"""
            task_data AS (
                SELECT 
                    tt.id task_id,
                    tt.title,
                    tt.created_at::date created_at,
                    uu.username AS created_by,
                    {wes_name} AS state,
                    wes.state_type AS state_type,
                    MAX(CASE WHEN ppf.name = 'Name of customer' THEN ttd.value END) AS name_of_customer,
                    MAX(CASE WHEN ppf.name = 'Finishing code' THEN ttd.value END) AS finishing_code,
                    MAX(CASE WHEN ppf.name = 'Retailer' THEN ttd.value END) AS retailer,
                    MAX(CASE WHEN ppf.name = 'Customer''s color name' THEN ttd.value END) AS customer_color_name,
                    MAX(CASE WHEN ppf.name = 'Type of substrate' THEN ttd.value END) AS type_of_substrate,
                    MAX(CASE WHEN ppf.name = 'Collection' THEN ttd.value END) AS collection,
                    MAX(CASE WHEN ppf.name = 'Sample Type' THEN ttd.value END) AS sample_type,
                    MAX(CASE WHEN ppf.name = 'Quantity requirement' THEN ttd.value END) AS quantity_requirement,
                    MAX(CASE WHEN ppf.name = 'Requester name' THEN ttd.value END) AS requester_name,
                    MAX(CASE WHEN ppf.name = 'Deadline request' THEN ttd.value END) AS deadline_request,
                    MAX(CASE WHEN ppf.name = 'Sampler' THEN uu_sampler.username END) AS sampler,
                    MAX(CASE WHEN ppf.name = 'Type of paint' THEN ttd.value END) AS type_of_paint,
                    MAX(CASE WHEN ppf.name = 'Finishing surface grain' THEN ttd.value END) AS finishing_surface_grain,       
                    MAX(CASE WHEN ppf.name = 'Sheen level' THEN ttd.value END) AS sheen_level,       
                    MAX(CASE WHEN ppf.name = 'Substrate surface treatment' THEN ttd.value END) AS substrate_surface_treatment,
                    MAX(CASE WHEN ppf.name = 'Panel category' THEN ttd.value END) AS panel_category,
                    MAX(CASE WHEN ppf.name = 'Purpose of usage' THEN ttd.value END) AS purpose_of_usage,
                    MAX(CASE WHEN ppf.name = 'Additional detail' THEN ttd.value END) AS additional_detail
                FROM task_task tt
                    JOIN workflow_engine_state wes ON tt.state_id = wes.id
                    JOIN user_user uu ON tt.created_by_id = uu.id
                    JOIN task_taskdata ttd ON tt.id = ttd.task_id
                    JOIN process_processfield ppf ON ttd.field_id = ppf.id
                    LEFT JOIN user_user uu_sampler ON ttd.value = uu_sampler.id::text AND ppf.name = 'Sampler'
                WHERE tt.title LIKE 'SP%%' 
                    AND tt.created_at >= '2025-08-29'
                GROUP BY tt.id, tt.created_at::date, tt.title, uu.username, {wes_name}, wes.state_type
            )
        """

        # Build parameterized filter conditions
        filter_conditions = []
        query_params = []

        if state_type__in:
            states = [s.strip() for s in state_type__in.split(',') if s.strip()]
            if states:
                # Create placeholders for each state
                placeholders = ','.join(['%s'] * len(states))
                filter_conditions.append(f"state_type IN ({placeholders})")
                query_params.extend(states)

        if name_of_customer__in:
            customers = [s.strip() for s in name_of_customer__in.split(',') if s.strip()]
            if customers:
                placeholders = ','.join(['%s'] * len(customers))
                filter_conditions.append(f"name_of_customer IN ({placeholders})")
                query_params.extend(customers)

        if retailer__in:
            retailers = [s.strip() for s in retailer__in.split(',') if s.strip()]
            if retailers:
                placeholders = ','.join(['%s'] * len(retailers))
                filter_conditions.append(f"retailer IN ({placeholders})")
                query_params.extend(retailers)

        if sampler__in:
            samplers = [s.strip() for s in sampler__in.split(',') if s.strip()]
            if samplers:
                placeholders = ','.join(['%s'] * len(samplers))
                filter_conditions.append(f"sampler IN ({placeholders})")
                query_params.extend(samplers)

        # Build final WHERE clause
        where_clause = ""
        if filter_conditions:
            where_clause = "WHERE " + " AND ".join(filter_conditions)

        # Complete query with CTE
        query = f"""
            WITH {main_cte}
            SELECT * FROM task_data
            {where_clause}
            ORDER BY title
        """

        with connection.cursor() as cursor:                
            cursor.execute(query, query_params)  # Pass parameters separately
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            
            results = [dict(zip(columns, row)) for row in rows]
            return Response(results, status=status.HTTP_200_OK)
    

class TaskActionDetailView(APIView):
    
    @extend_schema(
        responses=TaskActionDetailSerializer(many=True),
    )
    def get(self, request):
        wes_name = get_localized_column('wes.name')
        pa_name = get_localized_column('pa.name')

        with connection.cursor() as cursor:
            cursor.execute(f"""
                SELECT 
                    tt.id as task_id,
                    tt.title, 
                    tt.created_at, 
                    uu.username AS created_by,
                    {wes_name} AS state,
                    wes.state_type AS state_type,
                    {pa_name} AS action, 
                    pa.action_type as action_type,
                    uu2.username AS action_created_by, 
                    ttal.created_at AS action_created_at, 
                    ttal.comment,
                    CASE 
                        WHEN LAG(ttal.created_at) OVER (PARTITION BY tt.id ORDER BY ttal.created_at) IS NULL 
                        THEN ttal.created_at - tt.created_at
                        WHEN LEAD(ttal.created_at) OVER (PARTITION BY tt.id ORDER BY ttal.created_at) IS NULL 
                            AND pa.action_type != 'close'
                        THEN NOW() - ttal.created_at
                        ELSE LEAD(ttal.created_at) OVER (PARTITION BY tt.id ORDER BY ttal.created_at) - ttal.created_at
                    END AS duration
                FROM task_task tt
                    JOIN workflow_engine_state wes ON tt.state_id = wes.id
                    JOIN user_user uu ON tt.created_by_id = uu.id
                    JOIN task_taskactionlog ttal ON tt.id = ttal.task_id
                    JOIN process_action pa ON ttal.action_id = pa.id
                    JOIN user_user uu2 ON ttal.user_id = uu2.id
                WHERE tt.title LIKE 'SP%'
                    AND tt.created_at >= '2025-08-29'
                ORDER BY tt.title, action_created_at;
            """)
            columns = [col[0] for col in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]

        return Response(results, status=status.HTTP_200_OK)