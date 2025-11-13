from django.contrib import admin
from .models import Trip, Stop

class StopAdmin(admin.ModelAdmin):
    list_display = ('location', 'odometer', 'toll_station', 'created_at')


class StopInline(admin.TabularInline):
    model = Stop
    extra = 0
    fields = ('order', 'location', 'odometer', 'toll_station')
    ordering = ('order',)
    show_change_link = True


class TripAdmin(admin.ModelAdmin):
    list_display = ('date', 'license_plate', 'driver__username', 'created_at')
    list_filter = ('license_plate',)
    search_fields = ('driver__username',)
    ordering = ('date',)
    inlines = [StopInline]


admin.site.register(Trip, TripAdmin)
admin.site.register(Stop, StopAdmin)

