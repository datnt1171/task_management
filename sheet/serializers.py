from rest_framework import serializers
from django.db import transaction
from .models import StepTemplate, FormularTemplate, ProductTemplate, FinishingSheet, SheetRow, RowProduct, SheetBlueprint

class StepTemplateSerializer(serializers.ModelSerializer):
    """Always return all the translation regardless Accept-Language
        because finising sheet is a snapshot so it wont benefit from FK
    """
    name_en = serializers.CharField(read_only=True)
    name_vi = serializers.CharField(read_only=True)
    name_zh_hant = serializers.CharField(read_only=True)
    
    short_name_en = serializers.CharField(read_only=True)
    short_name_vi = serializers.CharField(read_only=True)
    short_name_zh_hant = serializers.CharField(read_only=True)
    
    spec_en = serializers.CharField(read_only=True)
    spec_vi = serializers.CharField(read_only=True)
    spec_zh_hant = serializers.CharField(read_only=True)


    class Meta:
        model = StepTemplate
        fields = (
            'id', 'name', 'short_name', 'spec', 'hold_time', 'consumption',
            'name_en', 'name_vi', 'name_zh_hant',
            'short_name_en', 'short_name_vi', 'short_name_zh_hant',
            'spec_en', 'spec_vi', 'spec_zh_hant'
        )


class ProductTemplateSerializer(serializers.ModelSerializer):

    class Meta:
        model = ProductTemplate
        fields = ('id', 'code', 'name', 'ratio', 'unit')


class FormularTemplateSerializer(serializers.ModelSerializer):
    products = ProductTemplateSerializer(many=True)

    class Meta:
        model = FormularTemplate
        fields = ('id', 'code', 'viscosity', 'wft', 'products')


class RowProductSerializer(serializers.ModelSerializer):

    class Meta:
        model = RowProduct
        fields = ('id', 'order', 'product_code', 'product_name', 
                  'ratio', 'qty', 'unit', 
                  'check_result', 'correct_action', 'te1_signature', 'customer_signature',
                  'created_by', 'created_at', 'updated_by', 'updated_at')
        read_only_fields = ('created_at', 'created_by', 'updated_at', 'updated_by',)


class SheetRowSerializer(serializers.ModelSerializer):
    products = RowProductSerializer(many=True)
    
    class Meta:
        model = SheetRow
        fields = ('id', 'step_template', 'formular_template', 'step_num', 'spot',
                  'stepname_en', 'stepname_vi', 'stepname_zh_hant',
                  'viscosity_en', 'viscosity_vi', 'viscosity_zh_hant',
                  'spec_en', 'spec_vi', 'spec_zh_hant',
                  'hold_time', 'chemical_code', 'consumption',
                  'created_at', 'created_by', 'updated_at', 'updated_by',
                  'products',)
        read_only_fields = ('created_at', 'created_by', 'updated_at', 'updated_by',)

    def create(self, validated_data):
        products_data = validated_data.pop('products', [])
        
        user = self.context['request'].user
        
        row = SheetRow.objects.create(
            created_by=user,
            updated_by=user,
            **validated_data
        )
        
        for product_data in products_data:
            RowProduct.objects.create(
                row=row,
                created_by=user,
                updated_by=user,
                **product_data
            )
        return row

    def update(self, instance, validated_data):
        products_data = validated_data.pop('products', [])
        
        user = self.context['request'].user
        
        # Update row fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.updated_by = user
        instance.save()
        
        # Handle products update (delete and recreate)
        instance.products.all().delete()
        for product_data in products_data:
            RowProduct.objects.create(
                row=instance,
                created_by=user,
                updated_by=user,
                **product_data
            )
            
        return instance


class FinishingSheetSerializer(serializers.ModelSerializer):
    rows = SheetRowSerializer(many=True)
    
    class Meta:
        model = FinishingSheet
        fields = ('id', 'task', 'finishing_code', 'name', 
                  'sheen', 'dft', 'type_of_paint', 'type_of_substrate',
                  'finishing_surface_grain', 'sampler',
                  'chemical_waste', 'conveyor_speed',
                  'with_panel_test', 'testing', 'chemical_yellowing',
                  'created_at', 'created_by', 'updated_at', 'updated_by',
                  'rows',)
        read_only_fields = ('created_at', 'created_by', 'updated_at', 'updated_by',)

    @transaction.atomic
    def create(self, validated_data):
        rows_data = validated_data.pop('rows', [])
        
        user = self.context['request'].user
        
        sheet = FinishingSheet.objects.create(
            created_by=user,
            updated_by=user,
            **validated_data
        )
        
        for row_data in rows_data:
            products_data = row_data.pop('products', [])
            row = SheetRow.objects.create(
                sheet=sheet,
                created_by=user,
                updated_by=user,
                **row_data
            )
            
            for product_data in products_data:
                RowProduct.objects.create(
                    row=row,
                    created_by=user,
                    updated_by=user,
                    **product_data
                )
        return sheet

    @transaction.atomic
    def update(self, instance, validated_data):
        rows_data = validated_data.pop('rows', [])
        
        user = self.context['request'].user
        
        # Update sheet fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.updated_by = user
        instance.save()
        
        # Handle rows update (delete and recreate)
        instance.rows.all().delete()
        for row_data in rows_data:
            products_data = row_data.pop('products', [])
            row = SheetRow.objects.create(
                sheet=instance,
                created_by=user,
                updated_by=user,
                **row_data
            )
            
            for product_data in products_data:
                RowProduct.objects.create(
                    row=row,
                    created_by=user,
                    updated_by=user,
                    **product_data
                )
                
        return instance


class SheetBlueprintSerializer(serializers.ModelSerializer):

    class Meta:
        model = SheetBlueprint
        fields = ('id', 'finishing_sheet', 'blueprint', 'description',
                  'created_at', 'created_by', 'updated_at', 'updated_by')
        read_only_fields = ('id', 'created_at', 'updated_at', 'created_by', 'updated_by',)