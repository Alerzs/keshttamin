import os

from django.core.management.base import BaseCommand

from portal.models import User


class Command(BaseCommand):
    help = 'اگر DJANGO_SUPERUSER_USERNAME تازه باشد، یک مدیر ارشد می‌سازد.'

    def handle(self, *args, **options):
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME', '').strip()
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', '')
        mobile = os.environ.get('DJANGO_SUPERUSER_MOBILE', '').strip()
        if not username or not password:
            self.stdout.write('DJANGO_SUPERUSER_USERNAME is unset; skipping.')
            return
        if not mobile:
            self.stdout.write('DJANGO_SUPERUSER_MOBILE is unset; skipping.')
            return
        if User.objects.filter(username=username).exists() or User.objects.filter(mobile=mobile).exists():
            self.stdout.write(f'{username} already exists; password and role left unchanged.')
            return
        user = User(
            username=username,
            mobile=mobile,
            email=os.environ.get('DJANGO_SUPERUSER_EMAIL', ''),
            full_name=os.environ.get('DJANGO_SUPERUSER_NAME', 'مدیر کشت‌تامین'),
            role=User.Role.ADMIN,
            status=User.Status.ACTIVE,
        )
        user.set_password(password)
        user.save()
        self.stdout.write(self.style.SUCCESS(f'Created admin {username}.'))
