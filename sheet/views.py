from django.shortcuts import get_object_or_404
from rest_framework import viewsets, generics
from .models import FinishingSheet, StepTemplate, FormularTemplate, SheetBlueprint, SheetImage
from .serializers import FinishingSheetSerializer, StepTemplateSerializer, FormularTemplateSerializer, SheetBlueprintSerializer, SheetImageSerializer

class StepTemplateListView(generics.ListAPIView):
    queryset = StepTemplate.objects.all()
    serializer_class = StepTemplateSerializer
    pagination_class = None


class FormularTemplateListView(generics.ListAPIView):
    queryset = FormularTemplate.objects.all()
    serializer_class = FormularTemplateSerializer
    pagination_class = None


class FinishingSheetViewSet(viewsets.ModelViewSet):
    queryset = FinishingSheet.objects.all()
    serializer_class = FinishingSheetSerializer

    filterset_fields = ['task', 'created_by']
    search_fields = ['finishing_code', 'factory_code']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = FinishingSheet.objects.select_related(
            'task', 'created_by', 'updated_by'
        ).prefetch_related(
            'rows__step_template',
            'rows__formular_template',
            'rows__created_by',
            'rows__updated_by',
            'rows__products__created_by',
            'rows__products__updated_by',
        )

        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)

        return queryset


class SheetImageViewSet(viewsets.ModelViewSet):
    serializer_class = SheetImageSerializer
    http_method_names = ['get', 'post', 'delete']

    def get_queryset(self):
        sheet_id = self.request.query_params.get('sheet')
        if sheet_id:
            return SheetImage.objects.filter(sheet_id=sheet_id)
        # For retrieve/destroy by pk, return all (permission handled by ownership if needed)
        return SheetImage.objects.all()

    def perform_create(self, serializer):
        sheet = get_object_or_404(FinishingSheet, id=self.request.data.get('sheet'))
        serializer.save(sheet=sheet, created_by=self.request.user)


class SheetBlueprintViewSet(viewsets.ModelViewSet):
    queryset = SheetBlueprint.objects.all()
    serializer_class = SheetBlueprintSerializer
    
    filterset_fields = ['finishing_sheet', 'blueprint']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)
    
    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)