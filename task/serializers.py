import json
import os
from django.core.files.storage import default_storage
from django.db import transaction
from rest_framework import serializers
from django.utils.timezone import now
from .models import Task, TaskData, TaskActionLog
from process.models import ProcessField, Action
from workflow_engine.models import State, Transition
from .permission_service import PermissionService


class SentTaskSerializer(serializers.ModelSerializer):
    process = serializers.CharField(source='process.name')
    recipient = serializers.SerializerMethodField()
    state = serializers.CharField(source='state.name')
    state_type = serializers.CharField(source='state.state_type')

    class Meta:
        model = Task
        fields = ['id', 'title', 'process', 'state', 'state_type', 'created_at', 'recipient']

    def get_recipient(self, obj):
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

    def get_action(self, obj):
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
    field_id = serializers.IntegerField()
    value = serializers.CharField(allow_blank=True, allow_null=True, required=False)
    file = serializers.FileField(required=False)
    json_value = serializers.JSONField(required=False)

    def validate(self, data):
        file = data.get("file")
        json_val = data.get("json_value")

        if file:
            upload_dir = now().strftime('uploads/task_data_files/%Y/%m')
            filename = default_storage.save(os.path.join(upload_dir, file.name), file)
            data["value"] = default_storage.save(filename, file)

        elif json_val is not None:
            data["value"] = json.dumps(json_val)

        elif "value" not in data:
            raise serializers.ValidationError("Either 'value', 'file', or 'json_value' must be provided.")

        return data


class TaskCreateSerializer(serializers.ModelSerializer):
    fields = TaskDataInputSerializer(many=True, write_only=True)

    class Meta:
        model = Task
        fields = ['process', 'fields']

    def validate_process(self, process):
        if not process.is_active:
            raise serializers.ValidationError("This process is inactive.")
        return process

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
                state=start_state
            )

            for field_data in field_data_list:
                field_id = field_data.get('field_id')
                try:
                    field_obj = ProcessField.objects.get(id=field_id, process=process)
                except ProcessField.DoesNotExist:
                    raise serializers.ValidationError(f"Field ID {field_id} is invalid for this process.")

                TaskData.objects.create(
                    task=task,
                    field=field_obj,
                    value=field_data.get('value')
                )

        return task
    

class TaskActionSerializer(serializers.Serializer):
    action_id = serializers.IntegerField()
    comment = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    file = serializers.FileField(required=False, allow_null=True)

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
    
    
class TaskProcessSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()


class TaskStateSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    type = serializers.CharField(source='state_type')


class TaskUserSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()


class TaskDataSerializer(serializers.ModelSerializer):
    field = serializers.SerializerMethodField()

    class Meta:
        model = TaskData
        fields = ['field', 'value']

    def get_field(self, obj):
        return {
            'id': obj.field.id,
            'name': obj.field.name,
            'type': obj.field.field_type  # Include this for clarity
        }


class TaskActionLogSerializer(serializers.ModelSerializer):
    user = TaskUserSerializer()
    action = serializers.SerializerMethodField()
    file = serializers.FileField(required=False)

    class Meta:
        model = TaskActionLog
        fields = ['id', 'user', 'action', 'created_at', 'comment', 'file']

    def get_action(self, obj):
        return {
            'id': obj.action.id,
            'name': obj.action.name,
            'description': obj.action.description,
            'type': obj.action.action_type
        }


class TaskDetailSerializer(serializers.ModelSerializer):
    process = TaskProcessSerializer()
    state = TaskStateSerializer()
    created_by = TaskUserSerializer()
    data = TaskDataSerializer(many=True)
    action_logs = TaskActionLogSerializer(many=True)
    available_actions = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            'id', 'title', 'process', 'state', 'created_by', 'created_at',
            'data', 'action_logs', 'available_actions'
        ]

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
                    'type': action.action_type
                })

        return permitted
