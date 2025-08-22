from django.db import models
import uuid


class StepTemplate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=128, unique=True)
    short_name = models.CharField(max_length=128, unique=True)
    spec = models.TextField(blank=True)
    hold_time = models.PositiveIntegerField()
    consumption = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True, help_text="Reason to create this step")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.short_name


class FormularTemplate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    viscosity = models.PositiveSmallIntegerField()
    wft = models.PositiveIntegerField()
    description = models.TextField(help_text="Reason to create this formular")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.code


class ProductTemplate(models.Model):
    """Product associated with Formular templates"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    formular_template = models.ForeignKey(
        FormularTemplate, 
        on_delete=models.CASCADE, 
        related_name='products'
    )
    code = models.CharField(max_length=128)
    name = models.CharField(max_length=128)
    ratio = models.DecimalField(max_digits=10, decimal_places=2)
    qty = models.CharField(max_length=50, blank=True)
    unit = models.CharField(max_length=20, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name


class FinishingSheet(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(
        'task.Task',
        on_delete=models.CASCADE,
        related_name='finishing_sheets',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('user.User', on_delete=models.CASCADE)
    updated_at = models.DateTimeField(auto_now=True)

    # Metadata
    finishing_code = models.CharField(max_length=255) # Title
    name = models.CharField(blank=True)
    sheen = models.CharField(max_length=50, blank=True) 
    dft = models.CharField(max_length=50, blank=True)
    type_of_paint = models.CharField(max_length=50, blank=True)
    type_of_substrate = models.CharField(max_length=200, blank=True)
    finishing_surface_grain = models.CharField(max_length=100, blank=True)
    sampler = models.CharField(max_length=100, blank=True)

    # Process details (production-specific)
    chemical_waste = models.CharField(max_length=20)
    conveyor_speed = models.CharField(max_length=100)

    # Test flags
    with_panel_test = models.BooleanField(default=False)
    testing = models.BooleanField(default=False)
    chemical_yellowing = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.finishing_code} - {self.created_at.date}"


# class SheetRow(models.Model):
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     sheet = models.ForeignKey(
#         FinishingSheet, 
#         on_delete=models.CASCADE, 
#         related_name='rows'
#     )
#     # FKs to template (for provenance only)
#     step_template = models.ForeignKey(
#         StepTemplate, 
#         on_delete=models.SET_NULL, 
#         null=True, 
#         blank=True
#     )
#     formular_template = models.ForeignKey(
#         FormularTemplate, 
#         on_delete=models.SET_NULL, 
#         null=True, 
#         blank=True
#     )
    
#     # Step data
#     step_num = models.IntegerField()
#     spot = models.IntegerField()

#     stepname_en = models.CharField(max_length=255)
#     stepname_vi = models.CharField(max_length=255)
#     stepname_zh_hant = models.CharField(max_length=255)

#     viscosity_en = models.TextField(blank=True)
#     viscosity_vn = models.TextField(blank=True)
#     viscosity_zh_hant = models.TextField(blank=True)

#     spec_en = models.TextField(blank=True)
#     spec_vn = models.TextField(blank=True)
#     spec_zh_hant = models.TextField(blank=True)

#     hold_time = models.CharField(max_length=50, blank=True)
#     chemical_code = models.CharField(max_length=100, blank=True)
#     consumption = models.CharField(max_length=100, blank=True)
    
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
    
#     class Meta:
#         db_table = 'production_records'
#         ordering = ['sheet', 'step_order']
#         unique_together = ['sheet', 'step_order']
    
#     def __str__(self):
#         return f"Step {self.step_order}: {self.stepname}"


# class RecordMaterial(models.Model):
#     """Materials used in each production record"""
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     record = models.ForeignKey(
#         SheetRow, 
#         on_delete=models.CASCADE, 
#         related_name='materials'
#     )
#     # Store product info locally (synced from data warehouse)
#     product_code = models.CharField(max_length=100, blank=True)  # material_code from React
#     product_name = models.CharField(max_length=200, blank=True)  # material_name from React
    
#     # Production-specific fields
#     ratio = models.CharField(max_length=50, blank=True)
#     qty = models.CharField(max_length=50, blank=True)
#     unit = models.CharField(max_length=20, blank=True)
#     check_result = models.TextField(blank=True)
#     correct_action = models.TextField(blank=True)
#     te1_signature = models.CharField(max_length=100, blank=True)
#     customer_signature = models.CharField(max_length=100, blank=True)
#     order = models.PositiveIntegerField(default=0)
    
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
    
#     class Meta:
#         db_table = 'record_materials'
#         ordering = ['record', 'order']
#         indexes = [
#             models.Index(fields=['product_code']),
#         ]
    
#     def __str__(self):
#         return f"{self.product_code} - {self.product_name}"

# # Optional: Audit trail model
# class ProductionAudit(models.Model):
#     """Track changes to production records"""
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     record = models.ForeignKey(SheetRow, on_delete=models.CASCADE)
#     action = models.CharField(max_length=50)  # CREATE, UPDATE, DELETE
#     user = models.CharField(max_length=100, blank=True)
#     changes = models.JSONField(default=dict)
#     timestamp = models.DateTimeField(auto_now_add=True)
    
#     class Meta:
#         db_table = 'production_audits'
#         ordering = ['-timestamp']