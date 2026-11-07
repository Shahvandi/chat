from django.urls import path
from .views import Sign, SignIn, SendOtp, CheckOtp, SignUp, SignOut
from .views import CustomLoginView, CustomLogoutView

app_name = 'accounts'

urlpatterns = [
    path('sign/', Sign.as_view(), name='sign'),
    path('sign-in/', SignIn.as_view(), name='sign_in'),
    path('send-otp/', SendOtp.as_view(), name='send_otp'),
    path('check-otp/', CheckOtp.as_view(), name='check_otp'),
    path('sign-up/', SignUp.as_view(), name='sign_up'),
    path('sign-out/', SignOut.as_view(), name='sign_out'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
]
