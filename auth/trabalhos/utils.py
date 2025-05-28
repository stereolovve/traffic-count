"""
Utility functions for the trabalhos app
"""
import logging
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from django.http import JsonResponse
from django.conf import settings

logger = logging.getLogger(__name__)

def api_error_handler(func):
    """Decorator to handle API errors consistently"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"API Error: {str(e)}")
            return JsonResponse(
                {"error": str(e)}, 
                status=500
            )
    return wrapper

@api_view(['GET'])
@authentication_classes([JWTAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
@api_error_handler
def api_check_auth(request):
    """
    Simple endpoint to check if authentication is working
    """
    return JsonResponse({
        "authenticated": True,
        "user": request.user.username,
        "auth_method": str(request.successful_authenticator.__class__.__name__) if hasattr(request, 'successful_authenticator') else "Unknown"
    })
