import csv
from user.models import User, Department, Role, BusinessFunction
from django.conf import settings
import os

def run():
    csv_path = os.path.join(settings.BASE_DIR, 'user', 'scripts', 'user_seed.csv')

    with open(csv_path, newline='', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Skip if username already exists
            if User.objects.filter(username=row['username']).exists():
                print(f"Skipping {row['username']} - already exists")
                continue
            
            # Get existing objects only (don't create new ones)
            try:
                department = Department.objects.get(name=row['department_name'])
                role = Role.objects.get(name=row['role_name'])
                business_function = BusinessFunction.objects.get(name=row['business_function_name'])
            except (Department.DoesNotExist, Role.DoesNotExist, BusinessFunction.DoesNotExist) as e:
                print(f"Skipping {row['username']} - required object not found: {e}")
                continue
            
            # Create user
            user = User.objects.create_user(
                username=row['username'],
                first_name=row['first_name'],
                last_name=row['last_name'],
                password=row['password'],
                department=department,
                role=role,
                business_function=business_function,
                is_password_changed=False
            )
            print(f"Created user: {user.username}")