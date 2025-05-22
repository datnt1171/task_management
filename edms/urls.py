from django.urls import path
from . import views

urlpatterns = [
    path('categories/', views.CategoryListView.as_view(), name='edms-category-list'),
    path('categories/<int:category_id>/documents/', views.DocumentListByCategoryView.as_view(), name='edms-documents-by-category'),
    path('documents/<int:document_id>/versions/', views.DocumentVersionListView.as_view(), name='edms-document-versions'),
    path('documents/<int:document_id>/request-signature/', views.SignatureRequestCreateView.as_view(), name='edms-request-signature'),
    path('documents/<int:document_id>/sign/', views.SignDocumentView.as_view(), name='edms-sign-document'),
]
