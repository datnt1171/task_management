from .serializers import ProcessDetailSerializer, ProcessListSerializer
from rest_framework.generics import ListAPIView, RetrieveAPIView
from .models import Process

class ListProcessAPIView(ListAPIView):
    serializer_class = ProcessListSerializer
    
    def get_queryset(self):
        user = self.request.user
        qs = Process.objects.filter(is_active=True)

        if user.is_staff:
            return qs
        return qs.filter(allowed_users__user=user)
    

class ProcessDetailAPIView(RetrieveAPIView):
    serializer_class = ProcessDetailSerializer
    
    def get_queryset(self):
        user = self.request.user
        qs = Process.objects.filter(is_active=True)

        if user.is_staff:
            return qs
        return qs.filter(allowed_users__user=user)
    