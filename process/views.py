from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from process.models import Process
from .serializers import ProcessSerializer


class ProcessListAPIView(generics.ListAPIView):
    serializer_class = ProcessSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Process.objects.prefetch_related('fields').all()
        return Process.objects.filter(allowed_users__user=user).prefetch_related('fields').distinct()