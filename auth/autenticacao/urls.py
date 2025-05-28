# autenticacao/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from .views import LoginView, RegisterView, RefreshTokenView, SessionTokenView, check_auth
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    # Autenticação
    path('login/', LoginView.as_view(), name='login'),
    path('register/', RegisterView.as_view(), name='register'),
    path('logout/', auth_views.LogoutView.as_view(template_name='registration/login.html'), name='logout'),
    path('refresh/', RefreshTokenView.as_view(), name='refresh'),

    # JWT Token
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    
    # Session-based token generation (for already authenticated users)
    path("api/token/", SessionTokenView.as_view(), name="session_token"),
    
    # Authentication check endpoint
    path("check-auth/", check_auth, name="check_auth"),
]