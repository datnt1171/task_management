from django.db.models import Prefetch, F
from django.db import connection
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Task, TaskActionLog, TaskData, TaskPermission, TaskFileData
from .serializers import (ReceivedTaskSerializer, SentTaskSerializer,
                          TaskActionSerializer, TaskDetailSerializer, TaskCreateSerializer,
                          TaskDataSerializer, 
                          TaskDataDetailSerializer, TaskActionDetailSerializer, SampleByFactorySerializer,
                          OnsiteTransferAbsenceSerializer, TransferAbsenceSerializer,
                          OvertimeSerializer)
from drf_spectacular.utils import extend_schema
from core.translation import get_localized_column
from user.permissions import HasJWTPermission
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.shortcuts import get_object_or_404
from process.models import FieldType
from rest_framework.exceptions import PermissionDenied
from datetime import datetime
from django.conf import settings


class SentTasksAPIView(generics.ListAPIView):
    serializer_class = SentTaskSerializer
    filterset_fields = {
        'state__state_type': ['exact', 'in'],
        'process__prefix': ['exact']
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
        'state__state_type': ['exact', 'in'],
        'process__prefix': ['exact']
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
    
    
class TaskFileUploadView(generics.GenericAPIView):
    def post(self, request, pk):
        """Upload files to existing task"""
        try:
            task = Task.objects.get(pk=pk)
        except Task.DoesNotExist:
            return Response(
                {"error": "Task not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        field_id = request.data.get('field_id')
        
        try:
            task_data = TaskData.objects.get(task=task, field_id=field_id)
            print("created file for task", task, field_id)
        except TaskData.DoesNotExist:
            return Response(
                {"error": "TaskData not found for this field"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        files = request.FILES.getlist('files')
        
        if not files:
            return Response(
                {"error": "No files provided"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        for file in files:
            TaskFileData.objects.create(
                task_data=task_data,
                uploaded_file=file,
                original_filename=file.name or 'unknown',
                file_size=file.size or 0,
                mime_type=getattr(file, 'content_type', '') or 'application/octet-stream'
            )
        
        return Response({
            "success": True,
            "files_uploaded": len(files)
        }, status=status.HTTP_201_CREATED)
    
    
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
        
        is_creator = task.created_by == self.request.user
        is_assistant = self.request.user.role.name == "assistant"
        
        if not (is_creator or is_assistant):
            raise PermissionDenied("Only task creator or assistants can edit task data")
        
        task_data = get_object_or_404(TaskData, task=task, field_id=self.kwargs['field_id'])
        return task_data
    
    def get_queryset(self):
        return TaskData.objects.prefetch_related('history__updated_by')
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Always handle files as list for file/multifile types
        if instance.field.field_type in [FieldType.FILE, FieldType.MULTIFILE]:
            files = request.FILES.getlist('files')  # Always get list
            data = {'files_upload': files} if files else {}
            if 'value' in request.data:
                data['value'] = request.data['value']
        else:
            data = request.data
        
        serializer = self.get_serializer(instance, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(self.get_serializer(instance).data)
    

class TaskDataDetailListView(APIView):
    
    @extend_schema(
        responses=TaskDataDetailSerializer(many=True),
    )
    def get(self, request):
        wes_name = get_localized_column('wes.name')

        # Parse and validate query parameters
        state_type__in = request.query_params.get('state_type__in')
        factory_code__in = request.query_params.get('factory_code__in')
        retailer_id__in = request.query_params.get('retailer_id__in')
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
                    MAX(CASE WHEN ppf.name = 'Name of customer' THEN ttd.value END) AS factory_code,
                    MAX(CASE WHEN ppf.name = 'Finishing code' THEN ttd.value END) AS finishing_code,
                    MAX(CASE WHEN ppf.name = 'Retailer' THEN ttd.value END) AS retailer_id,
                    MAX(CASE WHEN ppf.name = 'Customer''s color name' THEN ttd.value END) AS customer_color_name,
                    MAX(CASE WHEN ppf.name = 'Type of substrate' THEN ttd.value END) AS type_of_substrate,
                    MAX(CASE WHEN ppf.name = 'Collection' THEN ttd.value END) AS collection,
                    MAX(CASE WHEN ppf.name = 'Sample Type' THEN ttd.value END) AS sample_type,
                    MAX(CASE WHEN ppf.name = 'Quantity requirement' THEN ttd.value END) AS quantity_requirement,
                    MAX(CASE WHEN ppf.name = 'Requester name' THEN ttd.value END) AS requester_name,
                    MAX(CASE WHEN ppf.name = 'Deadline request' THEN ttd.value END) AS deadline_request,
                    MAX(CASE WHEN ppf.name = 'Sampler' THEN uu_sampler.username END) AS sampler,
                    MAX(CASE WHEN ppf.name = 'Sampler' THEN uu_sampler.id::text END) AS sampler_id,
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

        if factory_code__in:
            customers = [s.strip() for s in factory_code__in.split(',') if s.strip()]
            if customers:
                placeholders = ','.join(['%s'] * len(customers))
                filter_conditions.append(f"factory_code IN ({placeholders})")
                query_params.extend(customers)

        if retailer_id__in:
            retailers = [s.strip() for s in retailer_id__in.split(',') if s.strip()]
            if retailers:
                placeholders = ','.join(['%s'] * len(retailers))
                filter_conditions.append(f"retailer_id IN ({placeholders})")
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


class SampleByFactoryView(APIView):
    
    @extend_schema(
        responses=SampleByFactorySerializer(many=True),
    )
    def get(self, request):
        state_type__in = request.query_params.get('state_type__in')
        
        query_params = []
        where_clause = ""
        
        if state_type__in:
            states = [s.strip() for s in state_type__in.split(',') if s.strip()]
            if states:
                placeholders = ','.join(['%s'] * len(states))
                where_clause = f"AND wes.state_type IN ({placeholders})"
                query_params.extend(states)

        query = f"""
            WITH task_data AS (
                SELECT 
                    tt.id,
                    MAX(CASE WHEN ppf.name = 'Name of customer' THEN ttd.value END) AS factory_code,
                    MAX(CASE WHEN ppf.name = 'Quantity requirement' THEN ttd.value END) AS quantity
                FROM task_task tt
                    JOIN workflow_engine_state wes ON tt.state_id = wes.id
                    JOIN task_taskdata ttd ON tt.id = ttd.task_id
                    JOIN process_processfield ppf ON ttd.field_id = ppf.id
                WHERE tt.title LIKE 'SP%%' 
                    AND tt.created_at >= '2025-08-29'
                    {where_clause}
                GROUP BY tt.id
            )
            SELECT 
                factory_code,
                SUM(CAST(quantity AS INTEGER)) AS quantity_requirement
            FROM task_data
            GROUP BY factory_code
        """

        with connection.cursor() as cursor:
            cursor.execute(query, query_params)
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            
            results = [dict(zip(columns, row)) for row in rows]
            return Response(results, status=status.HTTP_200_OK)


class TaskDataDetailView(APIView):
    
    @extend_schema(
        responses=TaskDataDetailSerializer(),
    )
    def get(self, request, task_id):
        wes_name = get_localized_column('wes.name')

        query = f"""
            WITH task_data AS (
                SELECT 
                    tt.id task_id,
                    tt.title,
                    tt.created_at::date created_at,
                    uu.username AS created_by,
                    {wes_name} AS state,
                    wes.state_type AS state_type,
                    MAX(CASE WHEN ppf.name = 'Name of customer' THEN ttd.value END) AS factory_code,
                    MAX(CASE WHEN ppf.name = 'Finishing code' THEN ttd.value END) AS finishing_code,
                    MAX(CASE WHEN ppf.name = 'Retailer' THEN ttd.value END) AS retailer_id,
                    MAX(CASE WHEN ppf.name = 'Customer''s color name' THEN ttd.value END) AS customer_color_name,
                    MAX(CASE WHEN ppf.name = 'Type of substrate' THEN ttd.value END) AS type_of_substrate,
                    MAX(CASE WHEN ppf.name = 'Collection' THEN ttd.value END) AS collection,
                    MAX(CASE WHEN ppf.name = 'Sample Type' THEN ttd.value END) AS sample_type,
                    MAX(CASE WHEN ppf.name = 'Quantity requirement' THEN ttd.value END) AS quantity_requirement,
                    MAX(CASE WHEN ppf.name = 'Requester name' THEN ttd.value END) AS requester_name,
                    MAX(CASE WHEN ppf.name = 'Deadline request' THEN ttd.value END) AS deadline_request,
                    MAX(CASE WHEN ppf.name = 'Sampler' THEN uu_sampler.username END) AS sampler,
                    MAX(CASE WHEN ppf.name = 'Sampler' THEN uu_sampler.id::text END) AS sampler_id,
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
                WHERE tt.id = %s AND tt.title LIKE 'SP%%' 
                GROUP BY tt.id, tt.created_at::date, tt.title, uu.username, {wes_name}, wes.state_type
            )
            SELECT * FROM task_data
        """

        with connection.cursor() as cursor:
            cursor.execute(query, [task_id])
            columns = [col[0] for col in cursor.description]
            row = cursor.fetchone()
            
            if not row:
                return Response(
                    {"error": "Task not found"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            result = dict(zip(columns, row))
            return Response(result, status=status.HTTP_200_OK)


class TaskActionDetailView(APIView):
    
    @extend_schema(
        responses=TaskActionDetailSerializer(many=True),
    )
    def get(self, request):
        wes_name = get_localized_column('wes.name')
        pa_name = get_localized_column('pa.name')
        sp_prefix = 'SP%'
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
                WHERE tt.title LIKE %(prefix)s
                ORDER BY tt.title, action_created_at;
            """, {'prefix': sp_prefix})
            columns = [col[0] for col in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]

        return Response(results, status=status.HTTP_200_OK)
    

class OnsiteTransferAbsenceView(APIView):
    
    @extend_schema(
        responses=OnsiteTransferAbsenceSerializer(many=True),
    )
    def get(self, request):
        date = request.query_params.get('date')
    
        if not date:
            # Default to today if no date provided
            date = datetime.today().strftime('%Y-%m-%d')
        
        try:
            datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        ta_prefix = 'TA%'
        with connection.cursor() as cursor:
            cursor.execute("""
                WITH transfer_absence AS (
                    SELECT
                        MAX(CASE WHEN ppf.name = 'Name of customer' THEN ttd.value END) AS factory_code,
                        MAX(CASE WHEN ppf.name = 'username' THEN ttd.value END) AS user_id,
                        MAX(CASE WHEN ppf.name = 'Transfer type' THEN ttd.value END) AS transfer_type,
                        MAX(CASE WHEN ppf.name = 'From date' THEN ttd.value END) AS from_date,
                        MAX(CASE WHEN ppf.name = 'To date' THEN ttd.value END) AS to_date,
                        MAX(CASE WHEN ppf.name = 'Reason' THEN ttd.value END) AS reason
                    FROM task_task tt
                    JOIN task_taskdata ttd ON tt.id = ttd.task_id
                    JOIN process_processfield ppf ON ttd.field_id = ppf.id
                    WHERE tt.title LIKE %(prefix)s
                    GROUP BY tt.id
                    HAVING
                        MAX(CASE WHEN ppf.name = 'From date' THEN ttd.value END) <= %(date)s
                        AND MAX(CASE WHEN ppf.name = 'To date' THEN ttd.value END) >= %(date)s
                ),
                onsite_list AS (
                    SELECT ufo.factory, ufo.user_id, ud."name" AS dept_name
                    FROM user_userfactoryonsite ufo
                    JOIN user_user uu ON ufo.user_id = uu.id
                    JOIN user_department ud ON uu.department_id = ud.id
                    WHERE ufo.year = EXTRACT(YEAR FROM %(date)s::date) 
                        AND ufo.month = EXTRACT(MONTH FROM %(date)s::date)
                        AND uu.is_active = true
                ),
                grouped_data AS (
                    SELECT factory, dept_name, COUNT(user_id) AS count_users
                    FROM onsite_list
                    GROUP BY factory, dept_name
                ),
                factory_onsite AS (
                    SELECT
                        factory,
                        COALESCE(SUM(CASE WHEN dept_name = 'KTW' THEN count_users END), 0) AS KTW,
                        COALESCE(SUM(CASE WHEN dept_name = 'KTC' THEN count_users END), 0) AS KTC,
                        COALESCE(SUM(CASE WHEN dept_name = 'KVN' THEN count_users END), 0) AS KVN,
                        COALESCE(SUM(CASE WHEN dept_name = 'TT' THEN count_users END), 0) AS TT
                    FROM grouped_data
                    GROUP BY factory
                ),
                -- Get all factories from both onsite and transfer data
                all_factories AS (
                    SELECT DISTINCT factory FROM factory_onsite
                    UNION
                    SELECT DISTINCT factory_code FROM transfer_absence WHERE factory_code IS NOT NULL AND factory_code != ''
                ),
                -- Transfer and absence analysis CTEs
                transfer_onsite_list AS (
                    SELECT ufo.user_id, ufo.factory, ufo."year", ufo."month"
                    FROM user_userfactoryonsite ufo
                    WHERE ufo.year = EXTRACT(YEAR FROM %(date)s::date) 
                        AND ufo.month = EXTRACT(MONTH FROM %(date)s::date)
                ),
                factory_change_list AS (
                    SELECT ta.user_id, ol.factory factory_onsite, ta.factory_code AS factory_change, ta.transfer_type
                    FROM transfer_absence ta
                    LEFT JOIN transfer_onsite_list ol ON ta.user_id = ol.user_id::text
                ),
                user_info AS (
                    SELECT uu.id, ud.name AS dept_name
                    FROM user_user uu
                    JOIN user_department ud ON uu.department_id = ud.id
                ),
                factory_combined AS (
                    SELECT factory_onsite, factory_change, transfer_type, fcl.user_id, dept_name
                    FROM factory_change_list fcl
                    JOIN user_info ui ON fcl.user_id = ui.id::text
                ),
                factory_movements AS (
                    SELECT 
                        af.factory,
                        -- Incoming transfers by department
                        COALESCE(SUM(CASE WHEN fc.factory_change = af.factory AND fc.transfer_type = '調動 ĐIỀU ĐỘNG' AND fc.dept_name = 'KTW' THEN 1 END), 0) AS KTW_in,
                        COALESCE(SUM(CASE WHEN fc.factory_change = af.factory AND fc.transfer_type = '調動 ĐIỀU ĐỘNG' AND fc.dept_name = 'KTC' THEN 1 END), 0) AS KTC_in,
                        COALESCE(SUM(CASE WHEN fc.factory_change = af.factory AND fc.transfer_type = '調動 ĐIỀU ĐỘNG' AND fc.dept_name = 'KVN' THEN 1 END), 0) AS KVN_in,
                        COALESCE(SUM(CASE WHEN fc.factory_change = af.factory AND fc.transfer_type = '調動 ĐIỀU ĐỘNG' AND fc.dept_name = 'TT' THEN 1 END), 0) AS TT_in,
                        
                        -- Outgoing transfers by department
                        COALESCE(SUM(CASE WHEN fc.factory_onsite = af.factory AND fc.transfer_type = '調動 ĐIỀU ĐỘNG' AND fc.dept_name = 'KTW' AND fc.factory_change IS NOT NULL AND fc.factory_change != '' THEN 1 END), 0) AS KTW_out,
                        COALESCE(SUM(CASE WHEN fc.factory_onsite = af.factory AND fc.transfer_type = '調動 ĐIỀU ĐỘNG' AND fc.dept_name = 'KTC' AND fc.factory_change IS NOT NULL AND fc.factory_change != '' THEN 1 END), 0) AS KTC_out,
                        COALESCE(SUM(CASE WHEN fc.factory_onsite = af.factory AND fc.transfer_type = '調動 ĐIỀU ĐỘNG' AND fc.dept_name = 'KVN' AND fc.factory_change IS NOT NULL AND fc.factory_change != '' THEN 1 END), 0) AS KVN_out,
                        COALESCE(SUM(CASE WHEN fc.factory_onsite = af.factory AND fc.transfer_type = '調動 ĐIỀU ĐỘNG' AND fc.dept_name = 'TT' AND fc.factory_change IS NOT NULL AND fc.factory_change != '' THEN 1 END), 0) AS TT_out,
                        
                        -- Absences by department
                        COALESCE(SUM(CASE WHEN fc.factory_onsite = af.factory AND fc.transfer_type IN ('CL底薪假', '請假 NGHỈ PHÉP') AND fc.dept_name = 'KTW' THEN 1 END), 0) AS KTW_absence,
                        COALESCE(SUM(CASE WHEN fc.factory_onsite = af.factory AND fc.transfer_type IN ('CL底薪假', '請假 NGHỈ PHÉP') AND fc.dept_name = 'KTC' THEN 1 END), 0) AS KTC_absence,
                        COALESCE(SUM(CASE WHEN fc.factory_onsite = af.factory AND fc.transfer_type IN ('CL底薪假', '請假 NGHỈ PHÉP') AND fc.dept_name = 'KVN' THEN 1 END), 0) AS KVN_absence,
                        COALESCE(SUM(CASE WHEN fc.factory_onsite = af.factory AND fc.transfer_type IN ('CL底薪假', '請假 NGHỈ PHÉP') AND fc.dept_name = 'TT' THEN 1 END), 0) AS TT_absence
                    FROM all_factories af
                    LEFT JOIN factory_combined fc ON (af.factory = fc.factory_onsite OR af.factory = fc.factory_change)
                    GROUP BY af.factory
                )
                -- Final result combining onsite counts with movements
                SELECT 
                    COALESCE(fo.factory, fm.factory) as factory_code,
                    -- Current onsite counts
                    COALESCE(fo.KTW, 0) AS KTW_onsite,
                    COALESCE(fo.KTC, 0) AS KTC_onsite, 
                    COALESCE(fo.KVN, 0) AS KVN_onsite,
                    COALESCE(fo.TT, 0) AS TT_onsite,
                    
                    -- Transfer movements
                    COALESCE(fm.KTW_in, 0) AS KTW_in,
                    COALESCE(fm.KTC_in, 0) AS KTC_in,
                    COALESCE(fm.KVN_in, 0) AS KVN_in,
                    COALESCE(fm.TT_in, 0) AS TT_in,
                    COALESCE(fm.KTW_out, 0) AS KTW_out,
                    COALESCE(fm.KTC_out, 0) AS KTC_out,
                    COALESCE(fm.KVN_out, 0) AS KVN_out,
                    COALESCE(fm.TT_out, 0) AS TT_out,
                    
                    -- Absences
                    COALESCE(fm.KTW_absence, 0) AS KTW_absence,
                    COALESCE(fm.KTC_absence, 0) AS KTC_absence,
                    COALESCE(fm.KVN_absence, 0) AS KVN_absence,
                    COALESCE(fm.TT_absence, 0) AS TT_absence
                FROM factory_onsite fo
                FULL OUTER JOIN factory_movements fm ON fo.factory = fm.factory
                ORDER BY COALESCE(fo.factory, fm.factory);
            """, {'date': date, 'prefix': ta_prefix})
            
            columns = [col[0] for col in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]

        return Response(results, status=status.HTTP_200_OK)
    

class TransferAbsenceView(APIView):
    
    @extend_schema(
        responses=TransferAbsenceSerializer(many=True),
    )
    def get(self, request):
        start_date = request.query_params.get('date__gte')
        end_date = request.query_params.get('date__lte')
        department_param = request.query_params.get('user__department__name')
        
        department = None
        if department_param:
            department = [d.strip() for d in department_param.split(',') if d.strip()]
        
        # Both start_date and end_date are required
        if not start_date or not end_date:
            today = datetime.today().strftime('%Y-%m-%d')
            start_date = end_date = today
        
        # Validate date formats
        try:
            datetime.strptime(start_date, '%Y-%m-%d')
            datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate that start_date is before end_date
        if start_date > end_date:
            return Response(
                {"error": "start_date must be before or equal to end_date"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        ta_prefix = 'TA%'
        
        # Build the WHERE clause dynamically based on whether department is provided
        department_filter = ""
        params = {
            'start_date': start_date, 
            'end_date': end_date, 
            'prefix': ta_prefix
        }
        
        if department:
            department_filter = "AND ud.name IN %(department)s"
            params['department'] = tuple(department)  # Convert to tuple for SQL IN clause
        
        with connection.cursor() as cursor:
            cursor.execute(f"""
                WITH transfer_absence AS (
                    SELECT
                        tt.id as task_id,
                        MAX(CASE WHEN ppf.name = 'Name of customer' THEN ttd.value END) AS factory_code,
                        MAX(CASE WHEN ppf.name = 'username' THEN ttd.value END) AS user_id,
                        MAX(CASE WHEN ppf.name = 'Transfer type' THEN ttd.value END) AS transfer_type,
                        MAX(CASE WHEN ppf.name = 'From date' THEN ttd.value END) AS from_date,
                        MAX(CASE WHEN ppf.name = 'To date' THEN ttd.value END) AS to_date,
                        MAX(CASE WHEN ppf.name = 'Reason' THEN ttd.value END) AS reason
                    FROM task_task tt
                    JOIN task_taskdata ttd ON tt.id = ttd.task_id
                    JOIN process_processfield ppf ON ttd.field_id = ppf.id
                    WHERE tt.title LIKE %(prefix)s
                    GROUP BY tt.id
                ),
                onsite as (
                    SELECT DISTINCT user_id as user_id_onsite, factory as factory_code_onsite
                    FROM user_userfactoryonsite
                    WHERE year = EXTRACT(YEAR FROM %(start_date)s::date) 
                        AND month = EXTRACT(MONTH FROM %(start_date)s::date)
                )
                SELECT 
                    task_id,
                    ta.factory_code, ta.user_id,
                    ta.transfer_type, ta.from_date, ta.to_date, ta.reason,
                    uu.username, uu.first_name, uu.last_name, ud.name as department,
                    factory_code_onsite
                FROM transfer_absence ta
                    JOIN user_user uu ON uu.id::text = ta.user_id
                    JOIN user_department ud ON uu.department_id = ud.id
                    LEFT JOIN onsite os ON os.user_id_onsite = uu.id
                WHERE (ta.from_date <= %(end_date)s AND ta.to_date >= %(start_date)s)
                    {department_filter}
            """, params)
            
            columns = [col[0] for col in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]

        return Response(results, status=status.HTTP_200_OK)
    

class OvertimeView(APIView):
    
    @extend_schema(
        responses=OvertimeSerializer(many=True),
    )
    def get(self, request):
        start_date = request.query_params.get('date__gte')
        end_date = request.query_params.get('date__lte')
        
        # Both start_date and end_date are required
        if not start_date or not end_date:
            today = datetime.today().strftime('%Y-%m-%d')
            start_date = end_date = today
        
        # Validate date formats
        try:
            datetime.strptime(start_date, '%Y-%m-%d')
            datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate that start_date is before end_date
        if start_date > end_date:
            return Response(
                {"error": "start_date must be before or equal to end_date"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        dr_prefix = 'DR%'
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    tt.id as task_id,
                    MAX(CASE WHEN ppf.name = 'Name of customer' THEN ttd.value END) AS factory_code,
                    MAX(CASE WHEN ppf.name = 'Weekday overtime' THEN ttd.value END) AS weekday_ot,
                    MAX(CASE WHEN ppf.name = 'Overtime start time today' THEN ttd.value END) AS weekday_ot_start,
                    MAX(CASE WHEN ppf.name = 'Overtime end time today' THEN ttd.value END) AS weekday_ot_end,
                    MAX(CASE WHEN ppf.name = 'Number of overtime workers today' THEN ttd.value END) AS weekday_ot_num,
                    MAX(CASE WHEN ppf.name = 'Hanging line today' THEN ttd.value END) AS hanging_line_today,
                    MAX(CASE WHEN ppf.name = 'Pallet line today' THEN ttd.value END) AS pallet_line_today,
                    MAX(CASE WHEN ppf.name = 'Others task today' THEN ttd.value END) AS others_today,
                    MAX(CASE WHEN ppf.name = 'Hanging line tomorrow' THEN ttd.value END) AS hanging_line_tomorrow,
                    MAX(CASE WHEN ppf.name = 'Pallet line tomorrow' THEN ttd.value END) AS pallet_line_tomorrow,
                    MAX(CASE WHEN ppf.name = 'Others task tomorrow' THEN ttd.value END) AS others_tomorrow,
                    MAX(CASE WHEN ppf.name = 'Customer in stock status' THEN ttd.value END) AS instock,
                    MAX(CASE WHEN ppf.name = 'Customer in stock status for each color code' THEN ttd.value END) AS instock_by_code,       
                    MAX(CASE WHEN ppf.name = 'Sunday overtime' THEN ttd.value END) AS sunday_ot,       
                    MAX(CASE WHEN ppf.name = 'Sunday overtime end time' THEN ttd.value END) AS sunday_ot_end,
                    MAX(CASE WHEN ppf.name = 'Number of overtime workers sunday' THEN ttd.value END) AS sunday_ot_num,
                    MAX(CASE WHEN ppf.name = 'Hanging line sunday' THEN ttd.value END) AS hanging_line_sunday,
                    MAX(CASE WHEN ppf.name = 'Pallet line sunday' THEN ttd.value END) AS pallet_line_sunday,
                    COALESCE(
                        json_agg(
                            json_build_object(
                                'url', ttfd.uploaded_file,
                                'filename', ttfd.original_filename,
                                'size', ttfd.file_size,
                                'mime_type', ttfd.mime_type
                            )
                        ) FILTER (WHERE ttfd.id IS NOT NULL),
                        '[]'::json
                    ) as files,
                    tt.created_at 
                FROM task_task tt
                    JOIN task_taskdata ttd ON tt.id = ttd.task_id
                    JOIN process_processfield ppf ON ttd.field_id = ppf.id
                    LEFT JOIN task_taskfiledata ttfd ON ttd.id = ttfd.task_data_id
                WHERE tt.title LIKE %(prefix)s
                    AND DATE(tt.created_at) BETWEEN %(start_date)s AND %(end_date)s
                GROUP BY tt.id, tt.created_at
            """, {'start_date': start_date, 'end_date': end_date, 'prefix': dr_prefix})
            
            columns = [col[0] for col in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]

        domain = getattr(settings, 'DOMAIN_URL', '')
        for result in results:
            if result.get('files'):
                for file in result['files']:
                    if file.get('url'):
                        if domain:
                            file['url'] = f"{domain}/media/{file['url']}"
                        else:
                            file['url'] = f"{request.build_absolute_uri('/media/')}{file['url']}"

        return Response(results, status=status.HTTP_200_OK)