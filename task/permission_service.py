# Create services/permission_service.py

from django.db.models import Q
from typing import List, Set
from process.models import ProcessActionRole, RoleType, Action
from task.models import Task
from user.models import User

class PermissionService:
    
    @staticmethod
    def get_allowed_users_for_action(task: Task, action: Action) -> Set[User]:
        """
        Dynamically resolve which users can perform an action on a task
        """
        allowed_users = set()
        
        # Get all role definitions for this process-action combination
        role_definitions = ProcessActionRole.objects.filter(
            process=task.process,
            action=action
        )
        
        for role_def in role_definitions:
            users = PermissionService._resolve_users_for_role(task, role_def)
            allowed_users.update(users)
            
        return allowed_users
    
    @staticmethod
    def _resolve_users_for_role(task: Task, role_def: ProcessActionRole) -> List[User]:
        """
        Resolve users based on role type and task context
        """
        users = []
        
        if role_def.role_type == RoleType.REQUESTOR:
            users.append(task.created_by)
            
        elif role_def.role_type == RoleType.REQUESTOR_MANAGER:
            if task.created_by.manager:
                users.append(task.created_by.manager)
                
        elif role_def.role_type == RoleType.REQUESTOR_DEPARTMENT_HEAD:
            # Head of requestor's department
            dept_head = PermissionService._get_department_head(task.created_by.department)
            if dept_head:
                users.append(dept_head)
                
        elif role_def.role_type == RoleType.SPECIFIC_DEPARTMENT_HEAD:
            # Head of a specific department (not requestor's)
            if role_def.specific_department:
                dept_head = PermissionService._get_department_head(role_def.specific_department)
                if dept_head:
                    users.append(dept_head)
                
        elif role_def.role_type == RoleType.ASSIGNEE:
            # Get assigned user from task data (if you have assignee field)
            assignee = PermissionService._get_task_assignee(task)
            if assignee:
                users.append(assignee)
                
        elif role_def.role_type == RoleType.SPECIFIC_USER:
            if role_def.specific_user:
                users.append(role_def.specific_user)
                
        elif role_def.role_type == RoleType.SPECIFIC_ROLE:
            if role_def.specific_role:
                users.extend(
                    User.objects.filter(role=role_def.specific_role, is_active=True)
                )
                
        elif role_def.role_type == RoleType.SPECIFIC_DEPARTMENT:
            if role_def.specific_department:
                users.extend(
                    User.objects.filter(department=role_def.specific_department, is_active=True)
                )
        
        return users
    
    @staticmethod
    def _get_department_head(department):
        """Get department head - implement based on your business logic"""
        # Option 1: Role-based
        return User.objects.filter(
            department=department, 
            role__name__icontains='head'
        ).first()
        
        # Option 2: Custom field (if you add it)
        # return department.head_user
    
    @staticmethod
    def _get_task_assignee(task: Task):
        """Get assigned user from task data"""
        assignee_field = task.data.filter(
            field__field_type='assignee'
        ).first()
        
        if assignee_field and assignee_field.value:
            try:
                return User.objects.get(id=int(assignee_field.value))
            except (User.DoesNotExist, ValueError):
                pass
        return None
    
    @staticmethod
    def user_can_perform_action(user: User, task: Task, action: Action) -> bool:
        """
        Check if a user can perform a specific action on a task
        """
        allowed_users = PermissionService.get_allowed_users_for_action(task, action)
        return user in allowed_users