import json
from django.core.files.storage import default_storage
from rest_framework import serializers
from .models import Task, TaskData, TaskActionLog
from process.models import ProcessField, Action
from workflow_engine.models import State, Transition


class SentTaskSerializer(serializers.ModelSerializer):
    process = serializers.CharField(source='process.name')
    recipient = serializers.SerializerMethodField()
    state = serializers.CharField(source='state.name')
    state_type = serializers.CharField(source='state.state_type')

    class Meta:
        model = Task
        fields = ['id', 'title', 'process', 'state','state_type', 'created_at', 'recipient']

    def get_recipient(self, obj):
        request = self.context['request']

        transition = obj.state.transitions_from.first()
        if not transition:
            return None

        action_transition = transition.actiontransition_set.filter(action__process=obj.process).first()
        if not action_transition:
            return None

        user_action = action_transition.action.processuseraction_set.first()
        return user_action.user.username if user_action else None


class ReceivedTaskSerializer(serializers.ModelSerializer):
    process = serializers.CharField(source='process.name')
    created_by = serializers.SerializerMethodField()
    action = serializers.SerializerMethodField()
    state = serializers.CharField(source='state.name')
    state_type = serializers.CharField(source='state.state_type.name')

    class Meta:
        model = Task
        fields = ['id', 'title', 'process', 'state', 'state_type', 'created_at', 'created_by', 'action']

    def get_created_by(self, obj):
        return obj.created_by.username

    def get_action(self, obj):
        user = self.context['request'].user
        return (
            obj.state
              .transitions_from
              .filter(
                  actiontransition__action__processuseraction__user=user
              )
              .values_list('actiontransition__action__name', flat=True)
              .first()
        )
     
        
class TaskDataInputSerializer(serializers.Serializer):
    field_id = serializers.IntegerField()
    value = serializers.CharField(allow_blank=True, allow_null=True)
    file = serializers.FileField(required=False)
    json_value = serializers.JSONField(required=False)

    def validate(self, data):
        if 'file' in data:
            # Save file and replace value with file path
            uploaded_file = data['file']
            path = default_storage.save(f"uploads/task_data_files/{uploaded_file.name}", uploaded_file)
            data['value'] = path
        elif 'json_value' in data:
            data['value'] = json.dumps(data['json_value'])  # Store JSON as string
        return data


class TaskCreateSerializer(serializers.ModelSerializer):
    fields = TaskDataInputSerializer(many=True, write_only=True)

    class Meta:
        model = Task
        fields = ['process', 'fields']

    def create(self, validated_data):
        user = self.context['request'].user
        process = validated_data['process']
        field_data = validated_data.pop('fields')

        # Get the start state for this process
        start_state = State.objects.filter(
            state_type='start',
            transitions_from__process=process
        ).distinct().first()

        if not start_state:
            raise serializers.ValidationError("Start state not defined for this process.")

        task = Task.objects.create(
            process=process,
            created_by=user,
            state=start_state
        )

        for field in field_data:
            field_id = field['field_id']
            try:
                field_obj = ProcessField.objects.get(id=field_id, process=process)
            except ProcessField.DoesNotExist:
                raise serializers.ValidationError(f"Field ID {field_id} not found for this process.")

            TaskData.objects.create(
                task=task,
                field=field_obj,
                value=field['value']
            )

        return task
    

class TaskActionSerializer(serializers.Serializer):
    action_id = serializers.IntegerField()

    def validate(self, attrs):
        user = self.context['request'].user
        task = self.context['task']
        action_id = attrs['action_id']

        # Check if action exists
        try:
            action = Action.objects.get(id=action_id, process=task.process)
        except Action.DoesNotExist:
            raise serializers.ValidationError("Invalid action for this process.")

        # Check user permission
        if not task.process.processuseraction_set.filter(user=user, action=action).exists():
            raise serializers.ValidationError("User not permitted to perform this action.")

        # Validate that the action is allowed from the current state
        try:
            transition = Transition.objects.get(
                process=task.process,
                current_state=task.state,
                actiontransition__action=action
            )
        except Transition.DoesNotExist:
            raise serializers.ValidationError("Invalid transition for this action from current state.")

        attrs['action'] = action
        attrs['transition'] = transition
        return attrs

    def save(self, **kwargs):
        task = self.context['task']
        user = self.context['request'].user
        action = self.validated_data['action']
        transition = self.validated_data['transition']

        # Update task state
        task.state = transition.next_state
        task.save()

        # Log the action
        TaskActionLog.objects.create(task=task, user=user, action=action)
        return task
    
    
class TaskProcessSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()

class TaskStateSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    state_type = serializers.CharField(source='state_type.name', default=None)

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
            'name': obj.field.name
        }

class TaskActionLogSerializer(serializers.ModelSerializer):
    user = TaskUserSerializer()
    action = serializers.SerializerMethodField()
    task_title = serializers.SerializerMethodField()

    class Meta:
        model = TaskActionLog
        fields = ['id', 'user', 'action', 'task_title', 'created_at']

    def get_action(self, obj):
        return {
            'id': obj.action.id,
            'name': obj.action.name,
            'description': obj.action.description,
            'type': obj.action.action_type.name if obj.action.action_type else None
        }

    def get_task_title(self, obj):
        return obj.task.title

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

    def get_state(self, obj):
        return {
            'id': obj.state.id,
            'name': obj.state.name,
            'type': obj.state.state_type.name if obj.state.state_type else None
        }

    def get_available_actions(self, obj):
        user = self.context['request'].user
        transitions = Transition.objects.filter(
            process=obj.process,
            current_state=obj.state
        )
        actions = Action.objects.filter(
            actiontransition__transition__in=transitions,
            processuseraction__user=user,
            processuseraction__process=obj.process
        ).select_related('action_type').distinct()

        return [
            {
                'id': action.id,
                'name': action.name,
                'description': action.description,
                'type': action.action_type.name if action.action_type else None
            } for action in actions
        ]