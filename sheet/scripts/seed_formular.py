import csv
import os
from decimal import Decimal
from django.conf import settings
from django.db import transaction
from sheet.models import FormularTemplate, ProductTemplate

@transaction.atomic
def run():

    csv_file_path = os.path.join(settings.BASE_DIR, 'sheet', 'scripts', 'formular_seed.csv')
    
    if not os.path.exists(csv_file_path):
        print(f"CSV file not found at: {csv_file_path}")
        return
    
    print("Clearing existing data...")
    ProductTemplate.objects.all().delete()
    FormularTemplate.objects.all().delete()
    
    formular_templates = {}  # Cache to avoid duplicate FormularTemplates
    products_created = 0
    formulars_created = 0
    
    try:
        with open(csv_file_path, 'r', encoding='utf-8-sig') as file:
            csv_reader = csv.DictReader(file)
            
            print("Processing CSV data...")
            
            for row_num, row in enumerate(csv_reader, start=2):  # start=2 because row 1 is header
                try:
                    formular_code = row['formular_code'].strip()
                    product_code = row['product_code'].strip()
                    ratio = row['ratio'].strip()
                    viscosity = row['viscosity'].strip()
                    product_type = row['type'].strip() if 'type' in row and row['type'] else 'Standard'
                    
                    # Validate required fields
                    if not formular_code or not product_code or not ratio:
                        print(f"Warning: Skipping row {row_num} - missing required data")
                        continue
                    
                    # Get or create FormularTemplate
                    if formular_code not in formular_templates:
                        formular_template, created = FormularTemplate.objects.get_or_create(
                            code=formular_code,
                            viscosity=viscosity if viscosity else None,
                        )
                        formular_templates[formular_code] = formular_template
                        if created:
                            formulars_created += 1
                            print(f"Created FormularTemplate: {formular_code}")
                    else:
                        formular_template = formular_templates[formular_code]
                    
                    # Create ProductTemplate (unique per formular_code + product_code combination)
                    product_template, created = ProductTemplate.objects.get_or_create(
                        formular_template=formular_template,
                        code=product_code,
                        name=product_code,
                        type=product_type,
                        type_en=product_type,
                        type_vi=product_type,
                        type_zh_hant=product_type,
                        ratio=ratio,
                        unit='g'
                    )
                    
                    if created:
                        products_created += 1
                        print(f"Created ProductTemplate: {product_code} for formular {formular_code}")
                    else:
                        print(f"ProductTemplate already exists: {product_code} for formular {formular_code}")
                
                except Exception as e:
                    print(f"Error processing row {row_num}: {e}")
                    print(f"Row data: {row}")
                    # Re-raise to trigger rollback
                    raise
    
    except FileNotFoundError:
        print(f"Error: Could not find CSV file at {csv_file_path}")
        return
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        # Re-raise to trigger rollback
        raise
    
    print(f"\n--- Seeding Complete ---")
    print(f"FormularTemplates created: {formulars_created}")
    print(f"ProductTemplates created: {products_created}")
    print(f"Total FormularTemplates in database: {FormularTemplate.objects.count()}")
    print(f"Total ProductTemplates in database: {ProductTemplate.objects.count()}")