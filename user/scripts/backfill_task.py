from task.models import Task
from task.permission_service import PermissionService

def run():
    task_ids = []
    for task_id in task_ids:
        try:
            task = Task.objects.get(id=task_id)
            PermissionService.create_task_permissions(task)
            print(f"✓ Created permissions for task {task_id}")
        except Task.DoesNotExist:
            print(f"✗ Task {task_id} not found")
        except Exception as e:
            print(f"✗ Error with task {task_id}: {e}")