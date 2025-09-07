from .serializers import ProcessDetailSerializer, ProcessSerializer
from rest_framework.generics import ListAPIView, RetrieveAPIView
from .models import Process

class ProcessListAPIView(ListAPIView):
    serializer_class = ProcessSerializer
    search_fields = ['name']

    def get_queryset(self):
        user = self.request.user
        qs = Process.objects.active()

        if user.is_staff:
            return qs
        return qs.filter(allowed_users__user=user)
    

class ProcessDetailAPIView(RetrieveAPIView):
    serializer_class = ProcessDetailSerializer
    
    def get_queryset(self):
        user = self.request.user
        qs = Process.objects.active()

        if user.is_staff:
            return qs
        return qs.filter(allowed_users__user=user)
    