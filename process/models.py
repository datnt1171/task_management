import uuid
from django.db import models
from django.core.exceptions import ValidationError
from user.models import User, Role, Department


class ProcessManager(models.Manager):
    def active(self):
        return self.filter(is_active=True)


class Process(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    version = models.CharField(max_length=255)
    prefix = models.CharField(max_length=10)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = ProcessManager()
    
    class Meta:
        constraints = [
        models.UniqueConstraint(fields=['name', 'version'], name='unique_process_version')
    ]

    def __str__(self):
        return f"{self.prefix}({self.version})"


class ProcessUser(models.Model): #Allowed_users
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    process = models.ForeignKey(Process, on_delete=models.CASCADE, related_name='allowed_users')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    
    class Meta:
        constraints = [
        models.UniqueConstraint(fields=['process', 'user'], name='unique_process_user')
    ]
    
    def __str__(self):
        return f"{self.process} - {self.user}"


class ActionType(models.TextChoices):
    APPROVE = 'approve', 'Approve'
    ADJUST = 'adjust', 'Adjust'
    CONFIRM = 'confirm', 'Confirm'
    COMPLETE = 'complete', 'Complete'
    CLOSE = 'close', 'Close'
    REJECT = 'reject', 'Reject'
    CANCEL = 'cancel', 'Cancel'
    
    
class Action(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField()
    action_type = models.CharField(max_length=255, choices=ActionType.choices)
    process = models.ForeignKey(Process, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)    
    
    def __str__(self):
        return f"{self.process.prefix}{self.process.version} - {self.name}"
    
    
class RoleType(models.TextChoices):
    REQUESTOR = 'requestor', 'Task Requestor'
    REQUESTOR_MANAGER = 'requestor_manager', 'Requestor Manager'
    REQUESTOR_DEPARTMENT_HEAD = 'requestor_department_head', 'Requestor Department Head'
    SPECIFIC_DEPARTMENT_HEAD = 'specific_department_head', 'Specific Department Head'
    ASSIGNEE = 'assignee', 'Task Assignee'
    SPECIFIC_USER = 'specific_user', 'Specific User'
    SPECIFIC_ROLE = 'specific_role', 'Specific Role'
    SPECIFIC_DEPARTMENT = 'specific_department', 'Specific Department'
    SPECIFIC_ROLE_AND_DEPARTMENT = 'specific_role_and_department', 'Specific Role and Department'


class ProcessActionRole(models.Model):
    """Defines WHO can perform actions based on roles/relationships"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    process = models.ForeignKey(Process, on_delete=models.CASCADE)
    action = models.ForeignKey(Action, on_delete=models.CASCADE)
    role_type = models.CharField(max_length=50, choices=RoleType.choices)
    
    # Optional specific constraints
    specific_user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    specific_role = models.ForeignKey(Role, on_delete=models.CASCADE, null=True, blank=True)
    specific_department = models.ForeignKey(Department, on_delete=models.CASCADE, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['process', 'action', 'role_type', 'specific_user', 'specific_role', 'specific_department'], 
                name='unique_process_action_role'
            )
        ]
    
    def clean(self):
        # Validation logic
        if self.role_type == RoleType.SPECIFIC_USER and not self.specific_user:
            raise ValidationError("Specific user required for SPECIFIC_USER role type")
        if self.role_type == RoleType.SPECIFIC_ROLE and not self.specific_role:
            raise ValidationError("Specific role required for SPECIFIC_ROLE role type")
        if self.role_type == RoleType.SPECIFIC_DEPARTMENT and not self.specific_department:
            raise ValidationError("Specific department required for SPECIFIC_DEPARTMENT role type")
        if self.role_type == RoleType.SPECIFIC_ROLE_AND_DEPARTMENT:
            if not (self.specific_role and self.specific_department):
                raise ValidationError("Both role and department are required for SPECIFIC_ROLE_AND_DEPARTMENT role type.")
            
    def __str__(self):
        return f"{self.process} - {self.action} - {self.get_role_type_display()}"


class FieldType(models.TextChoices):
    TEXT = 'text', 'Text'
    NUMBER = 'number', 'Number'
    DATE = 'date', 'Date'
    SELECT = 'select', 'Select'
    FILE = 'file', 'File'
    JSON = 'json', 'Table'
    ASSIGNEE = 'assignee', 'Assignee'
    FACTORY = 'factory', 'Factory'
    RETAILER = 'retailer', 'Retailer'


class ProcessField(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    process = models.ForeignKey(Process, on_delete=models.CASCADE, related_name="fields")
    name = models.CharField(max_length=255)
    description = models.CharField(max_length=255, blank=True)
    field_type = models.CharField(max_length=255, choices=FieldType.choices, default=FieldType.TEXT)
    order = models.PositiveSmallIntegerField()
    required = models.BooleanField(default=False)
    options = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    
    class Meta:
        unique_together = [('process', 'name')]
        ordering = ['order']
    
    def clean(self):
        if self.field_type != FieldType.SELECT and self.options:
            raise ValidationError("Options are only valid for SELECT field type.")

    def __str__(self):
        return f"{self.process} - {self.name} ({self.field_type})"