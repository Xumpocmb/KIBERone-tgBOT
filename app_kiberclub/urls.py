from django.urls import path

from app_kiberclub.views import get_resume, get_response_from_page

urlpatterns = [
    path('resume/', get_resume, name='get_resume'),
    path('data_from_page/', get_response_from_page, name='data_from_page'),
]