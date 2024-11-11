from django.urls import path
from .views import LoginView
from .views import RegisterView


urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('register/', RegisterView.as_view(), name='register')
]
