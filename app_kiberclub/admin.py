from django.contrib import admin

from app_kiberclub.models import UserData, Locations


# Register your models here.


@admin.register(UserData)
class UserDataAdmin(admin.ModelAdmin):
    pass


@admin.register(Locations)
class LocationsAdmin(admin.ModelAdmin):
    pass
