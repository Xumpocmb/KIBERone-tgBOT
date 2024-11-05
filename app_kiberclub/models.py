from django.db import models


class UserData(models.Model):
    tg_id = models.CharField(max_length=255, unique=True)
    first_name = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    username = models.CharField(max_length=255, blank=True, null=True)
    phone_number = models.CharField(max_length=255, blank=True, null=True)
    is_study = models.IntegerField(blank=True, null=True)
    balance = models.CharField(max_length=255, blank=True, null=True)
    paid_lesson_count = models.IntegerField(blank=True, null=True)
    next_lesson_date = models.CharField(max_length=255, blank=True, null=True)
    user_branch_ids = models.CharField(max_length=255, blank=True, null=True)
    user_crm_id = models.IntegerField(blank=True, null=True)
    user_lessons = models.BooleanField(default=False)
    notified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    customer_data = models.TextField(blank=True, null=True)

    objects = models.Manager()

    class Meta:
        managed = False
        db_table = 'users'


    def __str__(self):
        return f"user: {self.username or self.tg_id}"


class Locations(models.Model):
    id = models.IntegerField(primary_key=True)
    location_branch_id = models.IntegerField()
    location_id = models.IntegerField()
    location_name = models.CharField(max_length=255)
    location_map_link = models.CharField(max_length=255)
    sheet_url = models.CharField(max_length=255)
    sheet_names = models.CharField(max_length=255)

    objects = models.Manager()

    class Meta:
        managed = False
        db_table = 'Locations'

    def __str__(self):
        return self.location_name