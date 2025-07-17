from django.urls import path, include
from users import views as apiview
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

app_name = "Auth API"
router = DefaultRouter()
router.register(r'roles', apiview.RoleViewSet, basename='role')
router.register(r'team-members', apiview.TeamMemberViewSet, basename='team-member')

urlpatterns = [
    path("login/", apiview.LoginApiView.as_view(), name="login"),
    path('profile/', apiview.ProfileAPIView.as_view(), name='profile-list-create'),
    path('profiles/<int:pk>/', apiview.ProfileDetailAPIView.as_view(), name='profile-detail'),
    path('forgetpw/', apiview.ForgetPasswordView.as_view(), name="forgetpw"),
    path('create-staff/', apiview.AdminCreateUserAPIView.as_view(), name='create-user'),
    path('change-password/', apiview.ChangePasswordAPIView.as_view(), name='change-password'),
    path('password_reset_confirm/<uidb64>/<token>/', apiview.PasswordResetConfirmView.as_view(),
         name='password_reset_confirm'),
    path('articles/', apiview.ArticleListCreateView.as_view(), name='article-list-create'),
    path('articles/<int:pk>/', apiview.ArticleDetailView.as_view(), name='article-detail'),
    path('contact-us/', apiview.ContactUsAPIView.as_view(), name='contact-us'),
    path('checklogin/', apiview.CheckLoginView.as_view(), name='checklogin'),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
urlpatterns += router.urls