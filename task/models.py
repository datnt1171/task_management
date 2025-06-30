import uuid
from django.db import models
from user.models import User
from process.models import Process, Action, ProcessField
from workflow_engine.models import State
from django.utils.timezone import now
from django.core.validators import FileExtensionValidator

def generate_task_title(process: Process) -> str:
    prefix = process.prefix or "XX"
    current_time = now()
    year_month = current_time.strftime('%y%m')

    # Count tasks from ALL processes with same prefix in same month
    task_count = Task.objects.filter(
        process__prefix=prefix,
        created_at__year=current_time.year,
        created_at__month=current_time.month
    ).count() + 1

    return f"{prefix}{year_month}{task_count:03d}"


class Task(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255, unique=True, editable=False)
    process = models.ForeignKey(Process, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    state = models.ForeignKey(State, on_delete=models.CASCADE)
    
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} ({self.process.name})"


class TaskData(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='data')
    field = models.ForeignKey(ProcessField, on_delete=models.CASCADE)
    value = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['task','field'], name='unique_task_field')
        ]
    
    def __str__(self):
        return f"{self.task} - {self.field}"
    

class TaskFileData(models.Model):
    task_data = models.ForeignKey(TaskData, on_delete=models.CASCADE, related_name='files')
    uploaded_file = models.FileField(
        upload_to='uploads/task_data_files/',
        validators=[FileExtensionValidator(allowed_extensions=[
            'jpg', 'jpeg', 'png', 'pdf', 'doc', 'docx', 'xls', 'xlsx'
        ])]
    )
    original_filename = models.CharField(max_length=255, blank=True)
    file_size = models.IntegerField(blank=True, null=True)
    mime_type = models.CharField(max_length=100, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)


class TaskActionLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="action_logs")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.ForeignKey(Action, on_delete=models.CASCADE)
    comment = models.TextField(null=True, blank=True)

    file = models.FileField(
        upload_to='task_logs/',
        null=True,
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=[
            'jpg', 'jpeg', 'png', 'pdf', 'doc', 'docx', 'xls', 'xlsx'
        ])]
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.task} - {self.user} - {self.action}"