from typing import List, Set
from process.models import ProcessActionRole, RoleType, Action
from task.models import Task
from user.models import User

class PermissionService:

    @staticmethod
    def get_allowed_users_for_action(task: Task, action: Action) -> Set[User]:
        """
        Dynamically resolve which users can perform an action on a task.
        """
        allowed_users = set()
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
        users = []

        if role_def.role_type == RoleType.REQUESTOR:
            users.append(task.created_by)

        elif role_def.role_type == RoleType.REQUESTOR_MANAGER and task.created_by.supervisor:
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
        """Return department manager (role = 'manager')"""
        if not department:
            return None
        return User.objects.filter(department=department, role__name_en='manager').first()

    @staticmethod
    def _get_task_assignees(task: Task) -> List[User]:
        """Support one or more assignees stored in task data"""
        assignees = []
        assignee_fields = task.data.filter(field__field_type='assignee')

        for field in assignee_fields:
            try:
                user = User.objects.get(id=field.value)
                assignees.append(user)
            except (User.DoesNotExist, ValueError):
                continue

        return assignees

    @staticmethod
    def user_can_perform_action(user: User, task: Task, action: Action) -> bool:
        """
        Fast permission check for whether user can perform the action.
        """
        role_definitions = ProcessActionRole.objects.filter(
            process=task.process,
            action=action
        )

        for role_def in role_definitions:
            users = PermissionService._resolve_users_for_role(task, role_def)
            if user in users:
                return True
        return False
