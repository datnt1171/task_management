from rest_framework import serializers
from .models import Task, TaskData, TaskActionLog
from process.models import Process, ProcessField, Action
from workflow_engine.models import State, Transition

class TaskProcessSerializer(serializers.ModelSerializer):
    class Meta:
        model = Process
        fields = ['name']


class SentTaskSerializer(serializers.ModelSerializer):
    process = TaskProcessSerializer(read_only=True)
    recipient = serializers.SerializerMethodField()
    state = serializers.CharField(source='state.name')
    state_type = serializers.CharField(source='state.state_type.name')

    class Meta:
        model = Task
        fields = ['id', 'title', 'process', 'state','state_type', 'created_at', 'recipient']

    def get_recipient(self, obj):
        # Get user who can act on this task
        request = self.context['request']
        action = (
            obj.state
              .transitions_from
              .first()
              .actiontransition_set
              .filter(action__process=obj.process)
              .first()
        )
        if action:
            user_action = action.action.processuseraction_set.first()
            return user_action.user.username if user_action else None
        return None


class ReceivedTaskSerializer(serializers.ModelSerializer):
    process = TaskProcessSerializer(read_only=True)
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
    value = serializers.CharField()


class TaskCreateSerializer(serializers.ModelSerializer):
    fields = TaskDataInputSerializer(many=True, write_only=True)
    
    class Meta:
        model = Task
        fields = ['process', 'title', 'fields']
    
    def create(self, validated_data):
        user = self.context['request'].user
        process = validated_data['process']
        title = validated_data['title']
        field_data = validated_data.pop('fields')

        # Get the start state for this process
        start_state = State.objects.filter(
            state_type__name__exact='start',
            transitions_from__process=process
        ).distinct().first()

        if not start_state:
            raise serializers.ValidationError("Start state not defined for this process.")

        task = Task.objects.create(
            process=process,
            title=title,
            created_by=user,
            state=start_state
        )

        for field in field_data:
            field_obj = ProcessField.objects.get(id=field['field_id'], process=process)
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
    user = serializers.SerializerMethodField()
    action = serializers.SerializerMethodField()

    class Meta:
        model = TaskActionLog
        fields = ['id', 'user', 'action', 'timestamp']

    def get_user(self, obj):
        return {
            'id': obj.user.id,
            'username': obj.user.username
        }

    def get_action(self, obj):
        return {
            'id': obj.action.id,
            'name': obj.action.name,
            'description': obj.action.description
        }


class TaskDetailSerializer(serializers.ModelSerializer):
    process = serializers.SerializerMethodField()
    state = serializers.SerializerMethodField()
    created_by = serializers.SerializerMethodField()
    task_data = TaskDataSerializer(source='taskdata_set', many=True)
    action_logs = TaskActionLogSerializer(source='taskactionlog_set', many=True)
    available_actions = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            'id', 'title', 'process', 'state', 'created_by', 'created_at',
            'task_data', 'action_logs', 'available_actions'
        ]

    def get_process(self, obj):
        return {
            'id': obj.process.id,
            'name': obj.process.name
        }

    def get_state(self, obj):
        return {
            'id': obj.state.id,
            'name': obj.state.name
        }

    def get_created_by(self, obj):
        return {
            'id': obj.created_by.id,
            'username': obj.created_by.username
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
                'type': action.action_type.name  # get the name of related ActionType
            } for action in actions
        ]