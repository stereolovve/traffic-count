# auth/backend/api/logout.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User

class LogoutView(APIView):
    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist() 
            return Response({"detail": "Logout realizado com sucesso."})
        except Exception as e:
            return Response({"error": str(e)}, status=400)
