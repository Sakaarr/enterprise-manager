from django.shortcuts import render
from .serializers import UserSerializer, LoginSerializer, ProfileSerializer, PasswordResetSerializer, SetNewPasswordSerializer
from django.contrib.auth import get_user_model, authenticate, login, logout
from rest_framework.permissions import IsAuthenticated
from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
from rest_framework import viewsets
from .models import *
from common.response import error_response, success_response
from django.contrib.auth.mixins import LoginRequiredMixin
from common.custom_permission import IsOwnerOrReadOnly
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.urls import reverse
from django.contrib.auth.tokens import default_token_generator
from rest_framework.response import Response
import jwt
from django.conf import settings
from urllib.parse import urlencode
from rest_framework import serializers
import environ
from django.core.mail import send_mail
from drf_spectacular.utils import extend_schema, OpenApiParameter

env = environ.Env()
env.read_env(str(settings.BASE_DIR / ".env"))

User = get_user_model()
env = environ.Env()
env.read_env(str(settings.BASE_DIR / ".env"))
class LoginApiView(APIView):
    serializer_class = LoginSerializer

    @extend_schema(
        operation_id="API To Login The User",
        description="API To Login The User",
        request=LoginSerializer,
    )
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        return success_response(
            status_code=status.HTTP_200_OK,
            message="Login Successful",
            description="User login successful.",
            data=serializer.validated_data,
        )

class ProfileAPIView(APIView):
    permission_class = [IsAuthenticated]
    serializer_class = ProfileSerializer

    @extend_schema(
        operation_id="API To Get Profie of Currently Login User",
        description="API To Get Profie of Currently Login Use",
        request=ProfileSerializer,
    )
    def get(self, request):
        try:
            profile = User.objects.get(id=request.user.id)
            serializer = ProfileSerializer(profile)
            return success_response(
                status_code=status.HTTP_200_OK,
                message="Profiles Retrieved Successfully",
                description="Retrieved profiles for the authenticated user.",
                data=serializer.data
            )
        except User.DoesNotExist:
            return error_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message="No Profile Found",
                description="No profile found for the current user",
                data=None,
            )


class ProfileDetailAPIView(APIView):
    permission_class = [IsAuthenticated, IsOwnerOrReadOnly]
    serializer_class = ProfileSerializer

    def get_object(self, pk):
        try:
            profile = User.objects.get(pk=pk)
            self.check_object_permissions(self.request, profile)
            return profile
        except User.DoesNotExist:
            '''
            in case of validation error (user this error format)
            '''
            raise ValidationError("Profile not found.")

    @extend_schema(
        operation_id="API To Get Profie of given id",
        description="API To Get Profie of given id",
        request=ProfileSerializer,
    )
    def get(self, request, pk):
        profile = self.get_object(pk)
        serializer = ProfileSerializer(profile)
        return success_response(
            status_code=status.HTTP_200_OK,
            message="Profile Retrieved Successfully",
            description="Retrieved profile details.",
            data=serializer.data
        )

    def patch(self, request, pk):
        profile = self.get_object(pk)
        serializer = ProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)

        return success_response(
            status_code=status.HTTP_200_OK,
            message="Profile Updated Successfully",
            description="Updated profile details.",
            data=serializer.data
        )

    def delete(self, request, pk):
        profile = self.get_object(pk)
        profile.delete()
        return success_response(
            status_code=status.HTTP_204_NO_CONTENT,
            message="Profile Deleted Successfully",
            description="Deleted profile.",
            data=None
        )


class ForgetPasswordView(APIView):
    serializer_class = PasswordResetSerializer

    @extend_schema(
        operation_id="API To Reset Password",
        description="API To Reset Password",
        request=PasswordResetSerializer,
    )
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        user = User.objects.get(email=email)
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        print(uid, token)
        BASE_URL = env("BASE_URL")

        reset_url = f"http://localhost:5173/reset-password?token={token}&uidb64={uid}"

        send_mail(
            'Password Reset',
            f'Click the following link to reset your password: {reset_url}',
            'money.minder077@gmail.com',
            [email],
        )
        return success_response(
            status_code=status.HTTP_200_OK,
            message="Password reset link sent.",
            description="Password reset link has been sent to your email.",
            data=None,
        )


class PasswordResetConfirmView(APIView):
    serializer_class = SetNewPasswordSerializer

    def post(self, request, uidb64, token, *args, **kwargs):
        try:
            uid = urlsafe_base64_decode(uidb64)
            print(uid)
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is not None and default_token_generator.check_token(user, token):
            serializer = self.serializer_class(data=request.data)
            serializer.is_valid(raise_exception=True)
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response({
                "message": "Password has been reset successfully."
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                "message": "Invalid token or user ID."
            }, status=status.HTTP_400_BAD_REQUEST)

