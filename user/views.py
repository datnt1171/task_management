from .models import User
from .serializers import UserDetailSerializer, UserListSerializer, ChangePasswordSerializer, CustomTokenObtainPairSerializer
from django.db.models import Q
from rest_framework.generics import ListAPIView, RetrieveAPIView, UpdateAPIView
from rest_framework import status
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from .permissions import HasJWTPermission

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class UserProfileView(RetrieveAPIView):
    serializer_class = UserDetailSerializer

    def get_object(self):
        return self.request.user


class UserListView(ListAPIView):
    serializer_class = UserListSerializer
    permission_classes = [HasJWTPermission]
    # required_permission = 'read.user.list'
    def get_queryset(self):
        return User.objects.active().exclude(
            Q(role__name__iexact='admin') & Q(department__name__iexact='admin')
        )


class UserRetrieveView(RetrieveAPIView):
    queryset = User.objects.active().exclude(
        Q(role__name__iexact='admin') & Q(department__name__iexact='admin')
    )
    serializer_class = UserListSerializer


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