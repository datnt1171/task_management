from django.db import models
from django.core.exceptions import ValidationError
from user.models import User

class Process(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    is_deleted = models.BooleanField(default=False)


    def __str__(self):
        return self.name


class ProcessUser(models.Model): #Allowed_users
    process = models.ForeignKey(Process, null=True, on_delete=models.SET_NULL, related_name='allowed_users')
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    
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
    action_type = models.CharField(max_length=255, choices=ActionType.choices, default=ActionType.INITIAL)
    process = models.ForeignKey(Process, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"{self.name} ({self.get_action_type_display()})"
    
    
class ProcessUserAction(models.Model): #Permission
    process = models.ForeignKey(Process, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.ForeignKey(Action, on_delete=models.CASCADE, related_name='user_permissions')
    
    
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
    CHECKBOX = 'checkbox', 'Checkbox'
    FILE = 'file', 'File'
    JSON = 'json', 'Table'
    ASSIGNEE = 'assignee', 'Assignee'


class ProcessField(models.Model):
    process = models.ForeignKey(Process, on_delete=models.CASCADE, related_name="fields")
    name = models.CharField(max_length=255)
    field_type = models.CharField(max_length=255, choices=FieldType.choices, default=FieldType.TEXT)
    order = models.PositiveSmallIntegerField(default=0)
    required = models.BooleanField(default=False)
    options = models.JSONField(blank=True, null=True)

    class Meta:
        unique_together = ('process', 'name')
        ordering = ['order']
    
    def clean(self):
        if self.field_type not in [FieldType.SELECT, FieldType.CHECKBOX] and self.field_type is not None:
            raise ValidationError("Options are only valid for SELECT field type.")

    def __str__(self):
        return f"{self.process.name} - {self.name} ({self.field_type})"