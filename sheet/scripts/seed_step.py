import csv
from sheet.models import StepTemplate
from django.conf import settings
import os
from django.db import transaction

def run():
    csv_path = os.path.join(settings.BASE_DIR, 'sheet', 'scripts', 'step_seed.csv')
    with transaction.atomic():
        with open(csv_path, newline='', encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                StepTemplate.objects.create(
                    name=row['name_en'],
                    name_en=row['name_en'],
                    name_vi=row['name_vi'],
                    name_zh_hant=row['name_zh_hant'],

                    short_name=row['short_name_en'],
                    short_name_en=row['short_name_en'],
                    short_name_vi=row['short_name_vi'],
                    short_name_zh_hant=row['short_name_zh_hant'],

                    spec=row['spec_en'],
                    spec_en=row['spec_en'],
                    spec_vi=row['spec_vi'],
                    spec_zh_hant=row['spec_zh_hant'],

                    sanding=row['sanding_en'],
                    sanding_en=row['sanding_en'],
                    sanding_vi=row['sanding_vi'],
                    sanding_zh_hant=row['sanding_zh_hant'],

                    hold_time=row['hold_time'],
                    consumption=row['consumption'] 
                )