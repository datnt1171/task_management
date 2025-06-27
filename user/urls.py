from django.urls import path
from user import views

urlpatterns = [
    path('me/', views.UserProfileView.as_view(), name='user-me'),
    path('', views.UserListView.as_view(), name='users'),
    path('<uuid:pk>/', views.UserRetrieveView.as_view(), name='user-retrieve'),
    path('me/change-password/', views.ChangePasswordView.as_view(), name='change-password'),
]