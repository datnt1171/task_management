from .models import User
from .serializers import UserDetailSerializer, UserListSerializer
from django.db.models import Q
from rest_framework.generics import ListAPIView, RetrieveAPIView

class UserProfileView(RetrieveAPIView):
    serializer_class = UserDetailSerializer

    def get_object(self):
        return self.request.user


class UserListView(ListAPIView):
    serializer_class = UserListSerializer

    def get_queryset(self):
        return User.objects.active().exclude(
            Q(role__name__iexact='admin') & Q(department__name__iexact='admin')
        )


class UserRetrieveView(RetrieveAPIView):
    queryset = User.objects.active().exclude(
        Q(role__name__iexact='admin') & Q(department__name__iexact='admin')
    )
    serializer_class = UserListSerializer

