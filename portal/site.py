from .models import Setting

DEFAULTS = {
    'site_name': 'کشت‌تامین',
    'site_name_en': 'KESHT TAMIN',
    'site_tagline': 'سرمایه‌گذاری هوشمند در تأمین نوار تیپ',
    'site_description': 'سامانه تأمین سرمایه گردشی برای خرید و توزیع نوار تیپ آبیاری قطره‌ای، با گزارش‌دهی شفاف و زمان‌بندی دقیق سود.',
    'support_phone': '02191000000',
    'support_email': 'hello@keshttamin.ir',
    'company_address': 'تهران',
    'instagram': '',
    'telegram': '',
    'currency_label': 'تومان',
    'default_monthly_rate': '6',
    'default_months': '6',
    'min_investment': '100000000',
    'default_funding_days': '7',
    'allow_registration': '1',
    'public_plans_mode': 'full',
    'deposit_accounts_enabled': '1',
    'legal_disclaimer': 'سود اعلام‌شده بر پایه قرارداد مشارکت در تأمین سرمایه گردشی محاسبه می‌شود و تعهد پرداخت آن بر عهده مجری طرح است. سرمایه‌گذاری در هر طرح تجاری با ریسک همراه است.',
}


def get(key, default=None):
    fallback = DEFAULTS.get(key, '') if default is None else default
    row = Setting.objects.filter(key=key).first()
    if row is None or row.value is None:
        return str(fallback)
    return row.value


def get_int(key, default=0):
    try:
        return int(get(key, default))
    except (TypeError, ValueError):
        return int(default)


def get_bool(key, default=False):
    return get(key, '1' if default else '0') in ('1', 'true', 'yes', 'on')


def set_value(key, value):
    Setting.objects.update_or_create(key=key, defaults={'value': '' if value is None else str(value)})


def as_dict():
    data = dict(DEFAULTS)
    for row in Setting.objects.all():
        data[row.key] = row.value
    return data


def plans_visible(user):
    if user.is_authenticated and (getattr(user, 'is_staff_role', False) or getattr(user, 'role', '') == 'investor'):
        return True
    return get('public_plans_mode', 'full') != 'hidden'


def details_visible(user):
    if user.is_authenticated and (getattr(user, 'is_staff_role', False) or getattr(user, 'role', '') == 'investor'):
        return True
    return get('public_plans_mode', 'full') == 'full'
