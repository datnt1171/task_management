# users/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import User, Department, Role, BusinessFunction, Permission, RolePermission, UserFactoryOnsite

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('username', 'email', 'department', 'role', 'business_function', 'supervisor')

class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = '__all__'

class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = User
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # If the current user is not a superuser, exclude all superusers from the list
        if not request.user.is_superuser:
            qs = qs.filter(is_superuser=False)
        return qs
    
    def has_change_permission(self, request, obj=None):
        if obj and obj.is_superuser and not request.user.is_superuser:
            return False
        return super().has_change_permission(request, obj)
    
    def has_delete_permission(self, request, obj=None):
        if obj and obj.is_superuser and not request.user.is_superuser:
            return False
        return super().has_delete_permission(request, obj)
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # If the user is not a superuser, make is_superuser field disabled
        if not request.user.is_superuser:
            if 'is_superuser' in form.base_fields:
                form.base_fields['is_superuser'].disabled = True
        return form

    
    # Fields to show in the add user form
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 
                      'department', 'role', 'supervisor', 'business_function',
                      'first_name', 'last_name', 'is_active', 'is_staff', 'is_password_changed'),
        }),
    )
    
    # Fields to show in the change user form
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions', 'is_password_changed'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
        ('Work info', {'fields': ('department', 'role', 'business_function', 'supervisor')}),
    )
    
    list_display = ('username', 'full_name', 'department', 'role', 'business_function', 'is_active')
    list_filter = ('department', 'role', 'business_function', 'is_active')
    search_fields = ('username', 'first_name', 'last_name')
    ordering = ('username',)

class UserFactoryOnsiteAdmin(admin.ModelAdmin):
    list_display = ('user__username', 'factory', 'year', 'month',)
    list_filter = ('month',)
    search_fields = ('user__username', 'factory',)
    ordering = ('-year', '-month',)

admin.site.register(User, CustomUserAdmin)
admin.site.register(Department)
admin.site.register(Role)
admin.site.register(BusinessFunction)
admin.site.register(Permission)
admin.site.register(RolePermission)
admin.site.register(UserFactoryOnsite, UserFactoryOnsiteAdmin)