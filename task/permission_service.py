from typing import List, Set
from process.models import ProcessActionRole, RoleType, Action
from task.models import Task, TaskPermission
from user.models import User

class PermissionService:
    
    @staticmethod
    def create_task_permissions(task: Task):
        """Calculate and store permissions once when task is created"""
        actions = Action.objects.filter(processactionrole__process=task.process).distinct()
        permissions = []
        
        for action in actions:
            users_with_rules = PermissionService._resolve_users_for_action(task, action)
            for user, role_type in users_with_rules:
                permissions.append(TaskPermission(
                    task=task,
                    action=action,
                    user=user,
                    role_type=role_type
                ))
        
        TaskPermission.objects.bulk_create(permissions, ignore_conflicts=True)
    
    @staticmethod
    def _resolve_users_for_action(task: Task, action: Action) -> List[tuple]:
        """Returns list of (user, role_type) tuples"""
        users_with_rules = []
        role_definitions = ProcessActionRole.objects.filter(
            process=task.process,
            action=action
        ).select_related('specific_user', 'specific_role', 'specific_department')

        for role_def in role_definitions:
            users = PermissionService._resolve_users_for_role(task, role_def)
            # Use the actual role_type enum value instead of constructing a string
            users_with_rules.extend([(user, role_def.role_type) for user in users])

        return users_with_rules
    
    @staticmethod
    def _resolve_users_for_role(task: Task, role_def: ProcessActionRole) -> List[User]:
        """Your original logic - unchanged"""
        users = []

        if role_def.role_type == RoleType.REQUESTOR:
            users.append(task.created_by)

        elif role_def.role_type == RoleType.REQUESTOR_MANAGER:
            if hasattr(task.created_by, 'supervisor') and task.created_by.supervisor:
                users.append(task.created_by.supervisor)

        elif role_def.role_type == RoleType.REQUESTOR_DEPARTMENT_HEAD:
            if task.created_by.department:
                dept_manager = PermissionService._get_department_manager(task.created_by.department)
                if dept_manager:
                    users.append(dept_manager)

        elif role_def.role_type == RoleType.SPECIFIC_DEPARTMENT_HEAD:
            if role_def.specific_department:
                dept_manager = PermissionService._get_department_manager(role_def.specific_department)
                if dept_manager:
                    users.append(dept_manager)

        elif role_def.role_type == RoleType.ASSIGNEE:
            assignees = PermissionService._get_task_assignees(task)
            users.extend(assignees)

        elif role_def.role_type == RoleType.SPECIFIC_USER and role_def.specific_user:
            users.append(role_def.specific_user)

        elif role_def.role_type == RoleType.SPECIFIC_ROLE and role_def.specific_role:
            users.extend(
                User.objects.filter(role=role_def.specific_role, is_active=True)
            )

        elif role_def.role_type == RoleType.SPECIFIC_DEPARTMENT and role_def.specific_department:
            users.extend(
                User.objects.filter(department=role_def.specific_department, is_active=True)
            )

        elif role_def.role_type == RoleType.SPECIFIC_ROLE_AND_DEPARTMENT:
            if role_def.specific_role and role_def.specific_department:
                users.extend(
                    User.objects.filter(
                        role=role_def.specific_role,
                        department=role_def.specific_department,
                        is_active=True
                    )
                )

        return users

    @staticmethod
    def _get_department_manager(department):
        """Return department manager"""
        if not department:
            return None
        return User.objects.filter(department=department, role__name_en='manager').first()

    @staticmethod
    def _get_task_assignees(task: Task) -> List[User]:
        """Get task assignees from task data"""
        assignees = []
        assignee_fields = task.data.filter(field__field_type='assignee')

        for field in assignee_fields:
            try:
                user = User.objects.get(id=field.value)
                assignees.append(user)
            except (User.DoesNotExist, ValueError):
                continue

        return assignees

    # Fast lookup methods
    @staticmethod
    def user_can_perform_action(user: User, task: Task, action: Action) -> bool:
        """Fast O(1) permission check"""
        return TaskPermission.objects.filter(
            task=task,
            action=action,
            user=user
        ).exists()
    
    @staticmethod
    def get_allowed_users_for_action(task: Task, action: Action) -> Set[User]:
        """Fast lookup of allowed users"""
        permissions = TaskPermission.objects.filter(
            task=task,
            action=action
        ).select_related('user')
        
        return {perm.user for perm in permissions}