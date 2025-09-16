# scripts/seed_user_onsite.py
"""
Django runscript to generate sample UserFactoryOnsite data
Usage: python manage.py runscript seed_user_onsite
"""

from user.models import User, UserFactoryOnsite
from django.db import transaction
import random


def run():
    """
    Generate sample UserFactoryOnsite data
    Constraint: unique_user_onsite (user, year, month) - one factory per user per month
    """
    
    # Sample data
    usernames = ['VL0826', 'VL0804', 'VL1210', 'VL0798', 'VL0891']
    factories = ['30127', '30895.4', '30150.1', '30301', '30567.1']
    year = 2025
    months = [1, 2, 3]
    
    print("🌱 Starting to seed UserFactoryOnsite data...")
    print("📋 Constraint: Each user can have only ONE factory per month")
    
    try:
        with transaction.atomic():
            # Check if users exist
            existing_users = User.objects.filter(username__in=usernames)
            existing_usernames = list(existing_users.values_list('username', flat=True))
            
            if not existing_users:
                print("❌ No users found with the specified usernames!")
                print(f"   Looking for: {usernames}")
                print("   Please create users first or update the usernames in the script.")
                return
            
            if len(existing_usernames) < len(usernames):
                missing = set(usernames) - set(existing_usernames)
                print(f"⚠️  Some users not found: {missing}")
                print(f"   Found users: {existing_usernames}")
            
            # Clear existing onsite data for these users (optional)
            UserFactoryOnsite.objects.filter(
                user__username__in=usernames,
                year=year
            ).delete()
            print(f"🧹 Cleared existing onsite data for {year}")
            
            created_count = 0
            
            # Generate data for each user
            for user in existing_users:
                print(f"\n👤 Processing user: {user.username}")
                
                # Randomly select which months this user will be onsite
                user_months = random.sample(months, random.randint(1, len(months)))  # 1-3 months per user
                
                for month in user_months:
                    # Randomly assign ONE factory for this user-month combination
                    selected_factory = random.choice(factories)
                    
                    onsite_record, created = UserFactoryOnsite.objects.get_or_create(
                        user=user,
                        year=year,
                        month=month,
                        defaults={'factory': selected_factory}  # Only set factory if creating new record
                    )
                    
                    if created:
                        print(f"   ✅ Created: Month {month} -> Factory {selected_factory}")
                        created_count += 1
                    else:
                        print(f"   ⚠️  Already exists: Month {month} -> Factory {onsite_record.factory}")
            
            print(f"\n🎉 Successfully created {created_count} UserFactoryOnsite records!")
            print(f"📊 Summary:")
            print(f"   Users processed: {len(existing_users)}")
            print(f"   Year: {year}")
            print(f"   Available factories: {factories}")
            print(f"   Available months: {months}")
            
            # Display final count and breakdown
            total_records = UserFactoryOnsite.objects.filter(year=year).count()
            print(f"   Total onsite records for {year}: {total_records}")
            
            # Show distribution by month
            print(f"\n📈 Distribution by month:")
            for month in months:
                month_count = UserFactoryOnsite.objects.filter(year=year, month=month).count()
                print(f"   Month {month}: {month_count} users onsite")
            
            # Show which factories were assigned
            print(f"\n🏭 Factory assignments:")
            for record in UserFactoryOnsite.objects.filter(year=year).select_related('user').order_by('user__username', 'month'):
                print(f"   {record.user.username} - Month {record.month}: Factory {record.factory}")
            
    except Exception as e:
        print(f"❌ Error occurred: {str(e)}")
        raise


def run_alternative():
    """
    Alternative approach - create all combinations for all users
    """
    usernames = ['VL0826', 'VL0804', 'VL1210', 'VL0798', 'VL0891']
    factories = ['30127', '30895.4', '30150.1', '30301', '30567.1']
    year = 2025
    months = [1, 2, 3]
    
    print("🌱 Creating ALL combinations for ALL users...")
    
    try:
        with transaction.atomic():
            users = User.objects.filter(username__in=usernames)
            
            if not users:
                print("❌ No users found!")
                return
            
            created_count = 0
            
            for user in users:
                for factory in factories:
                    for month in months:
                        onsite_record, created = UserFactoryOnsite.objects.get_or_create(
                            user=user,
                            factory=factory,
                            year=year,
                            month=month
                        )
                        
                        if created:
                            created_count += 1
            
            print(f"🎉 Created {created_count} records!")
            print(f"📊 Total combinations: {len(users)} users × {len(factories)} factories × {len(months)} months = {len(users) * len(factories) * len(months)}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        raise


if __name__ == "__main__":
    # For testing locally
    run()