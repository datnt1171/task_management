from .models import User, UserFactoryOnsite
from .serializers import UserDetailSerializer, UserSerializer, ChangePasswordSerializer, CustomTokenObtainPairSerializer, UserFactoryOnsiteSerializer
from django.db.models import Q
from rest_framework.generics import ListAPIView, RetrieveAPIView, UpdateAPIView
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.decorators import action

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class UserProfileView(RetrieveAPIView):
    serializer_class = UserDetailSerializer

    def get_object(self):
        return self.request.user


class UserListView(ListAPIView):
    serializer_class = UserDetailSerializer
    filterset_fields = {
        'department__name': ['exact', 'in'],
        'role__name': ['exact', 'in'],
        'username': ['exact', 'in'],
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
    

class UserFactoryOnsiteViewSet(viewsets.ModelViewSet):
    queryset = UserFactoryOnsite.objects.all()
    serializer_class = UserFactoryOnsiteSerializer
    
    filterset_fields = ['factory', 'year', 'month', 'user']
    ordering_fields = ['factory', 'year', 'month', 'user']
    ordering = ['-year', '-month']
    pagination_class = None

    @action(detail=False, methods=['post'])
    def bulk_update(self, request):
        """Update multiple assignments at once"""
        assignments = request.data
        
        if not isinstance(assignments, list):
            return Response(
                {'error': 'Expected an array of assignments'}, 
                status=400
            )
        
        for assignment_data in assignments:
            user_id = assignment_data.get('user')
            year = assignment_data.get('year')
            month = assignment_data.get('month')
            factory = assignment_data.get('factory')
            
            if factory:
                # Create or update
                obj, created = UserFactoryOnsite.objects.update_or_create(
                    user_id=user_id,
                    year=year,
                    month=month,
                    defaults={'factory': factory}
                )
            else:
                # Delete if factory is empty
                UserFactoryOnsite.objects.filter(
                    user_id=user_id,
                    year=year,
                    month=month
                ).delete()
        
        return Response({'status': 'success'})