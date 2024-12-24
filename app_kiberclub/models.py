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
    notified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    customer_data = models.TextField(blank=True, null=True)
    kiberons_count = models.IntegerField(default=0, null=True, blank=True)
    kiberons_count_after_orders = models.IntegerField(default=0, null=True, blank=True)
    user_lessons = models.BooleanField(default=False, null=True, blank=True)

    objects = models.Manager()

    class Meta:
        managed = True
        db_table = 'users'
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

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
        managed = True
        db_table = 'Locations'
        verbose_name = 'Локация'
        verbose_name_plural = 'Локации'

    def __str__(self):
        return self.location_name

class BranchesTelegramLink(models.Model):
    branch_id = models.IntegerField()
    link = models.CharField(max_length=255)

    objects = models.Manager()

    class Meta:
        managed = False
        db_table = 'branches_telegram_link'
        verbose_name = 'Телеграм ссылка на бранч'
        verbose_name_plural = 'Телеграм ссылки на бранч'

    def __str__(self):
        return str(self.branch_id)

class FAQ(models.Model):
    question = models.CharField(max_length=255)
    answer = models.CharField(max_length=255)

    objects = models.Manager()

    class Meta:
        managed = False
        db_table = 'FAQ'
        verbose_name = 'FAQ'
        verbose_name_plural = 'FAQ'

    def __str__(self):
        return self.question

class Promotion(models.Model):
    question = models.CharField(max_length=255)
    answer = models.CharField(max_length=255)

    objects = models.Manager()

    class Meta:
        managed = False
        db_table = 'Promotion'
        verbose_name = 'Промо акция'
        verbose_name_plural = 'Промо акции'

    def __str__(self):
        return self.question

class PartnerCategory(models.Model):
    category = models.CharField(max_length=255)

    objects = models.Manager()

    class Meta:
        managed = False
        db_table = 'PartnerCategory'
        verbose_name = 'Категория партнера'
        verbose_name_plural = 'Категории партнеров'

    def __str__(self):
        return self.category

class Partner(models.Model):
    partner = models.CharField(max_length=255)
    description = models.CharField(max_length=255)
    category = models.ForeignKey(PartnerCategory, on_delete=models.CASCADE, related_name='partners')

    objects = models.Manager()

    class Meta:
        managed = False
        db_table = 'Partner'
        verbose_name = 'Партнер'
        verbose_name_plural = 'Партнеры'

    def __str__(self):
        return self.partner

class Link(models.Model):
    link_name = models.CharField(max_length=255)
    link_url = models.CharField(max_length=255)

    objects = models.Manager()

    class Meta:
        managed = False
        db_table = 'Link'
        verbose_name = 'Ссылка на соц сеть'
        verbose_name_plural = 'Ссылки на соц сети'

    def __str__(self):
        return self.link_name

class Manager(models.Model):
    branch = models.IntegerField()
    location = models.IntegerField()
    manager = models.CharField(max_length=255)
    link = models.CharField(max_length=255)

    objects = models.Manager()

    class Meta:
        managed = False
        db_table = 'Manager'
        verbose_name = 'Менеджер'
        verbose_name_plural = 'Менеджеры'

    def __str__(self):
        return self.manager


