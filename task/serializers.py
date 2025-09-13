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


class SentTaskSerializer(serializers.ModelSerializer):
    process = serializers.CharField(source='process.name')
    recipient = serializers.SerializerMethodField()
    state = serializers.CharField(source='state.name')
    state_type = serializers.CharField(source='state.state_type')

    class Meta:
        model = Task
        fields = ['id', 'title', 'process', 'state', 'state_type', 'created_at', 'recipient']

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


class ReceivedTaskSerializer(serializers.ModelSerializer):
    process = serializers.CharField(source='process.name')
    created_by = serializers.CharField(source='created_by.username')
    state = serializers.CharField(source='state.name')
    state_type = serializers.CharField(source='state.state_type')
    action = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = ['id', 'title', 'process', 'state', 'state_type', 'created_at', 'created_by', 'action']

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
     
        
class TaskDataInputSerializer(serializers.Serializer):
    field_id = serializers.UUIDField()
    value = serializers.CharField(allow_blank=True, allow_null=True, required=False)
    file = serializers.FileField(required=False)

    def validate(self, data):
        """Ensure either value or file is provided, but not both for file fields"""
        field_id = data.get('field_id')
        value = data.get('value')
        file = data.get('file')
        
        if value and file:
            # Handle your business logic here
            pass
        
        return data

class TaskCreateSerializer(serializers.ModelSerializer):
    fields = TaskDataInputSerializer(many=True, write_only=True)

    class Meta:
        model = Task
        fields = ['process', 'fields']

    def to_internal_value(self, data):
        # Handle FormData structure from frontend
        if hasattr(data, 'getlist'):  # FormData from frontend
            fields_data = []
            field_indices = set()
            
            # Extract all field indices
            for key in data.keys():
                if key.startswith('fields[') and '][' in key:
                    index = key.split('[')[1].split(']')[0]
                    field_indices.add(int(index))
            
            # Build fields array
            for index in sorted(field_indices):
                field_data = {}
                field_id_key = f'fields[{index}][field_id]'
                value_key = f'fields[{index}][value]'
                file_key = f'fields[{index}][file]'
                
                if field_id_key in data:
                    field_data['field_id'] = data[field_id_key]
                if value_key in data:
                    field_data['value'] = data[value_key]
                if file_key in data:
                    field_data['file'] = data[file_key]
                    
                fields_data.append(field_data)
            
            # Reconstruct data
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
        """Validate fields data"""
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
            # raise serializers.ValidationError({"non_field_errors": ["No start state is defined for this process."]})
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
                    raise serializers.ValidationError({"non_field_errors": [f"Field ID {field_id} is invalid for this process."]})

                # Validate field type vs provided data
                uploaded_file = field_data.get('file')
                field_value = field_data.get('value')
                # # If field type is file but no file provided, and it's required
                # if field_obj.field_type == 'file' and not uploaded_file and field_obj.required:
                #     raise serializers.ValidationError(f"File is required for field '{field_obj.name}'")
                
                # # If field type is not file but file is provided
                # if field_obj.field_type != 'file' and uploaded_file:
                #     raise serializers.ValidationError(f"Field '{field_obj.name}' does not accept files")

                task_data = TaskData.objects.create(
                    task=task,
                    field=field_obj,
                    value=field_value
                )

                # If file is included, create TaskFileData
                if uploaded_file:
                    TaskFileData.objects.create(
                        task_data=task_data,
                        uploaded_file=uploaded_file,
                        original_filename=uploaded_file.name or 'unknown',
                        file_size=uploaded_file.size or 0,
                        # Handle cases where content_type might be None
                        mime_type=getattr(uploaded_file, 'content_type', '') or 'application/octet-stream'
                    )
            PermissionService.create_task_permissions(task)

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
    history = TaskDataHistorySerializer(many=True, read_only=True)
    value = serializers.CharField(allow_blank=True, allow_null=True, required=False)
    file = serializers.FileField(required=False, write_only=True)
    
    class Meta:
        model = TaskData
        fields = ['field', 'value', 'files', 'file', 'history']
    
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
        # Use custom logic for displaying value
        data['value'] = self.get_value(instance)
        return data
    
    def validate_value(self, value):
        field = self.instance.field if self.instance else None
        if not field or not value:
            return value
            
        # Field-type specific validation
        if field.field_type == FieldType.NUMBER:
            try:
                float(value)
            except (ValueError, TypeError):
                raise serializers.ValidationError("Value must be a valid number")
                
        elif field.field_type == FieldType.DATE:
            try:
                datetime.strptime(value, '%Y-%m-%d')
            except ValueError:
                raise serializers.ValidationError("Value must be in YYYY-MM-DD format")
                
        elif field.field_type == FieldType.SELECT:
            if field.options and 'choices' in field.options:
                valid_choices = [choice['value'] for choice in field.options['choices']]
                if value not in valid_choices:
                    raise serializers.ValidationError(f"Value must be one of: {valid_choices}")
                    
        elif field.field_type == FieldType.JSON:
            try:
                json.loads(value)
            except json.JSONDecodeError:
                raise serializers.ValidationError("Value must be valid JSON")
                
        elif field.field_type == FieldType.ASSIGNEE:
            try:
                User.objects.get(id=value)
            except (User.DoesNotExist, ValueError):
                raise serializers.ValidationError("Invalid user ID")
                
        return value
    
    def update(self, instance, validated_data):
        file = validated_data.pop('file', None)
        
        # Update with history tracking
        new_value = validated_data.get('value')
        if new_value is not None:
            instance.save_with_history(user=self.context.get('request').user, 
                                       new_value=new_value)
        else:
            # Update other fields without history
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()
        
        # Handle file upload for FILE type fields
        if instance.field.field_type == FieldType.FILE and file:
            # Keep existing files and add new one (no deletion)
            TaskFileData.objects.create(
                task_data=instance,
                uploaded_file=file,
                original_filename=file.name,
                file_size=file.size,
                mime_type=getattr(file, 'content_type', '')
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


class SPRReportRowSerializer(serializers.Serializer):
    task_id = serializers.UUIDField()
    title = serializers.CharField()
    created_at = serializers.DateTimeField()
    created_by = serializers.CharField()
    user_id = serializers.UUIDField()
    state = serializers.CharField()
    state_type = serializers.CharField()
    customer_name = serializers.CharField()
    finishing_code = serializers.CharField()
    customer_color_name = serializers.CharField()
    collection = serializers.CharField()
    quantity = serializers.CharField()
    deadline = serializers.CharField()


class TaskDataDetailSerializer(serializers.Serializer):
    task_id = serializers.UUIDField()
    title = serializers.CharField()
    created_at = serializers.DateField()
    created_by = serializers.CharField()
    state = serializers.CharField()
    state_type = serializers.CharField()
    name_of_customer = serializers.CharField(allow_null=True)
    finishing_code = serializers.CharField(allow_null=True)
    retailer = serializers.CharField(allow_null=True)
    customer_color_name = serializers.CharField(allow_null=True)
    type_of_substrate = serializers.CharField(allow_null=True)
    collection = serializers.CharField(allow_null=True)
    sample_type = serializers.CharField(allow_null=True)
    quantity_requirement = serializers.CharField(allow_null=True)
    requester_name = serializers.CharField(allow_null=True)
    deadline_request = serializers.CharField(allow_null=True)
    sampler = serializers.CharField(allow_null=True)
    type_of_paint = serializers.CharField(allow_null=True)
    finishing_surface_grain = serializers.CharField(allow_null=True)
    sheen_level = serializers.CharField(allow_null=True)
    substrate_surface_treatment = serializers.CharField(allow_null=True)
    panel_category = serializers.CharField(allow_null=True)
    purpose_of_usage = serializers.CharField(allow_null=True)
    additional_detail = serializers.CharField(allow_null=True)


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
    comment = serializers.CharField(allow_null=True)
    duration = serializers.DurationField()