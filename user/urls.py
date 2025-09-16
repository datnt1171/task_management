from django.urls import path, include
from user import views
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'', views.UserFactoryOnsiteViewSet, basename='user-factory-onsite')

urlpatterns = [
    path('me/', views.UserProfileView.as_view(), name='user-me'),
    path('', views.UserListView.as_view(), name='users'),
    path('<uuid:pk>/', views.UserRetrieveView.as_view(), name='user-retrieve'),
    path('me/change-password/', views.ChangePasswordView.as_view(), name='change-password'),
    path('onsite/', include(router.urls)),
]