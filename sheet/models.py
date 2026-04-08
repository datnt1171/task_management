from django.db import models
import uuid


class StepTemplate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=128, unique=True)
    short_name = models.CharField(max_length=25, unique=True)
    spec = models.TextField(blank=True)
    sanding = models.CharField(max_length=128, blank=True)
    hold_time = models.CharField(max_length=128, blank=True)
    oven_temperature = models.CharField(max_length=50, blank=True)
    consumption = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True, help_text="Reason to create this step")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.short_name


class FormularTemplate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    viscosity = models.CharField(max_length=50, blank=True)
    wft = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
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
    description = models.CharField(max_length=255)
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

    # From color panel request form
    factory_code = models.CharField(max_length=200)                             # Name of customer
    finishing_code = models.CharField(max_length=100)                           # Finishing code
    retailer_id = models.CharField(max_length=200, blank=True)                  # Retailer
    customer_color_name = models.CharField(max_length=100, blank=True)          # Customer's color name

    sample_type = models.CharField(max_length=100)                              # Sample Type
    type_of_substrate = models.CharField(max_length=200)                        # Type of substrate
    collection = models.CharField(max_length=200, blank=True)                               # Collection
    sampler = models.CharField(max_length=100)                                  # Sampler
    type_of_paint = models.CharField(max_length=100)                            # Type of paint
    finishing_surface_grain = models.CharField(max_length=100)                  # Finishing surface grain
    sheen_level = models.CharField(max_length=50)                               # Sheen level
    substrate_surface_treatment = models.CharField(max_length=200)              # Substrate surface treatment
    panel_category = models.CharField(max_length=200)                           # Panel category
    purpose_of_usage = models.CharField(max_length=200)                         # Purpose of usage
    
    # Manual input
    furniture_type = models.CharField(max_length=100, blank=True)               # Furniture Type (Chair, table,...)
    dft = models.CharField(max_length=50, blank=True)                           # Dry film thickness
    chemical_waste = models.CharField(max_length=20, blank=True)
    conveyor_speed = models.CharField(max_length=100, blank=True)
    color = models.CharField(max_length=100, blank=True)                        # Actual color of the sample (Black, Brown, White,...)
    
    # Test flags
    with_panel_test = models.BooleanField(default=False)
    testing = models.BooleanField(default=False)
    chemical_yellowing = models.BooleanField(default=False)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('user.User', on_delete=models.CASCADE, related_name='created_sheets')
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey('user.User', on_delete=models.CASCADE, related_name='updated_sheets')
    
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
        null=True, blank=True
    )
    formular_template = models.ForeignKey(
        FormularTemplate,
        on_delete=models.SET_NULL,
        null=True, blank=True
    )
    
    # Step data
    order = models.IntegerField()
    spot = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True)

    name_en = models.CharField(max_length=255)
    name_vi = models.CharField(max_length=255)
    name_zh_hant = models.CharField(max_length=255)

    name_short_en = models.CharField(max_length=255)
    name_short_vi = models.CharField(max_length=255)
    name_short_zh_hant = models.CharField(max_length=255)

    sanding_en = models.CharField(max_length=255, blank=True)
    sanding_vi = models.CharField(max_length=255, blank=True)
    sanding_zh_hant = models.CharField(max_length=255, blank=True)

    viscosity_en = models.TextField(blank=True)
    viscosity_vi = models.TextField(blank=True)
    viscosity_zh_hant = models.TextField(blank=True)

    spec_en = models.TextField(blank=True)
    spec_vi = models.TextField(blank=True)
    spec_zh_hant = models.TextField(blank=True)

    hold_time = models.CharField(max_length=50, blank=True)
    consumption = models.CharField(max_length=100, blank=True)
    wft = models.CharField(max_length=50, blank=True)
    oven_temperature = models.CharField(max_length=50, blank=True)

    chemical_code = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('user.User', on_delete=models.CASCADE, related_name='created_sheet_rows')
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey('user.User', on_delete=models.CASCADE, related_name='updated_sheet_rows')

    class Meta:
        ordering = ['sheet', 'order']
        unique_together = ['sheet', 'order']

    def __str__(self):
        return f"Step {self.order}. {self.name_en}"


class RowProduct(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    row = models.ForeignKey(
        SheetRow,
        on_delete=models.CASCADE,
        related_name='products'
    )

    product_code = models.CharField(max_length=100)
    product_name = models.CharField(max_length=200)
    product_description_en = models.CharField(max_length=255)
    product_description_vi = models.CharField(max_length=255)
    product_description_zh_hant = models.CharField(max_length=255)
    
    # Production-specific fields
    ratio = models.CharField(max_length=50, blank=True)
    qty = models.CharField(max_length=50, blank=True)
    unit = models.CharField(max_length=20, blank=True)

    order = models.PositiveIntegerField()

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('user.User', on_delete=models.CASCADE, related_name='created_row_products')
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey('user.User', on_delete=models.CASCADE, related_name='updated_row_products')

    class Meta:
        ordering = ['row', 'order']

    def __str__(self):
        return self.product_name


class SheetBlueprint(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    finishing_sheet = models.ForeignKey(FinishingSheet, on_delete=models.CASCADE, related_name='blueprints')
    blueprint = models.CharField(max_length=128)
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('user.User', on_delete=models.CASCADE, related_name='created_blueprints')
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey('user.User', on_delete=models.CASCADE, related_name='updated_blueprints')

    class Meta:
        ordering = ['-updated_at']


class SheetImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sheet = models.ForeignKey(FinishingSheet, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='finishing_sheets/')
    caption = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('user.User', on_delete=models.CASCADE, related_name='created_sheet_images')


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