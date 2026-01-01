# tasks.py
from celery import shared_task
from django.contrib.auth import get_user_model
from fcm_django.models import FCMDevice
from firebase_admin.messaging import Message, Notification
from firebase_admin.exceptions import FirebaseError
import logging
from django.conf import settings

logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task
def print_all_permission(task_id, permissions, state):
    print("task_id:", task_id, "permission:", permissions, "state", state)

@shared_task
def send_task_notification(task_id, state_id, exclude_user_id):
    """  
    Args:
        task_id: UUID of the task
        state_id: UUID of the current state
        exclude_user_id: User ID to exclude (creator/performer)
    """
    try:
        from .models import Task, State
        from .permission_service import PermissionService
        
        # Get task and state
        task = Task.objects.get(id=task_id)
        state = State.objects.get(id=state_id)
        
        # Get users who can perform actions (excluding performer)
        eligible_users = PermissionService.get_users_for_state(task, state)
        user_ids = [u.id for u in eligible_users if u.id != exclude_user_id]
        
        if not user_ids:
            logger.info(f"Task {task_id}: No users to notify")
            return {'success': False, 'message': 'No users to notify'}
        
        # Get active devices
        devices = FCMDevice.objects.filter(user_id__in=user_ids, active=True)
        
        if not devices.exists():
            logger.info(f"Task {task_id}: No active devices for {len(user_ids)} users")
            return {'success': False, 'message': 'No active devices'}
        
        # Simple message
        message = Message(
            data={
                'title': "TE-1 Viet Lien",
                'body': f"{task.title} ({state.name}) cần thực hiện",
                'task_id': str(task_id),
                'state_id': str(state_id),
                'url': f"{settings.DOMAIN_URL}/task-management/tasks/{task_id}" if hasattr(settings, 'DOMAIN_URL') else None,
            }
        )
        
        # Send and get response
        response = devices.send_message(message)
        
        # Extract success/failure counts
        success_count = getattr(response, 'success_count', 0)
        failure_count = getattr(response, 'failure_count', 0)
        
        # Log detailed results
        logger.info(
            f"Task {task_id}: Notification sent to {len(user_ids)} users, "
            f"{devices.count()} devices. Success: {success_count}, Failed: {failure_count}"
        )
        
        return {
            'success': True,
            'users_count': len(user_ids),
            'devices_count': devices.count(),
            'success_count': success_count,
            'failure_count': failure_count
        }
        
    except Exception as e:
        logger.error(f"Task {task_id}: Notification error - {str(e)}")
        return {'success': False, 'error': str(e)}