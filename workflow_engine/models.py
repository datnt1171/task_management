from django.db import models
from django.core.exceptions import ValidationError
from process.models import Process, Action


class StateType(models.TextChoices):
    PENDING_APPROVE = 'pending_approve', 'Pending Approve'
    ANALYZE = 'analyze', 'Analyze'
    WORKING = 'working', 'Working'
    PENDING_REVIEW = 'pending_review', 'Pending Review'
    START = 'start', 'Start'
    DENIED = 'denied', 'Denied'
    CANCELED = 'canceled', 'Canceled'
    CLOSED = 'closed', 'Closed'


class State(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    state_type = models.CharField(max_length=255, choices=StateType.choices, default=StateType.START)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)    
    
    def __str__(self):
        return self.name
    

class Transition(models.Model):
    process = models.ForeignKey(Process, on_delete=models.CASCADE)
    current_state = models.ForeignKey(State, on_delete=models.CASCADE, related_name='transitions_from')
    next_state = models.ForeignKey(State, on_delete=models.CASCADE, related_name='transitions_to')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def clean(self):
        if self.current_state == self.next_state:
            raise ValidationError("Current state and next state cannot be the same.")
    
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['process', 'current_state', 'next_state'], name='unique_transition')
        ]
    
    def __str__(self):
        return f"{self.process} - {self.current_state} - {self.next_state}"


class ActionTransition(models.Model):
    action = models.ForeignKey(Action, on_delete=models.CASCADE)
    transition = models.ForeignKey(Transition, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)    
    class Meta:
        constraints = [
        models.UniqueConstraint(fields=['action', 'transition'], name='unique_action_transition')
    ]
        
    def __str__(self):
        return f"{self.transition.process} - {self.transition.current_state} - {self.action} - {self.transition.next_state}"