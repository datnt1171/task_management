import csv
from user.models import Permission
from django.conf import settings
import os

def run():
    csv_path = os.path.join(settings.BASE_DIR, 'user', 'scripts', 'permission_seed.csv')

    with open(csv_path, newline='', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            Permission.objects.create(
                name=row['name'],
                action=row['action'],
                service=row['service'],
                resource=row['resource'],
            )
