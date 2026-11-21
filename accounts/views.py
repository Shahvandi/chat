from .models import User, Otp
from django.views.generic import View, TemplateView
from django.shortcuts import render, redirect, reverse
from django.contrib import messages
from random import randint
from django.utils.crypto import get_random_string
from django.contrib.auth import authenticate, login, logout


class Sign(View):
    def get(self, *args, **kwargs):
        if self.request.user.is_authenticated:
            messages.warning(self.request, f'{self.request.user} signed in!')
            return redirect('chats:home')
        return render(self.request, 'home/sign.html')


class SignIn(View):
    def post(self, *args, **kwargs):
        if self.request.user.is_authenticated:
            return redirect('chats:home')
        username = self.request.POST.get('signInUser')
        password = self.request.POST.get('signInPassword')
        try:
            user = User.objects.get(email=username)
        except User.DoesNotExist:
            try:
                user = User.objects.get(mobile=username)
            except User.DoesNotExist:
                messages.warning(self.request, 'User do\'es not exist! SignUp please.')
                return redirect(f'{reverse("accounts:sign")}?mobile={username}&sign_up=True')
        try:
            user = authenticate(username=user.email, password=password)
            login(self.request, user)
            print(f'User {user} login.')
            messages.success(self.request, f'Wellcome {user.fullname}!')
            return redirect('chats:home')
        except:
            messages.warning(self.request, 'Login Error!')
            return redirect(f'{reverse("accounts:sign")}?username={username}')


class SendOtp(View):
    def post(self, *args, **kwargs):
        if self.request.user.is_authenticated:
            return redirect('chats:home')
        mobile = self.request.POST.get('mobile')
        Otp.objects.filter(mobile=mobile).delete()
        code = randint(100000, 999999)
        token = get_random_string(length=64)
        Otp.objects.create(token=token, mobile=mobile, code=code)
        print(mobile, code, token[:20])          # todo: sms or email
        messages.success(self.request, f'Code sent to {mobile}')
        return redirect(f'{reverse("accounts:check_otp")}?token={token}')


class CheckOtp(TemplateView):
    template_name = 'home/check_otp.html'

    def post(self, *args, **kwargs):
        code = self.request.POST.get('code')
        token = self.request.GET.get('token')
        print(token)
        try:
            otp = Otp.objects.get(token=token, code=code)
            user = User.objects.get(mobile=otp.mobile)
            login(self.request, user)
            print(f'User {user} login.')
            messages.success(self.request, f'Wellcome {user.fullname}!')
            return redirect('chats:home')
        except Otp.DoesNotExist:
            messages.warning(self.request, 'Code Error! Try again.')
            return redirect(f'{reverse("accounts:sign")}?sign_in=True')
        except User.DoesNotExist:
            messages.warning(self.request, 'User ERROR! Sign Up please.')
            return redirect(f'{reverse("accounts:sign")}?mobile={otp.mobile}&sign_up=True')
        except:
            messages.warning(self.request, 'Code ERROR! Try again!')
            return redirect(f'{reverse("accounts:sign")}')


class SignUp(View):
    def post(self, *args, **kwargs):
        if self.request.user.is_authenticated:
            return redirect('chats:home')
        first_name = self.request.POST.get('signUpName')
        last_name = self.request.POST.get('signUpFamily')
        mobile = self.request.POST.get('signUpMobile')
        email = self.request.POST.get('signUpEmail')
        password = self.request.POST.get('signUpPassword')
        password_confirm = self.request.POST.get('signUpPasswordConfirm')
        print(first_name, last_name, mobile, email, password)
        if password != password_confirm:
            messages.warning(self.request, 'Passwords do not match!')
            return redirect(f'{reverse("accounts:sign")}?name={first_name}&family={last_name}&mobile={mobile}&email={email}&sign_up=True')
        try:
            user = (User.objects.create_user(mobile=mobile, email=email, first_name=first_name, last_name=last_name, password=password))
            print(f'{user} signed up.')
            messages.success(self.request, f'You signed up successfully: {user.first_name} {user.last_name}! Sign in please.')
            return redirect(f'{reverse("accounts:sign")}?username={email}')
        except:
            print('creation error')
            messages.warning(self.request, 'Error!')
        return redirect(f'{reverse("accounts:sign")}?name={first_name}&family={last_name}&mobile={mobile}&email={email}&sign_up=True')


class SignOut(View):
    def get(self, *args, **kwargs):
        print(f'Logout {self.request.user}')
        if self.request.user.is_authenticated:
            messages.success(self.request, 'Logout Successfully!')
        else:
            messages.success(self.request, 'Any User is not Signed in!')
        logout(self.request)
        return redirect('chats:home')

