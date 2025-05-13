from django.urls import path
from user.views import UserListView, UserMeView

urlpatterns = [
    path('', UserListView.as_view(), name='user-list'),
    path('me/', UserMeView.as_view(), name='user-me'),
]