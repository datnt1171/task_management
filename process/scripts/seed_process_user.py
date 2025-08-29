import csv
from user.models import User
from process.models import Process, ProcessUser
from django.conf import settings
import os

def run():
    # Set your specific process ID here
    PROCESS_ID = '1234-5678'
    
    csv_path = os.path.join(settings.BASE_DIR, 'process', 'scripts', 'process_user_seed.csv')

    # Get the process object
    try:
        process = Process.objects.get(id=PROCESS_ID)
    except Process.DoesNotExist:
        print(f"Process with ID {PROCESS_ID} not found!")
        return

    with open(csv_path, newline='', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            try:
                # Get the user
                user = User.objects.get(username=row['username'])
                
                # Check if ProcessUser already exists (due to unique constraint)
                process_user, created = ProcessUser.objects.get_or_create(
                    process=process,
                    user=user
                )
                
                if created:
                    print(f"Added user {user.username} to process {process.id}")
                else:
                    print(f"User {user.username} already assigned to process {process.id}")
                    
            except User.DoesNotExist:
                print(f"User {row['username']} not found - skipping")
            except Exception as e:
                print(f"Error processing {row['username']}: {e}")