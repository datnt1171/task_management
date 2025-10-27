from django.db import transaction
from django.conf import settings
from rest_framework import serializers
from .models import Task, TaskData, TaskActionLog, generate_task_title, TaskFileData, TaskPermission, TaskDataHistory
from process.models import ProcessField, Action, FieldType
from process.serializers import ProcessFieldSerializer, ProcessSerializer, ActionSerializer
from workflow_engine.models import State, Transition
from workflow_engine.serializers import StateSerializer
from .permission_service import PermissionService
from user.serializers import UserSerializer
from user.models import User
from drf_spectacular.utils import extend_schema_field
from core.utils import FileValidator
import json
from datetime import datetime
from .tasks import send_task_notification


class SentTaskSerializer(serializers.ModelSerializer):
    process = serializers.CharField(source='process.name')
    recipient = serializers.SerializerMethodField()
    state = serializers.CharField(source='state.name')
    state_type = serializers.CharField(source='state.state_type')
    finishing_code = serializers.SerializerMethodField()
    customer_color_name = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = ['id', 'title', 'process', 'state', 'state_type', 'created_at', 
                 'recipient', 'finishing_code', 'customer_color_name']

    def get_recipient(self, obj) -> str | None:
        """
        Single query optimization - get all permissions for this task at once.
        """
        # Get possible actions and their permissions in one query
        permissions = TaskPermission.objects.filter(
            task=obj,
            action__actiontransition__transition__current_state=obj.state,
            action__process=obj.process
        ).select_related('user', 'action').distinct()
        
        # Return first available user
        if permissions:
            return permissions[0].user.username
        return None

    def get_finishing_code(self, obj) -> str | None:
        """Get finishing code for SP tasks only."""
        if not obj.title.startswith('SP'):
            return None
        try:
            task_data = obj.data.select_related('field').get(field__name='Finishing code')
            return task_data.value
        except:
            return None

    def get_customer_color_name(self, obj) -> str | None:
        """Get customer color name for SP tasks only."""
        if not obj.title.startswith('SP'):
            return None
        try:
            task_data = obj.data.select_related('field').get(field__name="Customer's color name")
            return task_data.value
        except:
            return None


class ReceivedTaskSerializer(serializers.ModelSerializer):
    process = serializers.CharField(source='process.name')
    created_by = serializers.CharField(source='created_by.username')
    state = serializers.CharField(source='state.name')
    state_type = serializers.CharField(source='state.state_type')
    action = serializers.SerializerMethodField()
    finishing_code = serializers.SerializerMethodField()
    customer_color_name = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = ['id', 'title', 'process', 'state', 'state_type', 'created_at', 'created_by', 'action',
                  'finishing_code', 'customer_color_name']

    def get_action(self, obj) -> str | None:
        """
        Single query optimization for current user's permissions.
        """
        user = self.context['request'].user
        
        # Get user's permissions for current state actions in one query
        permission = TaskPermission.objects.filter(
            task=obj,
            user=user,
            action__actiontransition__transition__current_state=obj.state,
            action__process=obj.process
        ).select_related('action').first()
        
        return permission.action.name if permission else None
    
    def get_finishing_code(self, obj) -> str | None:
        """Get finishing code for SP tasks only."""
        if not obj.title.startswith('SP'):
            return None
        try:
            task_data = obj.data.select_related('field').get(field__name='Finishing code')
            return task_data.value
        except:
            return None

    def get_customer_color_name(self, obj) -> str | None:
        """Get customer color name for SP tasks only."""
        if not obj.title.startswith('SP'):
            return None
        try:
            task_data = obj.data.select_related('field').get(field__name="Customer's color name")
            return task_data.value
        except:
            return None
     
        
class TaskDataInputSerializer(serializers.Serializer):
    field_id = serializers.UUIDField()
    value = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    files = serializers.ListField(
        child=serializers.FileField(),
        required=False,
        allow_empty=True
    )

class TaskCreateSerializer(serializers.ModelSerializer):
    fields = TaskDataInputSerializer(many=True, write_only=True)

    class Meta:
        model = Task
        fields = ['process', 'fields']

    def to_representation(self, instance):
        return {
            'id': instance.id,
            'title': instance.title,
            'state': instance.state.name if instance.state else None,
            'created_at': instance.created_at.isoformat() if hasattr(instance, 'created_at') else None,
            'process_prefix': instance.process.prefix
        }

    def to_internal_value(self, data):
        if hasattr(data, 'getlist'):
            fields_data = []
            field_indices = set()
            
            for key in data.keys():
                if key.startswith('fields[') and '][' in key:
                    index = key.split('[')[1].split(']')[0]
                    field_indices.add(int(index))
            
            for index in sorted(field_indices):
                field_data = {}
                field_id_key = f'fields[{index}][field_id]'
                value_key = f'fields[{index}][value]'
                files_key = f'fields[{index}][files]'
                
                if field_id_key in data:
                    field_data['field_id'] = data[field_id_key]
                if value_key in data:
                    field_data['value'] = data[value_key]
                
                if files_key in data:
                    files_list = data.getlist(files_key)
                    field_data['files'] = files_list
                
                fields_data.append(field_data)
            
            processed_data = {
                'process': data.get('process'),
                'fields': fields_data
            }
            return super().to_internal_value(processed_data)
        
        return super().to_internal_value(data)

    def validate_process(self, process):
        if not process.is_active:
            raise serializers.ValidationError("This process is inactive.")
        return process

    def validate_fields(self, fields_data):
        if not fields_data:
            raise serializers.ValidationError("At least one field is required.")
        return fields_data

    def create(self, validated_data):
        user = self.context['request'].user
        process = validated_data['process']
        field_data_list = validated_data.pop('fields')

        start_state = State.objects.filter(
            state_type='start',
            transitions_from__process=process
        ).distinct().first()

        if not start_state:
            start_state = State.objects.get(state_type='static')

        with transaction.atomic():
            task = Task.objects.create(
                process=process,
                created_by=user,
                state=start_state,
                title=generate_task_title(process)
            )

            for field_data in field_data_list:
                field_id = field_data.get('field_id')
                try:
                    field_obj = ProcessField.objects.get(id=field_id, process=process)
                except ProcessField.DoesNotExist:
                    raise serializers.ValidationError(
                        {"non_field_errors": [f"Field ID {field_id} is invalid for this process."]}
                    )

                field_value = field_data.get('value')
                
                TaskData.objects.create(
                    task=task,
                    field=field_obj,
                    value=field_value
                )
            
            PermissionService.create_task_permissions(task)

            send_task_notification.delay_on_commit(
                task_id=str(task.id),
                state_id=str(start_state.id),
                exclude_user_id=user.id
            )
            
        return task


class TaskActionSerializer(serializers.Serializer):
    action_id = serializers.UUIDField()
    comment = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    file = serializers.FileField(required=False, allow_null=True)
    
    def validate(self, attrs):
        user = self.context['request'].user
        task = self.context['task']
        action_id = attrs['action_id']

        try:
            action = Action.objects.get(id=action_id, process=task.process)
        except Action.DoesNotExist:
            raise serializers.ValidationError({"non_field_errors": ["Invalid action for this process."]})
        
        # Check permission via PermissionService
        if not PermissionService.user_can_perform_action(user, task, action):
            raise serializers.ValidationError({"non_field_errors": ["You do not have permission to perform this action."]})
        
        try:
            transition = Transition.objects.get(
                process=task.process,
                current_state=task.state,
                actiontransition__action=action
            )
        except Transition.DoesNotExist:
            raise serializers.ValidationError({"non_field_errors": ["No valid transition from current state for this action."]})
        
        attrs['action'] = action
        attrs['transition'] = transition
        return attrs
    
    def save(self, **kwargs):
        task = self.context['task']
        user = self.context['request'].user
        action = self.validated_data['action']
        transition = self.validated_data['transition']
        comment = self.validated_data.get('comment', '')
        file = self.validated_data.get('file')
        
        # Perform state transition
        task.state = transition.next_state
        task.save()
        
        # Log action
        TaskActionLog.objects.create(
            task=task,
            user=user,
            action=action,
            comment=comment,
            file=file
        )
        
        # Send notification
        send_task_notification.delay_on_commit(
            task_id=str(task.id),
            state_id=str(transition.next_state.id),
            exclude_user_id=user.id
        )
        
        return task


class TaskFileDataSerializer(serializers.ModelSerializer):
    uploaded_file = serializers.SerializerMethodField()
    class Meta:
        model = TaskFileData
        fields = ['original_filename', 'uploaded_file', 'uploaded_at']
    
    def get_uploaded_file(self, obj):
        if obj.uploaded_file:
            # Use the configured domain URL instead of request-based URL
            domain = getattr(settings, 'DOMAIN_URL', '')
            if domain:
                return f"{domain}{obj.uploaded_file.url}"
            
            # Fallback to request-based URL
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.uploaded_file.url)
            
            # Last fallback - relative URL
            return obj.uploaded_file.url
        return None

class TaskDataHistorySerializer(serializers.ModelSerializer):
    updated_by = serializers.StringRelatedField()
    
    class Meta:
        model = TaskDataHistory
        fields = ['value', 'updated_by', 'updated_at']


class TaskDataSerializer(serializers.ModelSerializer):
    field = serializers.SerializerMethodField()
    files = TaskFileDataSerializer(many=True, read_only=True)
    files_upload = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=False,
        allow_empty=True
    )
    history = TaskDataHistorySerializer(many=True, read_only=True)
    value = serializers.CharField(allow_blank=True, allow_null=True, required=False)
    
    class Meta:
        model = TaskData
        fields = ['field', 'value', 'files', 'files_upload', 'history']
    
    @extend_schema_field(ProcessFieldSerializer)
    def get_field(self, obj):
        return ProcessFieldSerializer(obj.field).data
    
    def get_value(self, obj):
        if obj.field.field_type == 'assignee' and obj.value:
            try:
                user = User.objects.get(id=obj.value)
                return str(user)
            except (User.DoesNotExist, ValueError):
                return obj.value
        return obj.value
    
    def to_representation(self, instance):
        """Custom representation for GET requests"""
        data = super().to_representation(instance)
        data['value'] = self.get_value(instance)
        return data
    
    def update(self, instance, validated_data):
        files_upload = validated_data.pop('files_upload', None)
        
        # Update with history tracking
        new_value = validated_data.get('value')
        if new_value is not None:
            instance.save_with_history(
                user=self.context.get('request').user, 
                new_value=new_value
            )
        else:
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()
        
        if instance.field.field_type in [FieldType.FILE, FieldType.MULTIFILE] and files_upload:
            
            for file in files_upload:
                TaskFileData.objects.create(
                    task_data=instance,
                    uploaded_file=file,
                    original_filename=file.name or 'unknown',
                    file_size=file.size or 0,
                    mime_type=getattr(file, 'content_type', '') or 'application/octet-stream'
                )
        
        return instance


class TaskActionLogSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    action = ActionSerializer()
    file = serializers.SerializerMethodField()

    class Meta:
        model = TaskActionLog
        fields = ['id', 'user', 'action', 'created_at', 'comment', 'file']

    def get_file(self, obj):
        if obj.file:
            # Use the configured domain URL instead of request-based URL
            domain = getattr(settings, 'DOMAIN_URL', '')
            if domain:
                return f"{domain}{obj.file.url}"
            
            # Fallback to request-based URL
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            
            # Last fallback - relative URL
            return obj.file.url
        return None


class TaskDetailSerializer(serializers.ModelSerializer):
    process = ProcessSerializer()
    state = StateSerializer()
    created_by = UserSerializer()
    data = TaskDataSerializer(many=True)
    action_logs = TaskActionLogSerializer(many=True)
    available_actions = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            'id', 'title', 'process', 'state', 'created_by', 'created_at',
            'data', 'action_logs', 'available_actions'
        ]

    @extend_schema_field(ActionSerializer(many=True))
    def get_available_actions(self, obj):
        user = self.context['request'].user

        transitions = Transition.objects.filter(
            process=obj.process,
            current_state=obj.state
        )

        actions = Action.objects.filter(
            actiontransition__transition__in=transitions
        ).distinct()

        permitted = []
        for action in actions:
            if PermissionService.user_can_perform_action(user, obj, action):
                permitted.append({
                    'id': action.id,
                    'name': action.name,
                    'description': action.description,
                    'action_type': action.action_type
                })

        return permitted


class TaskDataDetailSerializer(serializers.Serializer):
    task_id = serializers.UUIDField()
    title = serializers.CharField()
    created_at = serializers.DateField()
    created_by = serializers.CharField()
    state = serializers.CharField()
    state_type = serializers.CharField()
    factory_code = serializers.CharField()
    finishing_code = serializers.CharField()
    retailer_id = serializers.CharField()
    customer_color_name = serializers.CharField()
    type_of_substrate = serializers.CharField()
    collection = serializers.CharField()
    sample_type = serializers.CharField()
    quantity_requirement = serializers.CharField()
    requester_name = serializers.CharField()
    deadline_request = serializers.CharField()
    sampler = serializers.CharField()
    sampler_id = serializers.CharField()
    type_of_paint = serializers.CharField()
    finishing_surface_grain = serializers.CharField()
    sheen_level = serializers.CharField()
    substrate_surface_treatment = serializers.CharField()
    panel_category = serializers.CharField()
    purpose_of_usage = serializers.CharField()
    additional_detail = serializers.CharField()


class SampleByFactorySerializer(serializers.Serializer):
    factory_code = serializers.CharField()
    quantity_requirement = serializers.IntegerField()

class TaskActionDetailSerializer(serializers.Serializer):
    task_id = serializers.UUIDField()
    title = serializers.CharField()
    created_at = serializers.DateTimeField()
    created_by = serializers.CharField()
    state = serializers.CharField()
    state_type = serializers.CharField()
    action = serializers.CharField()
    action_type = serializers.CharField()
    action_created_by = serializers.CharField()
    action_created_at = serializers.DateTimeField()
    comment = serializers.CharField()
    duration = serializers.DurationField()


class OnsiteTransferAbsenceSerializer(serializers.Serializer):
    factory_code = serializers.CharField()

    ktw_onsite = serializers.IntegerField()
    ktc_onsite = serializers.IntegerField()
    kvn_onsite = serializers.IntegerField()
    tt_onsite = serializers.IntegerField()

    ktw_in = serializers.IntegerField()
    ktc_in = serializers.IntegerField()
    kvn_in = serializers.IntegerField()
    tt_in = serializers.IntegerField()

    ktw_out = serializers.IntegerField()
    ktc_out = serializers.IntegerField()
    kvn_out = serializers.IntegerField()
    tt_out = serializers.IntegerField()

    ktw_absence = serializers.IntegerField()
    ktc_absence = serializers.IntegerField()
    kvn_absence = serializers.IntegerField()
    tt_absence = serializers.IntegerField()


class TransferAbsenceSerializer(serializers.Serializer):
    task_id = serializers.CharField()
    factory_code = serializers.CharField()
    user_id = serializers.CharField()
    transfer_type = serializers.CharField()
    from_date = serializers.DateField()
    to_date = serializers.DateField()
    reason = serializers.CharField()
    username = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    department = serializers.CharField()
    factory_code_onsite = serializers.CharField()


class OvertimeSerializer(serializers.Serializer):
    task_id = serializers.CharField()
    factory_code = serializers.CharField()
    weekday_ot = serializers.CharField()
    weekday_ot_start = serializers.TimeField()
    weekday_ot_end = serializers.TimeField()
    weekday_ot_num = serializers.IntegerField()
    hanging_line_today = serializers.CharField()
    pallet_line_today = serializers.CharField()
    others_today = serializers.CharField()
    hanging_line_tomorrow = serializers.CharField()
    pallet_line_tomorrow = serializers.CharField()
    others_tomorrow = serializers.CharField()
    instock = serializers.CharField()
    instock_by_code = serializers.CharField()
    sunday_ot = serializers.CharField()
    sunday_ot_end = serializers.TimeField()
    sunday_ot_num = serializers.IntegerField()
    hanging_line_sunday = serializers.CharField()
    pallet_line_sunday = serializers.CharField()
    num_of_ppl = serializers.IntegerField()
    name_of_ppl = serializers.CharField()
    files = serializers.ListField(child=serializers.DictField(), required=False)
    created_at = serializers.DateField()