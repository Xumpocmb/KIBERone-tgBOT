from django.urls import path
from app_admin_management.views import index_admin, user_data_from_excel

app_name = 'app_admin_management'

urlpatterns = [
    path('index_admin/', index_admin, name='index_admin'),
    path('user_data_from_excel/', user_data_from_excel, name='user_data_from_excel'),
]