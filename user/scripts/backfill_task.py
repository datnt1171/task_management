from django.db import transaction
from task.models import Task, TaskPermission
from process.models import Process
from task.permission_service import PermissionService

def run(process_id=None, batch_size=100):
    """
    Backfill task permissions for existing tasks.
    Deletes existing permissions and recreates them.
    
    Args:
        process_id: Optional process ID to filter tasks. If None, processes all tasks.
        batch_size: Number of tasks to process in each batch
    """
    # Build queryset
    queryset = Task.objects.select_related('process', 'created_by')
    
    if process_id:
        try:
            process = Process.objects.get(id=process_id)
            queryset = queryset.filter(process=process)
            print(f"Processing tasks for process: {process.name if hasattr(process, 'name') else process_id}")
        except Process.DoesNotExist:
            print(f"✗ Process {process_id} not found")
            return
    else:
        print("Processing all tasks")
    
    total_tasks = queryset.count()
    print(f"Found {total_tasks} tasks to process\n")
    
    success_count = 0
    error_count = 0
    
    # Process in batches
    for i in range(0, total_tasks, batch_size):
        batch = queryset[i:i + batch_size]
        
        for task in batch:
            try:
                with transaction.atomic():
                    # Delete existing permissions
                    deleted_count = TaskPermission.objects.filter(task=task).delete()[0]
                    
                    # Recreate permissions
                    PermissionService.create_task_permissions(task)
                    created_count = TaskPermission.objects.filter(task=task).count()
                    
                    print(f"✓ Task {task.id}: Deleted {deleted_count}, Created {created_count} permissions")
                    success_count += 1
                    
            except Exception as e:
                print(f"✗ Task {task.id}: {str(e)}")
                error_count += 1
        
        # Progress update after each batch
        processed = min(i + batch_size, total_tasks)
        print(f"\nProgress: {processed}/{total_tasks} tasks processed")
        print(f"Success: {success_count}, Errors: {error_count}\n")
    
    # Final summary
    print("=" * 50)
    print("BACKFILL COMPLETE")
    print(f"Total tasks: {total_tasks}")
    print(f"✓ Successfully processed: {success_count}")
    print(f"✗ Errors: {error_count}")
    print("=" * 50)