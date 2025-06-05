from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import User
from .serializers import UserProfileSerializer, UserListSerializer
from django.db.models import Q

class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)


class UserListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        users = User.objects.active().exclude(
            Q(role__name__iexact='admin') & Q(department__name__iexact='admin')
        )
        serializer = UserListSerializer(users, many=True)
        return Response(serializer.data)
