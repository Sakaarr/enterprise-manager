from .serializers import SetNewPasswordSerializer,ChangePasswordSerializer,UserSerializer,LoginSerializer,ProfileSerializer, PasswordResetSerializer, RoleSerializer
from django.contrib.auth import get_user_model, authenticate, login, logout
from rest_framework.permissions import IsAuthenticated
from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
from rest_framework import viewsets
from .models import *
from common.response import error_response, success_response
from django.contrib.auth.mixins import LoginRequiredMixin
from common.custom_permission import IsOwnerOrReadOnly, IsAdminRole
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
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from drf_spectacular.utils import extend_schema, OpenApiParameter

User = get_user_model()
env = environ.Env()
env.read_env(str(settings.BASE_DIR / ".env"))
class LoginApiView(APIView):
    serializer_class = LoginSerializer

    @extend_schema(
        tags=["Authentication"],
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
        tags=["Authentication"],
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


@extend_schema(
        tags=["Authentication"],
        operation_id="API To Get Profie of given id",
        description="API To Get Profie of given id",
        request=ProfileSerializer,
    )
class ProfileDetailAPIView(APIView):
    
    permission_class = [IsAuthenticated]
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
        tags=["Authentication"],
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

        reset_url = f"http://localhost:8000/api/users/reset-password-confirm/{uid}/{token}/"

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



@extend_schema(
        tags=["Authentication"],
        operation_id="API to manage roles (CRUD)",
        description="API endpoints for creating, updating, retrieving, and deleting user roles.",
    )
class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer

    
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    


class AdminCreateUserAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Authentication"],
        operation_id="Admin Create User",
        description="Allows an admin to create a new user and send credentials via email.",
        request=UserSerializer
    )
    def post(self, request, *args, **kwargs):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
             # Set is_staff to True for admin-created users

            # Send credentials email
            password = request.data.get('password')
            send_mail(
                subject="Your Account Has Been Created",
                message=(
                    f"Dear {user.first_name},\n\n"
                    f"Your account has been created by the admin.\n"
                    f"Email: {user.email}\n"
                    f"Password: {password}\n\n"
                    f"Please change your password after logging in."
                ),
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[user.email],
                fail_silently=False,
            )

            return success_response(
                status_code=status.HTTP_200_OK,
                message="User created successfully and credentials emailed.",
                description="User created successfully and credentials emailed.",
                data=UserSerializer(user).data
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    
class ChangePasswordAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Authentication"],
        operation_id="Change Password",
        description="Allow authenticated users to change their password by entering old and new password.",
        request=ChangePasswordSerializer
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return success_response(
                status_code=status.HTTP_200_OK,
                message="Password changed successfully.",
                description="The user's password was updated successfully.",
                data=None
            )
        return error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Password change failed.",
            description="There was an error changing the password.",
            data=serializer.errors
        )
        
class PasswordResetConfirmView(APIView):
    serializer_class = SetNewPasswordSerializer
    @extend_schema(
        tags=["Authentication"],
        operation_id="API to Reset Confirm Password",
        description="API to Reset Confirm Password",
    )

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

