from django.urls import path
from .views import DocumentListView, DocumentDetailView, SignDocumentView

urlpatterns = [
    path('documents/', DocumentListView.as_view(), name='document-list'),
    path('documents/<int:pk>/', DocumentDetailView.as_view(), name='document-detail'),
    path('documents/sign/', SignDocumentView.as_view(), name='document-sign'),
]
