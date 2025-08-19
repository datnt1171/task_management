from django.db import models
import uuid


class StepTemplate(models.Model):
    """Template for production steps"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    stepname = models.CharField(max_length=200)
    viscosity_en = models.TextField(blank=True)
    viscosity_vn = models.TextField(blank=True)
    spec_en = models.TextField(blank=True)
    spec_vn = models.TextField(blank=True)
    hold_time = models.CharField(max_length=50, blank=True)
    consumption = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.stepname


class ChemicalTemplate(models.Model):
    """Template for chemical mixing codes"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chemical_code = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.chemical_code


class MaterialTemplate(models.Model):
    """Materials associated with chemical templates"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chemical_template = models.ForeignKey(
        ChemicalTemplate, 
        on_delete=models.CASCADE, 
        related_name='materials'
    )
    product_code = models.CharField(max_length=100)
    product_name = models.CharField(max_length=200)
    
    ratio = models.CharField(max_length=50, blank=True)
    qty = models.CharField(max_length=50, blank=True)
    unit = models.CharField(max_length=20, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'material_templates'
        ordering = ['chemical_template', 'order']
        indexes = [
            models.Index(fields=['product_code']),
            models.Index(fields=['product_status']),
        ]
    
    def __str__(self):
        return f"{self.product_code} - {self.product_name}"


class ProductSheet(models.Model):
    """Main production sheet"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product_code = models.CharField(max_length=100, default='RH-OAK-51-1')
    product_name = models.CharField(max_length=200, default='BARON')
    date = models.DateField(auto_now_add=True)
    
    # Foreign key to task management (same Django project)
    sample_request = models.ForeignKey(
        'task_management.SampleRequest',  # Assuming app name is task_management
        on_delete=models.CASCADE,
        related_name='production_sheets',
        help_text='The original sample request that initiated this production sheet'
    )
    
    # These fields will be populated automatically from sample_request
    # but can be overridden if needed
    full_name = models.TextField(blank=True)
    sheen = models.CharField(max_length=50, blank=True) 
    dft = models.CharField(max_length=50, blank=True)
    chemical_type = models.CharField(max_length=50, blank=True)
    substrate = models.CharField(max_length=200, blank=True)
    grain_filling = models.CharField(max_length=100, blank=True)
    developer = models.CharField(max_length=100, blank=True)
    
    # Process details (production-specific)
    chemical_waste = models.CharField(max_length=20, default='0%')
    conveyor_speed = models.CharField(max_length=100, default='1.5 METER PER 1 MINUTE')
    
    # Test flags
    with_panel_test = models.BooleanField(default=False)
    no_panel_test = models.BooleanField(default=False)
    testing = models.BooleanField(default=False)
    chemical_yellowing = models.BooleanField(default=False)
    
    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=[
            ('DRAFT', 'Draft'),
            ('IN_PROGRESS', 'In Progress'),
            ('COMPLETED', 'Completed'),
            ('APPROVED', 'Approved'),
        ],
        default='DRAFT'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'product_sheets'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['product_code']),
            models.Index(fields=['sample_request']),
            models.Index(fields=['status']),
        ]
    
    def save(self, *args, **kwargs):
        """Auto-populate metadata from sample_request if not set"""
        if self.sample_request and not self.full_name:
            # Auto-populate from sample request
            self.full_name = self.sample_request.full_name or ''
            self.sheen = self.sample_request.sheen or ''
            self.dft = self.sample_request.dft or ''
            self.chemical_type = self.sample_request.chemical_type or ''
            self.substrate = self.sample_request.substrate or ''
            self.grain_filling = self.sample_request.grain_filling or ''
            self.developer = self.sample_request.developer or ''
            
        super().save(*args, **kwargs)
    
    @property
    def customer(self):
        """Get customer from related sample request"""
        return self.sample_request.customer if self.sample_request else None
        
    @property
    def request_date(self):
        """Get original request date"""
        return self.sample_request.created_at if self.sample_request else None
    
    def __str__(self):
        return f"{self.product_code} - {self.date} (Request: {self.sample_request.id if self.sample_request else 'N/A'})"


class ProductionRecord(models.Model):
    """Individual production step records"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sheet = models.ForeignKey(
        ProductSheet, 
        on_delete=models.CASCADE, 
        related_name='records'
    )
    booth = models.PositiveIntegerField()
    step_order = models.PositiveIntegerField(default=1)
    
    # Step template reference
    step_template = models.ForeignKey(
        StepTemplate, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    
    # Step data (can be overridden from template)
    stepname = models.CharField(max_length=200, blank=True)
    viscosity_en = models.TextField(blank=True)
    viscosity_vn = models.TextField(blank=True)
    spec_en = models.TextField(blank=True)
    spec_vn = models.TextField(blank=True)
    hold_time = models.CharField(max_length=50, blank=True)
    
    # Chemical template reference
    chemical_template = models.ForeignKey(
        ChemicalTemplate, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    
    # Chemical data (can be overridden from template)
    chemical_code = models.CharField(max_length=100, blank=True)
    consumption = models.CharField(max_length=100, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'production_records'
        ordering = ['sheet', 'step_order']
        unique_together = ['sheet', 'step_order']
    
    def __str__(self):
        return f"Step {self.step_order}: {self.stepname}"
    
    def save(self, *args, **kwargs):
        # Auto-populate from templates if not set
        if self.step_template and not self.stepname:
            self.stepname = self.step_template.stepname
            self.viscosity_en = self.step_template.viscosity_en
            self.viscosity_vn = self.step_template.viscosity_vn
            self.spec_en = self.step_template.spec_en
            self.spec_vn = self.step_template.spec_vn
            self.hold_time = self.step_template.hold_time
            
        if self.chemical_template and not self.chemical_code:
            self.chemical_code = self.chemical_template.chemical_code
            self.consumption = self.chemical_template.consumption
            
        super().save(*args, **kwargs)


class RecordMaterial(models.Model):
    """Materials used in each production record"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    record = models.ForeignKey(
        ProductionRecord, 
        on_delete=models.CASCADE, 
        related_name='materials'
    )
    # Store product info locally (synced from data warehouse)
    product_code = models.CharField(max_length=100, blank=True)  # material_code from React
    product_name = models.CharField(max_length=200, blank=True)  # material_name from React
    
    # Production-specific fields
    ratio = models.CharField(max_length=50, blank=True)
    qty = models.CharField(max_length=50, blank=True)
    unit = models.CharField(max_length=20, blank=True)
    check_result = models.TextField(blank=True)
    correct_action = models.TextField(blank=True)
    te1_signature = models.CharField(max_length=100, blank=True)
    customer_signature = models.CharField(max_length=100, blank=True)
    order = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'record_materials'
        ordering = ['record', 'order']
        indexes = [
            models.Index(fields=['product_code']),
        ]
    
    def __str__(self):
        return f"{self.product_code} - {self.product_name}"

# Optional: Audit trail model
class ProductionAudit(models.Model):
    """Track changes to production records"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    record = models.ForeignKey(ProductionRecord, on_delete=models.CASCADE)
    action = models.CharField(max_length=50)  # CREATE, UPDATE, DELETE
    user = models.CharField(max_length=100, blank=True)
    changes = models.JSONField(default=dict)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'production_audits'
        ordering = ['-timestamp']