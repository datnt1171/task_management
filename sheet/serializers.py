from rest_framework import serializers
from django.db import transaction
from .models import StepTemplate, FormularTemplate, ProductTemplate, FinishingSheet, SheetRow, RowProduct, SheetBlueprint, SheetImage
from user.serializers import UserSerializer

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

    sanding_en = serializers.CharField(read_only=True)
    sanding_vi = serializers.CharField(read_only=True)
    sanding_zh_hant = serializers.CharField(read_only=True)

    class Meta:
        model = StepTemplate
        fields = (
            'id', 'name', 'short_name', 'spec', 'sanding',
            'hold_time', 'oven_temperature', 'consumption',
            'name_en', 'name_vi', 'name_zh_hant',
            'short_name_en', 'short_name_vi', 'short_name_zh_hant',
            'spec_en', 'spec_vi', 'spec_zh_hant',
            'sanding_en', 'sanding_vi', 'sanding_zh_hant',
        )


class ProductTemplateSerializer(serializers.ModelSerializer):
    description_en = serializers.CharField(read_only=True)
    description_vi = serializers.CharField(read_only=True)
    description_zh_hant = serializers.CharField(read_only=True)

    class Meta:
        model = ProductTemplate
        fields = (
            'id', 'code', 'name',
            'description_en', 'description_vi', 'description_zh_hant',
            'ratio', 'unit',
        )


class FormularTemplateSerializer(serializers.ModelSerializer):
    products = ProductTemplateSerializer(many=True)

    class Meta:
        model = FormularTemplate
        fields = ('id', 'code', 'viscosity', 'wft', 'products')


class RowProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = RowProduct
        fields = (
            'id', 'order',
            'product_code', 'product_name',
            'product_description_en', 'product_description_vi', 'product_description_zh_hant',
            'ratio', 'qty', 'unit',
            'created_by', 'created_at', 'updated_by', 'updated_at',
        )
        read_only_fields = ('created_at', 'created_by', 'updated_at', 'updated_by',)


class SheetRowSerializer(serializers.ModelSerializer):
    products = RowProductSerializer(many=True)

    class Meta:
        model = SheetRow
        fields = (
            'id', 'step_template', 'formular_template',
            'order',
            'spot',
            'name_en', 'name_vi', 'name_zh_hant',
            'name_short_en', 'name_short_vi', 'name_short_zh_hant',
            'sanding_en', 'sanding_vi', 'sanding_zh_hant',
            'viscosity_en', 'viscosity_vi', 'viscosity_zh_hant',
            'spec_en', 'spec_vi', 'spec_zh_hant',
            'hold_time', 'chemical_code', 'consumption',
            'wft', 'oven_temperature',
            'created_at', 'created_by', 'updated_at', 'updated_by',
            'products',
        )
        read_only_fields = ('created_at', 'created_by', 'updated_at', 'updated_by',)

    def create(self, validated_data):
        products_data = validated_data.pop('products', [])
        user = self.context['request'].user
        row = SheetRow.objects.create(created_by=user, updated_by=user, **validated_data)
        for product_data in products_data:
            RowProduct.objects.create(row=row, created_by=user, updated_by=user, **product_data)
        return row

    def update(self, instance, validated_data):
        products_data = validated_data.pop('products', [])
        user = self.context['request'].user
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.updated_by = user
        instance.save()
        instance.products.all().delete()
        for product_data in products_data:
            RowProduct.objects.create(row=instance, created_by=user, updated_by=user, **product_data)
        return instance


class SheetImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = SheetImage
        fields = ('id', 'image', 'caption', 'created_at', 'created_by')
        read_only_fields = ('created_at', 'created_by')

    def create(self, validated_data):
        return SheetImage.objects.create(**validated_data)


class FinishingSheetSerializer(serializers.ModelSerializer):
    rows = SheetRowSerializer(many=True)
    images = SheetImageSerializer(many=True, read_only=True)

    created_by = UserSerializer(read_only=True)
    updated_by = UserSerializer(read_only=True)

    class Meta:
        model = FinishingSheet
        fields = (
            'id', 'task',
            'factory_code', 'finishing_code', 'retailer_id', 'customer_color_name',  # was just finishing_code/name
            'sample_type', 'type_of_substrate', 'collection', 'sampler',
            'type_of_paint', 'finishing_surface_grain', 'sheen_level',               # was sheen
            'substrate_surface_treatment', 'panel_category', 'purpose_of_usage',
            'furniture_type', 'dft', 'chemical_waste', 'conveyor_speed', 'color',
            'images',
            'with_panel_test', 'testing', 'chemical_yellowing',
            'created_at', 'created_by', 'updated_at', 'updated_by',
            'rows',
        )
        read_only_fields = ('created_at', 'created_by', 'updated_at', 'updated_by',)

    @transaction.atomic
    def create(self, validated_data):
        rows_data = validated_data.pop('rows', [])
        user = self.context['request'].user
        sheet = FinishingSheet.objects.create(created_by=user, updated_by=user, **validated_data)
        for row_data in rows_data:
            products_data = row_data.pop('products', [])
            row = SheetRow.objects.create(sheet=sheet, created_by=user, updated_by=user, **row_data)
            for product_data in products_data:
                RowProduct.objects.create(row=row, created_by=user, updated_by=user, **product_data)
        return sheet

    @transaction.atomic
    def update(self, instance, validated_data):
        rows_data = validated_data.pop('rows', [])
        user = self.context['request'].user
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.updated_by = user
        instance.save()
        instance.rows.all().delete()
        for row_data in rows_data:
            products_data = row_data.pop('products', [])
            row = SheetRow.objects.create(sheet=instance, created_by=user, updated_by=user, **row_data)
            for product_data in products_data:
                RowProduct.objects.create(row=row, created_by=user, updated_by=user, **product_data)
        return instance


class SheetBlueprintSerializer(serializers.ModelSerializer):
    finishing_sheet_detail = FinishingSheetSerializer(source='finishing_sheet', read_only=True)
    created_by = UserSerializer(read_only=True)
    updated_by = UserSerializer(read_only=True)

    class Meta:
        model = SheetBlueprint
        fields = ('id', 'finishing_sheet', 'finishing_sheet_detail', 'blueprint', 'description',
                  'created_at', 'created_by', 'updated_at', 'updated_by')
        read_only_fields = ('id', 'created_at', 'updated_at', 'created_by', 'updated_by')