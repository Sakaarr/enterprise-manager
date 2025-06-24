from django.urls import path, include
from users import views as apiview
app_name = "API"
urlpatterns = [
    path("login/", apiview.LoginApiView.as_view(), name="login"),
    path('profile/', apiview.ProfileAPIView.as_view(), name='profile-list-create'),
    path('profiles/<int:pk>/', apiview.ProfileDetailAPIView.as_view(), name='profile-detail'),
    path('forgetpw/', apiview.ForgetPasswordView.as_view(), name="forgetpw"),
    path('password_reset_confirm/<uidb64>/<token>/', apiview.PasswordResetConfirmView.as_view(),
         name='password_reset_confirm'),
]