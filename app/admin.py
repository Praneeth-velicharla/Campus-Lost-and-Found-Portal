from django.contrib import admin
from .models import LostItem, FoundItem, MatchNotificationStatus

@admin.register(LostItem)
class LostItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'date_reported')
    search_fields = ('name', 'description', 'features')

@admin.register(FoundItem)
class FoundItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'date_reported')
    search_fields = ('name', 'description', 'features')

admin.site.register(MatchNotificationStatus)