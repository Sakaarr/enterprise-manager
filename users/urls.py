from django.urls import path, include
from users import views as apiview
from rest_framework.routers import DefaultRouter
app_name = "Auth API"
router = DefaultRouter()
router.register(r'roles', apiview.RoleViewSet, basename='role')

urlpatterns = [
    path("login/", apiview.LoginApiView.as_view(), name="login"),
    path('profile/', apiview.ProfileAPIView.as_view(), name='profile-list-create'),
    path('profiles/<int:pk>/', apiview.ProfileDetailAPIView.as_view(), name='profile-detail'),
    path('forgetpw/', apiview.ForgetPasswordView.as_view(), name="forgetpw"),
    path('create-user/', apiview.AdminCreateUserAPIView.as_view(), name='create-user'),
    path('change-password/', apiview.ChangePasswordAPIView.as_view(), name='change-password'),
    path('password_reset_confirm/<uidb64>/<token>/', apiview.PasswordResetConfirmView.as_view(),
         name='password_reset_confirm'),
]
urlpatterns += router.urls