import calendar
import re
from datetime import date

import jdatetime

FA_DIGITS = str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹')
TO_EN = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789')
MONTHS = ['', 'فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور', 'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند']


def fa(value):
    return str(value).translate(FA_DIGITS)


def parse_int(value):
    text = str(value or '').translate(TO_EN)
    digits = re.sub(r'[^\d]', '', text)
    return int(digits) if digits else 0


def money(value):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return '—'
    return fa(f'{number:,}')


def money_short(value):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return '—'
    if number >= 1_000_000_000 and number % 1_000_000_000 == 0:
        return fa(number // 1_000_000_000) + ' میلیارد'
    if number >= 1_000_000 and number % 1_000_000 == 0:
        return fa(number // 1_000_000) + ' میلیون'
    return money(number)


def pct(value, digits=1):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return '—'
    text = f'{number:.{digits}f}'.rstrip('0').rstrip('.')
    return fa(text) + '٪'


def jalali(value):
    if not value:
        return '—'
    if hasattr(value, 'date'):
        value = value.date()
    j = jdatetime.date.fromgregorian(date=value)
    return f'{fa(j.day)} {MONTHS[j.month]} {fa(j.year)}'


def jalali_year(value=None):
    if value is None:
        return jdatetime.date.today().year
    if hasattr(value, 'date'):
        value = value.date()
    return jdatetime.date.fromgregorian(date=value).year


def add_months(start, months):
    month_index = start.month - 1 + months
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    day = min(start.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def schedule(principal, months, monthly_rate, return_principal=True):
    """سود ساده: سود ماهانه یک‌بار گرد می‌شود و در طول دوره ثابت می‌ماند."""
    monthly = int(round(int(principal) * float(monthly_rate)))
    total_profit = monthly * int(months)
    principal_back = int(principal) if return_principal else 0
    return {
        'monthly_profit': monthly,
        'total_profit': total_profit,
        'total_return': principal_back + total_profit,
    }


def accrual_rows(start, months, monthly_profit):
    rows = []
    cumulative = 0
    for index in range(1, months + 1):
        cumulative += monthly_profit
        rows.append({
            'k': index,
            'date': add_months(start, index),
            'amount': monthly_profit,
            'cumulative': cumulative,
        })
    return rows


def norm_mobile(value):
    digits = re.sub(r'[^\d]', '', str(value or '').translate(TO_EN))
    if digits.startswith('98') and len(digits) == 12:
        digits = '0' + digits[2:]
    if digits.startswith('9') and len(digits) == 10:
        digits = '0' + digits
    if re.fullmatch(r'09\d{9}', digits):
        return digits
    return None


def letters_only(value, min_len=2):
    text = str(value or '').strip()
    if len(text) < min_len:
        return False
    return re.fullmatch(r'[\u0600-\u06FF\s\u200cA-Za-z]+', text) is not None
