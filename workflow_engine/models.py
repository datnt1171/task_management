from django.db import models
from process.models import Process, Action


class StateType(models.Model):
    name = models.CharField(max_length=255)
    
    def __str__(self):
        return self.name
    

class State(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    state_type = models.ForeignKey(StateType, on_delete=models.CASCADE)
    
    def __str__(self):
        return self.name
    

class Transition(models.Model):
    process = models.ForeignKey(Process, on_delete=models.CASCADE)
    current_state = models.ForeignKey(State, on_delete=models.CASCADE, related_name='transitions_from')
    next_state = models.ForeignKey(State, on_delete=models.CASCADE, related_name='transitions_to')
    
    def __str__(self):
        return f"{self.process} - {self.current_state} - {self.next_state}"


class ActionTransition(models.Model):
    action = models.ForeignKey(Action, on_delete=models.CASCADE)
    transition = models.ForeignKey(Transition, on_delete=models.CASCADE)
    
    class Meta:
        constraints = [
        models.UniqueConstraint(fields=['action', 'transition'], name='unique_action_transition')
    ]
        
    def __str__(self):
        return f"{self.transition.process} - {self.transition.current_state} - {self.action} - {self.transition.next_state}"



    
    
