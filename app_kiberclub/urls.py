from django.urls import path

from app_kiberclub.views import open_profile, choose_child, save_init_data, index, error_page, submit_review

app_name = 'app_kiberclub'

urlpatterns = [
    path('index/', index, name='index'),
    path('save_init_data/', save_init_data, name='save_init_data'),
    path('choose_child/', choose_child, name='choose_child'),
    path('profile/', open_profile, name='open_profile'),
    path('error/', error_page, name='error_page'),
    path('review_from_parent/', submit_review, name='review_from_parent'),
]