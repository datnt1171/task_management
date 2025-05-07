from rest_framework import serializers
from task.models import Task, TaskData, TaskUser, TaskActionLog
from workflow_engine.models import State, Transition, ActionTransition
from process.models import ProcessUserAction, Action

class TaskDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskData
        fields = ['field', 'value']


class TaskUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskUser
        fields = ['user']


class TaskCreateSerializer(serializers.ModelSerializer):
    data = TaskDataSerializer(many=True, write_only=True)

    class Meta:
        model = Task
        fields = ['process', 'title', 'data']

    def create(self, validated_data):
        data = validated_data.pop('data')
        user = self.context['request'].user
        process = validated_data['process']

        # Get the first state (with state_type='start')
        start_state = State.objects.filter(state_type__name__iexact='start').first()
        if not start_state:
            raise serializers.ValidationError("No 'start' state defined.")

        # Create the Task
        task = Task.objects.create(
            **validated_data,
            created_by=user,
            state=start_state
        )

        # Save TaskData
        for item in data:
            TaskData.objects.create(task=task, **item)

        # Auto add all relevant ProcessUserAction users as TaskUser
        process_user_actions = ProcessUserAction.objects.filter(process=process)
        unique_users = set(pua.user for pua in process_user_actions)
        for u in unique_users:
            TaskUser.objects.get_or_create(task=task, user=u)

        # Include the creator as a stakeholder
        TaskUser.objects.get_or_create(task=task, user=user)

        create_action = Action.objects.filter(
            action_type__name__iexact='initial',
            process=process
        ).first()

        # Create TaskActionLog
        TaskActionLog.objects.create(
            task=task,
            user=user,
            action=create_action
        )
        
        return task


class TaskSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ['id', 'title', 'process', 'state', 'created_at']


class TaskDetailSerializer(serializers.ModelSerializer):
    data = serializers.SerializerMethodField()
    stakeholders = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = ['id', 'title', 'process', 'state', 'created_at', 'data', 'stakeholders']

    def get_data(self, obj):
        return TaskDataSerializer(obj.taskdata_set.all(), many=True).data

    def get_stakeholders(self, obj):
        return TaskUserSerializer(obj.stakeholder.all(), many=True).data


class TaskStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ['state']

    def update(self, instance, validated_data):
        new_state = validated_data.get('state')
        user = self.context['request'].user

        # Validate transition
        transition = Transition.objects.filter(
            current_state=instance.state,
            next_state=new_state,
            process=instance.process
        ).first()

        if not transition:
            raise serializers.ValidationError("Invalid state transition.")

        # Find the action associated with this transition
        action_transition = ActionTransition.objects.filter(transition=transition).first()
        if not action_transition:
            raise serializers.ValidationError("No action defined for this transition.")

        # Update the task's state
        instance.state = new_state
        instance.save()

        # Log the action without the transition reference
        TaskActionLog.objects.create(
            task=instance,
            user=user,
            action=action_transition.action
        )

        return instance
