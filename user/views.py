from rest_framework import generics, permissions
from .models import User
from .serializers import UserSerializer


class UserListView(generics.ListAPIView):
    queryset = User.objects.select_related('department', 'role').all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    
class UserMeView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user