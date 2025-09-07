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
    wft = models.PositiveIntegerField(blank=True, null=True)
    description = models.TextField(blank=True, help_text="Reason to create this formular")
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
    unit = models.CharField(max_length=20, default='g')
    
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
    created_by = models.ForeignKey('user.User', on_delete=models.CASCADE, related_name='created_sheets')
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey('user.User', on_delete=models.CASCADE, related_name='updated_sheets')

    # Metadata
    finishing_code = models.CharField() # Title
    name = models.CharField()
    sheen = models.CharField(max_length=50) 
    dft = models.CharField(max_length=50)
    type_of_paint = models.CharField(max_length=50)
    type_of_substrate = models.CharField(max_length=200)
    finishing_surface_grain = models.CharField(max_length=100)
    sampler = models.CharField(max_length=100)

    # Process details (production-specific)
    chemical_waste = models.CharField(max_length=20)
    conveyor_speed = models.CharField(max_length=100)

    # Test flags
    with_panel_test = models.BooleanField()
    testing = models.BooleanField()
    chemical_yellowing = models.BooleanField()
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.finishing_code


class SheetRow(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sheet = models.ForeignKey(
        FinishingSheet, 
        on_delete=models.CASCADE, 
        related_name='rows'
    )
    # FKs to template (for provenance only)
    step_template = models.ForeignKey(
        StepTemplate, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    formular_template = models.ForeignKey(
        FormularTemplate, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    
    # Step data
    step_num = models.IntegerField()
    spot = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True)

    stepname_en = models.CharField(max_length=255)
    stepname_vi = models.CharField(max_length=255)
    stepname_zh_hant = models.CharField(max_length=255)

    viscosity_en = models.TextField()
    viscosity_vi = models.TextField()
    viscosity_zh_hant = models.TextField()

    spec_en = models.TextField()
    spec_vi = models.TextField()
    spec_zh_hant = models.TextField()

    hold_time = models.CharField(max_length=50)
    chemical_code = models.CharField(max_length=100)
    consumption = models.CharField(max_length=100)
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('user.User', on_delete=models.CASCADE, related_name='created_sheet_rows')
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey('user.User', on_delete=models.CASCADE, related_name='updated_sheet_rows')
    
    class Meta:
        ordering = ['sheet', 'step_num']
        unique_together = ['sheet', 'step_num']
    
    def __str__(self):
        return f"Step {self.step_num}. {self.stepname_en}"


class RowProduct(models.Model):
    """Product used in each sheet row"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    row = models.ForeignKey(
        SheetRow, 
        on_delete=models.CASCADE, 
        related_name='products'
    )

    product_code = models.CharField(max_length=100)
    product_name = models.CharField(max_length=200)
    
    # Production-specific fields
    ratio = models.CharField(max_length=50)
    qty = models.CharField(max_length=50)
    unit = models.CharField(max_length=20)
    check_result = models.CharField(max_length=255, blank=True)
    correct_action = models.CharField(max_length=255, blank=True)
    te1_signature = models.CharField(max_length=100, blank=True)
    customer_signature = models.CharField(max_length=100, blank=True)
    order = models.PositiveIntegerField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('user.User', on_delete=models.CASCADE, related_name='created_row_products')
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey('user.User', on_delete=models.CASCADE, related_name='updated_row_products')
    
    class Meta:
        ordering = ['row', 'order']
    
    def __str__(self):
        return self.product_name


class ProductionAudit(models.Model):
    """Track changes to production records"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    row = models.ForeignKey(SheetRow, on_delete=models.CASCADE)
    action = models.CharField(max_length=50)  # CREATE, UPDATE, DELETE
    user = models.ForeignKey('user.User', on_delete=models.CASCADE)
    changes = models.JSONField(default=dict)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']