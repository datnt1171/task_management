from django.db import models
from user.models import User
from process.models import Process, Action, ProcessField
from workflow_engine.models import State, Transition


class Task(models.Model):
    process = models.ForeignKey(Process, on_delete=models.CASCADE)
    title = models.TextField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    state = models.ForeignKey(State, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"{self.title} ({self.process.name})"


class TaskData(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    field = models.ForeignKey(ProcessField, on_delete=models.CASCADE)
    value = models.TextField()

    def __str__(self):
        return f"{self.task} - {self.field.label}: {self.value}"
    

class TaskUser(models.Model): # stakeholder
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='stakeholder')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    class Meta:
        constraints = [
        models.UniqueConstraint(fields=['task', 'user'], name='unique_request_user')
    ]
        
    def __str__(self):
        return f"{self.user} - {self.task}"
    

class TaskActionLog(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.ForeignKey(Action, on_delete=models.CASCADE)
    transition = models.ForeignKey(Transition, on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.task} - {self.user} - {self.action} at {self.timestamp}"