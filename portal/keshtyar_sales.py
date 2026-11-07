from datetime import date, datetime
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.urls import reverse
from django.utils.crypto import get_random_string

from portal.models import Plan
from portal.services import notify_staff
from portal.site import get_int
from portal.utils import add_months, fa, jalali, money


class SalePayloadError(Exception):
    pass


_CODE_ALPHABET = '23456789ABCDEFGHJKLMNPQRSTUVWXYZ'


def create_check_sale(payload):
    """یک فروش چکی را به طرح سرمایه‌گذاری تبدیل می‌کند.

    بدنه فقط حجم معامله، تعداد چک و سررسیدهاست و شناسه تکرار ندارد،
    پس هر ارسالِ پذیرفته‌شده یک طرح تازه می‌سازد.
    """
    amount, count, dues = _sale_fields(payload)
    content = _plan_content(amount, count, dues)
    for _ in range(5):
        code, slug = _fresh_label()
        try:
            with transaction.atomic():
                plan = Plan.objects.create(
                    code=code,
                    slug=slug,
                    status=Plan.Status.OPEN,
                    raised_amount=0,
                    investors_count=0,
                    is_featured=False,
                    sort_order=0,
                    return_principal=True,
                    payout_mode=Plan.PayoutMode.LUMP,
                    **content,
                )
        except IntegrityError:
            continue
        notify_staff(
            'پیشنهاد سرمایه‌گذاری تازه از فروش چکی',
            plan.title,
            url=reverse('staff_plan_edit', args=[plan.pk]),
        )
        return plan
    raise SalePayloadError('ثبت طرح ممکن نشد.')


def _sale_fields(payload):
    if not isinstance(payload, dict):
        raise SalePayloadError('بدنه درخواست ناقص است.')
    amount = _positive_int(payload.get('sale_amount'), 'حجم معامله', 10**15)
    count = _positive_int(payload.get('check_count'), 'تعداد چک‌ها', 120)
    dues = payload.get('check_due_dates')
    if not isinstance(dues, list) or len(dues) != count:
        raise SalePayloadError('تعداد سررسیدها با تعداد چک‌ها یکی نیست.')
    parsed = []
    for item in dues:
        day = _date(item)
        if day is None:
            raise SalePayloadError('سررسید چک‌ها نامعتبر است.')
        parsed.append(day)
    return amount, count, parsed


def _plan_content(amount, count, dues):
    ordered = sorted(dues)
    latest = ordered[-1]
    months = _duration_months(latest)
    minimum, maximum, step = _participation_bounds(amount)
    count_label = f'{fa(count)} فقره چک'
    due_lines = [jalali(day) for day in ordered]
    if count == 1:
        subtitle = f'{count_label} · سررسید {due_lines[0]}'
    else:
        subtitle = f'{count_label} · تا {due_lines[-1]}'
    return {
        'title': 'طرح فروش چکی',
        'subtitle': subtitle,
        'summary': (
            f'تأمین سرمایه فروش چکی به مبلغ {money(amount)} تومان. '
            f'مطالبات در {count_label} است و مدت طرح {fa(months)} ماه.'
        ),
        'description': (
            f'این طرح برای تأمین سرمایه یک فروش چکی به مبلغ {money(amount)} تومان ثبت شده است.\n'
            f'تعداد چک‌ها: {count_label}.\n'
            'سررسیدها:\n' + '\n'.join(due_lines)
        ),
        'usage_of_funds': 'وجوه این طرح صرف پوشش فاصله وصول مطالبات همین فروش چکی می‌شود.',
        'guarantee_note': f'پشتوانه طرح، {count_label} با سررسید {"، ".join(due_lines)} است.',
        'risk_note': (
            'وصول این طرح به سررسید چک‌ها وابسته است. '
            'سود اعلام‌شده تعهد قراردادی مجری است و سود بانکی نیست.'
        ),
        'risk_level': Plan.Risk.MEDIUM,
        'target_amount': amount,
        'min_investment': minimum,
        'max_investment': maximum,
        'invest_step': step,
        'monthly_rate': _monthly_rate(),
        'duration_months': months,
        'region': '',
        'product_name': 'فروش چکی',
        'unit_label': 'فقره',
        'cover_preset': (latest.toordinal() % 6) + 1,
    }


def _duration_months(end, today=None):
    start = today or date.today()
    if end <= start:
        return 1
    months = 1
    while add_months(start, months) < end and months < 120:
        months += 1
    return months


def _participation_bounds(target):
    site_min = max(get_int('min_investment', 100_000_000), 1)
    if target <= site_min:
        return target, target, target
    step = 10_000_000
    if target % step or site_min % step:
        step = 1
    return site_min, target, step


def _monthly_rate():
    percent = get_int('default_monthly_rate', 6)
    return (Decimal(percent) / Decimal(100)).quantize(Decimal('0.0001'))


def _fresh_label():
    token = get_random_string(6, _CODE_ALPHABET)
    return f'KY-{token}', f'ky-{token.lower()}'


def _positive_int(value, label, limit):
    if isinstance(value, bool) or not isinstance(value, int):
        raise SalePayloadError(f'{label} نامعتبر است.')
    if value <= 0 or value > limit:
        raise SalePayloadError(f'{label} نامعتبر است.')
    return value


def _date(value):
    if not isinstance(value, str) or len(value) != 10:
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        return None
