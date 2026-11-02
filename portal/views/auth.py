from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from portal.forms import ForgotForm, LoginForm, RegisterForm, ResetForm
from portal.models import User
from portal.services import notify
from portal.site import get_bool

signer = TimestampSigner(salt='keshttamin-reset')


def _home_for(user):
    return 'staff' if user.is_staff_role else 'panel'


def login_view(request):
    if request.user.is_authenticated and request.user.status == User.Status.ACTIVE:
        return redirect(_home_for(request.user))
    form = LoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        identity = form.cleaned_data['identity'].strip()
        user = User.objects.filter(mobile=identity).first() or User.objects.filter(username=identity).first()
        authed = authenticate(request, username=user.username, password=form.cleaned_data['password']) if user else None
        if authed is None:
            messages.error(request, 'شماره موبایل یا رمز عبور نادرست است.')
        elif authed.status == User.Status.DISABLED:
            messages.error(request, 'این حساب غیرفعال است.')
        elif authed.status == User.Status.PENDING:
            messages.error(request, 'حساب شما هنوز تأیید نشده است.')
        else:
            login(request, authed)
            messages.success(request, f'خوش آمدید، {authed.full_name}.')
            nxt = request.GET.get('next') or request.POST.get('next')
            if nxt and nxt.startswith('/') and not nxt.startswith('//'):
                return redirect(nxt)
            return redirect(_home_for(authed))
    return render(request, 'auth/login.html', {'form': form})


def register_view(request):
    if not get_bool('allow_registration', True):
        messages.error(request, 'ثبت‌نام در حال حاضر بسته است.')
        return redirect('login')
    if request.user.is_authenticated:
        return redirect(_home_for(request.user))
    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        data = form.cleaned_data
        user = User(
            username=data['mobile'],
            mobile=data['mobile'],
            full_name=data['full_name'],
            city=data.get('city') or '',
            role=User.Role.INVESTOR,
            status=User.Status.ACTIVE,
        )
        user.set_password(data['password'])
        user.save()
        notify(user, 'به کشت‌تامین خوش آمدید', 'از فرصت‌های سرمایه‌گذاری یک طرح را انتخاب کنید.', '/panel/opportunities/')
        login(request, user)
        messages.success(request, 'حساب شما ساخته شد.')
        return redirect('panel')
    return render(request, 'auth/register.html', {'form': form})


def forgot_view(request):
    form = ForgotForm(request.POST or None)
    reset_url = None
    if request.method == 'POST' and form.is_valid():
        user = User.objects.filter(mobile=form.cleaned_data['mobile'], status=User.Status.ACTIVE).first()
        messages.success(request, 'اگر این شماره در سامانه باشد، مسیر بازیابی آماده است.')
        if user:
            token = signer.sign(str(user.pk))
            reset_url = request.build_absolute_uri(f'/reset/{token}/')
        form = ForgotForm()
    return render(request, 'auth/forgot.html', {'form': form, 'reset_url': reset_url})


def reset_view(request, token):
    try:
        user_id = signer.unsign(token, max_age=60 * 60 * 2)
        user = User.objects.get(pk=user_id, status=User.Status.ACTIVE)
    except (BadSignature, SignatureExpired, User.DoesNotExist):
        messages.error(request, 'لینک بازیابی نامعتبر یا منقضی شده است.')
        return redirect('forgot')
    form = ResetForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user.set_password(form.cleaned_data['password'])
        user.save()
        messages.success(request, 'رمز عبور تغییر کرد. اکنون وارد شوید.')
        return redirect('login')
    return render(request, 'auth/reset.html', {'form': form})


@require_POST
def logout_view(request):
    logout(request)
    messages.success(request, 'از حساب خارج شدید.')
    return redirect('home')
