from celery import shared_task

@shared_task
def print_all_permission(task_id, permissions, state):
    print("task_id:", task_id, "permission:", permissions, "state", state)