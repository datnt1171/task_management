import csv
from user.models import BusinessFunction
from django.conf import settings
import os

def run():
    csv_path = os.path.join(settings.BASE_DIR, 'user', 'scripts', 'business_function_seed.csv')

    with open(csv_path, newline='', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            BusinessFunction.objects.create(
                name=row['business_function'],
                name_en=row['business_function_en'],
                name_vi=row['business_function_vi'],
                name_zh_hant=row['business_function_zh_hant'],
            )
