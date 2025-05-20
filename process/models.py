from django.db import models
from django.core.exceptions import ValidationError
from user.models import User

class Process(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    version = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    
    class Meta:
        constraints = [
        models.UniqueConstraint(fields=['name', 'version'], name='unique_process_version')
    ]

    def __str__(self):
        return f"{self.name}(v{self.version})"


class ProcessUser(models.Model): #Allowed_users
    process = models.ForeignKey(Process, null=True, on_delete=models.SET_NULL, related_name='allowed_users')
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        constraints = [
        models.UniqueConstraint(fields=['process', 'user'], name='unique_process_user')
    ]
    
    def __str__(self):
        return f"{self.process} - {self.user}"


class ActionType(models.TextChoices):
    INITIAL = 'initial', 'Initial'
    APPROVE = 'approve', 'Approve'
    ADJUST = 'adjust', 'Adjust'
    CONFIRM = 'confirm', 'Confirm'
    COMPLETE = 'complete', 'Complete'
    CLOSE = 'close', 'Close'
    REJECT = 'reject', 'Reject'
    CANCEL = 'cancel', 'Cancel'
    
    

class Action(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    action_type = models.CharField(max_length=255, choices=ActionType.choices)
    process = models.ForeignKey(Process, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)    
    
    def __str__(self):
        return f"{self.name} ({self.get_action_type_display()})"
    
    
class ProcessUserAction(models.Model): #Permission
    process = models.ForeignKey(Process, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.ForeignKey(Action, on_delete=models.CASCADE, related_name='user_permissions')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)    
    
    class Meta:
        constraints = [
        models.UniqueConstraint(fields=['process', 'user', 'action'], name='unique_process_user_action')
    ]
        
    def __str__(self):
        return f"{self.process} - {self.user} - {self.action}"
    

class FieldType(models.TextChoices):
    TEXT = 'text', 'Text'
    NUMBER = 'number', 'Number'
    DATE = 'date', 'Date'
    SELECT = 'select', 'Select'
    FILE = 'file', 'File'
    JSON = 'json', 'Table'
    ASSIGNEE = 'assignee', 'Assignee'


class ProcessField(models.Model):
    process = models.ForeignKey(Process, on_delete=models.CASCADE, related_name="fields")
    name = models.CharField(max_length=255)
    field_type = models.CharField(max_length=255, choices=FieldType.choices, default=FieldType.TEXT)
    order = models.PositiveSmallIntegerField()
    required = models.BooleanField(default=False)
    options = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    
    class Meta:
        constraints = [
        models.UniqueConstraint(fields=['process', 'name'], name='unique_process_field')
    ]
        ordering = ['order']
    
    def clean(self):
        if self.field_type != FieldType.SELECT and self.options:
            raise ValidationError("Options are only valid for SELECT field type.")

    def __str__(self):
        return f"{self.process.name} - {self.name} ({self.field_type})"