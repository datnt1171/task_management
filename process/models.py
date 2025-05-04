from django.db import models
from user.models import User

class Process(models.Model):
    name = models.TextField()


    def __str__(self):
        return self.name


class ProcessUser(models.Model): #Stakeholders template
    process = models.ForeignKey(Process, on_delete=models.CASCADE, related_name='allowed_users')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"{self.process} - {self.user}"


class ActionType(models.Model):
    name = models.CharField(max_length=255)
    
    def __str__(self):
        return self.name
    

class Action(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    action_type = models.ForeignKey(ActionType, on_delete=models.CASCADE)
    process = models.ForeignKey(Process, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"{self.name} ({self.action_type.name})"
    
    
class ProcessUserAction(models.Model): #Permission
    process = models.ForeignKey(Process, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.ForeignKey(Action, on_delete=models.CASCADE)
    
    
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
    MULTISELECT = 'multiselect', 'Multi-Select'
    CHECKBOX = 'checkbox', 'Checkbox'
    FILE = 'file', 'File'
    JSON = 'json', 'Table'


class ProcessField(models.Model):
    process = models.ForeignKey(Process, on_delete=models.CASCADE, related_name="fields")
    name = models.CharField(max_length=255)
    field_type = models.CharField(max_length=255, choices=FieldType.choices, default=FieldType.TEXT)
    required = models.BooleanField(default=False)


    class Meta:
        unique_together = ('process', 'name')

    def __str__(self):
        return f"{self.process.name} - {self.name} ({self.field_type})"