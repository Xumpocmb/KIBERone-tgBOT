from django.contrib import admin

from app_kiberclub.models import UserData, Locations, BranchesTelegramLink, FAQ, Promotion, PartnerCategory, Partner, Link, Manager


# Register your models here.


@admin.register(UserData)
class UserDataAdmin(admin.ModelAdmin):
    fields = ('tg_id', 'phone_number', 'is_study', 'balance',
              'paid_lesson_count', 'next_lesson_date', 'user_branch_ids', 'user_crm_id', 'user_lessons',
              'notified', 'created_at', 'customer_data')
    list_display = ('tg_id', 'phone_number', 'is_study', 'balance')
    search_fields = ('tg_id', 'phone_number')


@admin.register(Locations)
class LocationsAdmin(admin.ModelAdmin):
    list_display = ('location_name',)
    search_fields = ('location_id', 'location_name')


admin.site.register(BranchesTelegramLink)
admin.site.register(FAQ)
admin.site.register(Promotion)
admin.site.register(PartnerCategory)
admin.site.register(Partner)
admin.site.register(Link)
admin.site.register(Manager)
