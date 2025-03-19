from django.urls import path
from app_accounts.views import signup, login_view, logout_view

app_name = 'app_accounts'

urlpatterns = [
    path('signup/', signup, name='signup'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
]
