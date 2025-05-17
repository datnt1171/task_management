from django.db import models
from user.models import User
from process.models import Process, Action, ProcessField
from workflow_engine.models import State, Transition


class Task(models.Model):
    process = models.ForeignKey(Process, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    state = models.ForeignKey(State, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"{self.title} ({self.process.name})"


class TaskData(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='data')
    field = models.ForeignKey(ProcessField, on_delete=models.CASCADE)
    value = models.TextField(blank=True, null=True)
    file = models.FileField(upload_to='task_files/%Y/%m/%d/', blank=True, null=True)
    json_data = models.JSONField(blank=True, null=True)

    def clean(self):
        from django.core.exceptions import ValidationError
        # Ensure only one of value, file, or json_data is set based on field_type
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
        if self.field.field_type == 'file':
            return f"{self.task} - {self.field}: {self.file.name if self.file else 'No file'}"
        elif self.field.field_type == 'json':
            return f"{self.task} - {self.field}: JSON data"
        return f"{self.task} - {self.field}: {self.value}"
    

class TaskActionLog(models.Model):
    task = models.ForeignKey(Task, on_delete=models.DO_NOTHING)
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    action = models.ForeignKey(Action, on_delete=models.DO_NOTHING)
    comment = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.task} - {self.user} - {self.action} at {self.timestamp}"