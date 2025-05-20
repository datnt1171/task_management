from django.db import models
from django.core.exceptions import ValidationError
from user.models import User
from process.models import Process, Action, ProcessField
from workflow_engine.models import State
from django.utils.timezone import now

def get_process_prefix(process_name: str) -> str:
    mapping = {
        "purchase request": "PR",
        "common task": "COM",
        "maintenance request": "BT",
    }
    return mapping.get(process_name, "XX")

def generate_task_title(process: Process) -> str:
    prefix = get_process_prefix(process.name)  # e.g., "BT"
    current_time = now()
    year_month = current_time.strftime('%y%m')

    # Count tasks for this process created in the current month
    task_count = Task.objects.filter(
        process=process,
        created_at__year=current_time.year,
        created_at__month=current_time.month
    ).count() + 1

    return f"{prefix}{year_month}{task_count:03d}"


class Task(models.Model):
    
    process = models.ForeignKey(Process, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    state = models.ForeignKey(State, on_delete=models.CASCADE)
    
    
    class Meta:
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        if not self.pk:  # Only generate on creation
            self.title = generate_task_title(self.process)
        super().save(*args, **kwargs) 
    
    def __str__(self):
        return f"{self.title} ({self.process.name})"


class TaskData(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='data')
    field = models.ForeignKey(ProcessField, on_delete=models.CASCADE)
    value = models.TextField(blank=True, null=True)
    file = models.FileField(upload_to='uploads/task_data_files/%Y/%m/%d/', blank=True, null=True)
    json_data = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def clean(self):
    # Skip validation if the field is optional and all inputs are empty
        if not self.field.required and not self.value and not self.file and not self.json_data:
            return

        # Required logic based on field type
        if self.field.field_type == 'file':
            if not self.file:
                raise ValidationError("File is required for FILE field type.")
            if self.value or self.json_data:
                raise ValidationError("Only file should be set for FILE field type.")
        
        elif self.field.field_type == 'json':
            if not self.json_data:
                raise ValidationError("JSON data is required for JSON field type.")
            if self.value or self.file:
                raise ValidationError("Only json_data should be set for JSON field type.")
        
        else:
            if not self.value:
                raise ValidationError("Value is required for non-FILE and non-JSON field types.")
            if self.file or self.json_data:
                raise ValidationError("Only value should be set for non-FILE and non-JSON field types.")

    def __str__(self):
        return f"{self.task} - {self.field}"
    

class TaskActionLog(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.ForeignKey(Action, on_delete=models.CASCADE)
    comment = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.task} - {self.user} - {self.action}"