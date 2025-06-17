import os
from django.db import transaction
from django.conf import settings
from rest_framework import serializers
from .models import Task, TaskData, TaskActionLog, generate_task_title, TaskFileData
from process.models import ProcessField, Action
from process.serializers import ProcessFieldSerializer, ProcessListSerializer, ActionSerializer
from workflow_engine.models import State, Transition
from workflow_engine.serializers import StateSerializer
from .permission_service import PermissionService
from user.serializers import UserListSerializer
from core.constants import ALLOWED_EXTENSIONS, MAX_FILE_SIZE
from drf_spectacular.utils import extend_schema_field

def validate_file_extension(file):
    """Validate file extension"""
    if not file:
        return
    
    file_extension = os.path.splitext(file.name)[1].lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        allowed_str = ', '.join(ALLOWED_EXTENSIONS)
        raise serializers.ValidationError(
            f"File extension '{file_extension}' is not allowed. "
            f"Allowed extensions: {allowed_str}"
        )

def validate_file_size(file):
    """Validate file size"""
    if not file:
        return
    
    if file.size > MAX_FILE_SIZE:
        size_mb = MAX_FILE_SIZE / (1024 * 1024)
        raise serializers.ValidationError(
            f"File size exceeds maximum allowed size of {size_mb}MB. "
            f"Current file size: {file.size / (1024 * 1024):.2f}MB"
        )

def validate_file_content(file):
    """Basic file content validation (optional - for additional security)"""
    if not file:
        return
    
    # Reset file pointer to beginning
    file.seek(0)
    
    # Read first few bytes to check file signature
    file_header = file.read(4)
    file.seek(0)  # Reset pointer
    
    # Basic file signature validation (optional)
    # You can expand this based on your security requirements
    if file.name.lower().endswith(('.jpg', '.jpeg')):
        if not file_header.startswith(b'\xff\xd8\xff'):
            raise serializers.ValidationError("Invalid JPEG file format")
    elif file.name.lower().endswith('.png'):
        if not file_header.startswith(b'\x89PNG'):
            raise serializers.ValidationError("Invalid PNG file format")
    elif file.name.lower().endswith('.pdf'):
        if not file_header.startswith(b'%PDF'):
            raise serializers.ValidationError("Invalid PDF file format")
        
        
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
        Try to identify a user who is allowed to act on the task from the start state.
        """
        possible_actions = Action.objects.filter(
            actiontransition__transition__current_state=obj.state,
            process=obj.process
        ).distinct()

        for action in possible_actions:
            allowed_users = PermissionService.get_allowed_users_for_action(obj, action)
            for user in allowed_users:
                return user.username
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
        Return the name of the first action the current user is allowed to perform on this task.
        """
        user = self.context['request'].user
        possible_actions = Action.objects.filter(
            actiontransition__transition__current_state=obj.state,
            process=obj.process
        ).distinct()

        for action in possible_actions:
            if PermissionService.user_can_perform_action(user, obj, action):
                return action.name
        return None
     
        
class TaskDataInputSerializer(serializers.Serializer):
    field_id = serializers.UUIDField()
    value = serializers.CharField(allow_blank=True, allow_null=True, required=False)
    file = serializers.FileField(required=False)

    def validate_file(self, file):
        """Comprehensive file validation"""
        if file:
            # Validate file extension
            validate_file_extension(file)
            
            # Validate file size
            validate_file_size(file)
            
            # Validate file content (optional - remove if too strict)
            # validate_file_content(file)
            
        return file

    def validate(self, data):
        """Ensure either value or file is provided, but not both for file fields"""
        field_id = data.get('field_id')
        value = data.get('value')
        file = data.get('file')
        
        # If both value and file are provided for the same field, that might be an error
        # This depends on your business logic - adjust as needed
        if value and file:
            # You might want to allow this, or raise an error
            # For now, we'll allow it but log a warning
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
            raise serializers.ValidationError("No start state is defined for this process.")

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
                    raise serializers.ValidationError(f"Field ID {field_id} is invalid for this process.")

                # Validate field type vs provided data
                uploaded_file = field_data.get('file')
                field_value = field_data.get('value')
                
                # If field type is file but no file provided, and it's required
                if field_obj.field_type == 'file' and not uploaded_file and field_obj.required:
                    raise serializers.ValidationError(f"File is required for field '{field_obj.name}'")
                
                # If field type is not file but file is provided
                if field_obj.field_type != 'file' and uploaded_file:
                    raise serializers.ValidationError(f"Field '{field_obj.name}' does not accept files")

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
                        original_filename=uploaded_file.name,
                        file_size=uploaded_file.size,
                        mime_type=uploaded_file.content_type or ''
                    )

        return task
    

class TaskActionSerializer(serializers.Serializer):
    action_id = serializers.UUIDField()
    comment = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    file = serializers.FileField(required=False, allow_null=True)
    
    def validate_file(self, file):
        """Comprehensive file validation"""
        if file:
            # Validate file extension
            validate_file_extension(file)
            
            # Validate file size
            validate_file_size(file)
            
        return file
    
    def validate(self, attrs):
        user = self.context['request'].user
        task = self.context['task']
        action_id = attrs['action_id']
        
        try:
            action = Action.objects.get(id=action_id, process=task.process)
        except Action.DoesNotExist:
            raise serializers.ValidationError("Invalid action for this process.")
        
        # Check permission via PermissionService
        if not PermissionService.user_can_perform_action(user, task, action):
            raise serializers.ValidationError("You do not have permission to perform this action.")
        
        try:
            transition = Transition.objects.get(
                process=task.process,
                current_state=task.state,
                actiontransition__action=action
            )
        except Transition.DoesNotExist:
            raise serializers.ValidationError("No valid transition from current state for this action.")
        
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
        fields = ['original_filename', 'uploaded_file']
    
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


class TaskDataSerializer(serializers.ModelSerializer):
    field = serializers.SerializerMethodField()
    files = TaskFileDataSerializer(many=True)

    class Meta:
        model = TaskData
        fields = ['field', 'value', 'files']

    @extend_schema_field(ProcessFieldSerializer)
    def get_field(self, obj):
        return ProcessFieldSerializer(obj.field).data



class TaskActionLogSerializer(serializers.ModelSerializer):
    user = UserListSerializer()
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
    process = ProcessListSerializer()
    state = StateSerializer()
    created_by = UserListSerializer()
    data = TaskDataSerializer(many=True)
    action_logs = TaskActionLogSerializer(many=True)
    available_actions = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            'id', 'title', 'process', 'state', 'created_by', 'created_at',
            'data', 'action_logs', 'available_actions'
        ]

    @extend_schema_field(ActionSerializer)
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
    state_type = serializers.CharField()
    customer_name = serializers.CharField()
    finishing_code = serializers.CharField()
    customer_color_name = serializers.CharField()
    collection = serializers.CharField()
    quantity = serializers.CharField()
    deadline = serializers.CharField()