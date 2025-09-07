from .models import User
from .serializers import UserDetailSerializer, UserSerializer, ChangePasswordSerializer, CustomTokenObtainPairSerializer
from django.db.models import Q
from rest_framework.generics import ListAPIView, RetrieveAPIView, UpdateAPIView
from rest_framework import status
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from core.paginations import LargeResultsSetPagination

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class UserProfileView(RetrieveAPIView):
    serializer_class = UserDetailSerializer

    def get_object(self):
        return self.request.user


class UserListView(ListAPIView):
    serializer_class = UserDetailSerializer
    pagination_class = LargeResultsSetPagination
    filterset_fields = {
        'department__name': ['exact', 'in'],
        'role__name': ['exact', 'in'],
    }
    search_fields = ['username', 'first_name', 'last_name']

    def get_queryset(self):
        return User.objects.active().select_related('department', 'role', 'supervisor').exclude(
            Q(role__name__iexact='admin') & Q(department__name__iexact='admin')
        )


class UserRetrieveView(RetrieveAPIView):
    queryset = User.objects.active().exclude(
        Q(role__name__iexact='admin') & Q(department__name__iexact='admin')
    )
    serializer_class = UserSerializer


class ChangePasswordView(UpdateAPIView):
    serializer_class = ChangePasswordSerializer

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = self.get_object()
        user.set_password(serializer.validated_data['new_password'])
        user.is_password_changed = True
        user.save()
        
        return Response(
            {"message": "Password changed successfully"}, 
            status=status.HTTP_200_OK
        )