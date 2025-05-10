from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets

from process.models import Process
from .serializers import ProcessSerializer


class ProcessViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProcessSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Process.objects.prefetch_related('fields').all()
        return Process.objects.filter(allowed_users__user=user).prefetch_related('fields').distinct()