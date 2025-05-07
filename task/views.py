from rest_framework import generics
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .serializers import (
    TaskSimpleSerializer,
    TaskDetailSerializer,
    TaskCreateSerializer,
    TaskStatusUpdateSerializer,
)

from task.models import Task
from process.models import ProcessUserAction
# GET /api/tasks/sent/
class SentTaskListAPIView(generics.ListAPIView):
    serializer_class = TaskSimpleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Task.objects.filter(created_by=self.request.user)


class ReceivedTasksAPIView(generics.ListAPIView):
    serializer_class = TaskSimpleSerializer  # or TaskDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        return Task.objects.filter(
            state__transitions_from__actiontransition__action__in=(
                ProcessUserAction.objects.filter(user=user).values('action')
            ),
            process__in=(
                ProcessUserAction.objects.filter(user=user).values('process')
            )
        ).distinct().select_related('process', 'state', 'created_by')


#  GET /api/tasks/{id}/
class TaskDetailAPIView(generics.RetrieveAPIView):
    queryset = Task.objects.all()
    serializer_class = TaskDetailSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'


#  POST /api/tasks/
class TaskCreateAPIView(generics.CreateAPIView):
    queryset = Task.objects.all()
    serializer_class = TaskCreateSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_context(self):
        return {'request': self.request}


#  PUT /api/tasks/{id}/status/
class TaskStatusUpdateAPIView(generics.UpdateAPIView):
    queryset = Task.objects.all()
    serializer_class = TaskStatusUpdateSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'

    def get_serializer_context(self):
        return {'request': self.request}