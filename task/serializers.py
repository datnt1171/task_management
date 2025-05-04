from rest_framework import serializers
from task.models import Task, TaskData, TaskUser, TaskActionLog
from workflow_engine.models import State


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
    stakeholders = TaskUserSerializer(many=True, write_only=True)

    class Meta:
        model = Task
        fields = ['process', 'title', 'data', 'stakeholders']

    def create(self, validated_data):
        data = validated_data.pop('data')
        stakeholders = validated_data.pop('stakeholders')
        user = self.context['request'].user

        # Get first state of the process
        process = validated_data['process']
        first_state = State.objects.filter(
            transition__process=process,
            is_first_state=True
        ).first()

        if not first_state:
            raise serializers.ValidationError("No first state defined for this process.")

        task = Task.objects.create(
            **validated_data,
            created_by=user,
            state=first_state
        )

        # Save TaskData
        for item in data:
            TaskData.objects.create(task=task, **item)

        # Save Stakeholders
        for stakeholder in stakeholders:
            TaskUser.objects.create(task=task, **stakeholder)

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