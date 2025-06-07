from rest_framework import viewsets

from process.models import Process
from .serializers import ProcessSerializer


class ProcessViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProcessSerializer

    def get_queryset(self):
        user = self.request.user
        qs = Process.objects.filter(is_active=True).prefetch_related('fields')
        
        if user.is_staff:
            return qs
        return qs.filter(allowed_users__user=user).distinct()