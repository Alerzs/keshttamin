from datetime import datetime
from decimal import Decimal

from django.db import transaction
from django.urls import reverse

from portal.models import Plan
from portal.services import notify_staff
from portal.site import get_int
from portal.utils import add_months, fa, money


class SalePayloadError(Exception):
    pass


def upsert_check_sale(payload):
    if not isinstance(payload, dict):
        raise SalePayloadError('بدنه درخواست ناقص است.')
    if payload.get('source') != 'keshtyar' or payload.get('event') != 'check_sale_approved':
        raise SalePayloadError('رویداد ارسالی شناخته نشد.')

    sale_id = _sale_id(payload.get('sale_request_id'))
    content = _plan_content(payload, sale_id)

    with transaction.atomic():
        plan, created = Plan.objects.get_or_create(
            keshtyar_sale_id=sale_id,
            defaults={
                **content,
                'code': _free_value('code', f'KY-{sale_id}', sale_id),
                'slug': _free_value('slug', f'ky-{sale_id}', sale_id),
                'status': Plan.Status.OPEN,
                'raised_amount': 0,
                'investors_count': 0,
                'is_featured': False,
                'sort_order': 0,
                'return_principal': True,
                'payout_mode': Plan.PayoutMode.LUMP,
            },
        )
        if not created:
            for key, value in content.items():
                setattr(plan, key, value)
            plan.save()
        elif plan.pk:
            notify_staff(
                'پیشنهاد سرمایه‌گذاری تازه از فروش چکی',
                plan.title,
                url=reverse('staff_plan_edit', args=[plan.pk]),
            )
    return plan, created


def _plan_content(payload, sale_id):
    customer = payload.get('customer') if isinstance(payload.get('customer'), dict) else {}
    invoice = payload.get('invoice') if isinstance(payload.get('invoice'), dict) else {}
    credit = customer.get('credit') if isinstance(customer.get('credit'), dict) else {}
    lines = _dicts(payload.get('lines'))
    payments = _dicts(payload.get('payments'))
    checks = _dicts(payload.get('checks'))
    guarantees = _dicts(payload.get('guarantees'))

    products = _product_names(lines)
    product_label = _product_label(products)
    city = _text(customer.get('city'), 120)
    customer_type = _text(customer.get('customer_type'), 40)
    settlement = _text(payload.get('settlement') or invoice.get('settlement'), 40) or 'قسطی'
    sold_jalali = _text(payload.get('sold_on_jalali') or invoice.get('sold_on_jalali'), 20)
    invoice_no = _text(invoice.get('number'), 20)
    note = _text(payload.get('note') or invoice.get('note'), 300)

    target = _target_amount(invoice, payments, checks)
    if target <= 0:
        raise SalePayloadError('مبلغ قابل تأمین در این فروش پیدا نشد.')

    minimum, maximum, step = _participation_bounds(target)
    months = _duration_months(payload.get('sold_on') or invoice.get('sold_on'), checks)
    buyer = _buyer_label(customer_type, city)
    place = f' در {city}' if city else ''

    title = f'طرح فروش {product_label}{place}'
    subtitle_parts = [part for part in (f'فاکتور {invoice_no}' if invoice_no else '', settlement, sold_jalali) if part]
    summary = (
        f'تأمین سرمایه فروش {settlement} {product_label}{place}. '
        f'مبلغ قابل جذب {money(target)} تومان و مدت طرح {fa(months)} ماه است.'
    )
    description = _description(
        settlement, invoice_no, sold_jalali, buyer, lines, invoice, payments, checks, note,
    )
    usage = _usage(product_label, invoice, lines)
    guarantee = _guarantee(guarantees, checks, _texts(payload.get('docs')))
    risk = _risk(_texts(payload.get('warnings')), credit)
    bounced = _bounced(credit)

    return {
        'title': _text(title, 180) or f'طرح فروش چکی {sale_id}',
        'subtitle': _text(' · '.join(subtitle_parts), 255),
        'summary': summary,
        'description': description,
        'usage_of_funds': usage,
        'guarantee_note': guarantee,
        'risk_note': risk,
        'risk_level': Plan.Risk.HIGH if bounced or payload.get('warnings') else Plan.Risk.MEDIUM,
        'target_amount': target,
        'min_investment': minimum,
        'max_investment': maximum,
        'invest_step': step,
        'monthly_rate': _monthly_rate(),
        'duration_months': months,
        'region': city,
        'product_name': _text(product_label, 120) or 'کالا',
        'unit_label': 'عدد',
        'cover_preset': (sale_id % 6) + 1,
    }


def _description(settlement, invoice_no, sold_jalali, buyer, lines, invoice, payments, checks, note):
    paragraphs = []
    intro = f'این طرح برای تأمین سرمایه فروش {settlement}'
    if invoice_no:
        intro += f' فاکتور {invoice_no}'
    if sold_jalali:
        intro += f' در تاریخ {sold_jalali}'
    paragraphs.append(intro + ' ثبت شده است.')
    if buyer:
        paragraphs.append(f'خریدار: {buyer}.')

    item_lines = []
    for line in lines:
        name = _text(line.get('product_name'), 120)
        if not name:
            continue
        qty = _qty(line.get('qty'))
        price = _amount(line.get('unit_price'))
        bits = [name]
        if qty:
            bits.append(f'{qty} عدد')
        if price:
            bits.append(f'هر واحد {money(price)} تومان')
        item_lines.append('، '.join(bits))
    if item_lines:
        paragraphs.append('اقلام:\n' + '\n'.join(item_lines))

    sale_amount = _amount(invoice.get('sale_amount'))
    money_bits = []
    if sale_amount:
        money_bits.append(f'جمع فروش {money(sale_amount)} تومان')
    paid = sum(_amount(row.get('amount')) for row in payments)
    if paid:
        methods = '، '.join(_unique(_text(row.get('method'), 40) for row in payments))
        paid_text = f'پیش‌پرداخت {money(paid)} تومان'
        if methods:
            paid_text += f' از مسیر {methods}'
        money_bits.append(paid_text)
    if money_bits:
        paragraphs.append('. '.join(money_bits) + '.')

    check_total = sum(_amount(row.get('amount')) for row in checks)
    if check_total:
        count = fa(len([row for row in checks if _amount(row.get('amount'))]))
        paragraphs.append(f'مانده مطالبات {money(check_total)} تومان در {count} فقره چک است.')
        for row in checks:
            amount = _amount(row.get('amount'))
            if not amount:
                continue
            bits = [f'مبلغ {money(amount)} تومان']
            bank = _text(row.get('bank'), 40)
            status = _text(row.get('status'), 40)
            due = _text(row.get('due_on_jalali'), 20)
            if bank:
                bits.append(f'بانک {bank}')
            if status:
                bits.append(f'وضعیت {status}')
            if due:
                bits.append(f'سررسید {due}')
            paragraphs.append('، '.join(bits) + '.')

    if note:
        paragraphs.append(f'توضیح فروش: {note}')
    return '\n'.join(paragraphs)


def _usage(product_label, invoice, lines):
    purchase = _amount(invoice.get('purchase_amount')) or _amount(invoice.get('cost_amount'))
    if not purchase:
        purchase = sum(_amount(line.get('unit_cost')) * _qty_number(line.get('qty')) for line in lines)
    if purchase:
        return f'مبلغ {money(purchase)} تومان صرف خرید {product_label} برای همین فروش می‌شود.'
    return f'وجوه این طرح صرف خرید {product_label} و پوشش فاصله وصول مطالبات همین فروش می‌شود.'


def _guarantee(guarantees, checks, docs):
    rows = []
    for row in guarantees:
        kind = _text(row.get('type'), 80)
        amount = _amount(row.get('amount'))
        if not kind and not amount:
            continue
        if kind and amount:
            rows.append(f'{kind} به مبلغ {money(amount)} تومان')
        elif kind:
            rows.append(kind)
        else:
            rows.append(f'تضمین به مبلغ {money(amount)} تومان')
    for row in checks:
        amount = _amount(row.get('amount'))
        if not amount:
            continue
        bits = [f'چک {money(amount)} تومان']
        bank = _text(row.get('bank'), 40)
        status = _text(row.get('status'), 40)
        due = _text(row.get('due_on_jalali'), 20)
        if bank:
            bits.append(f'بانک {bank}')
        if status:
            bits.append(status)
        if due:
            bits.append(f'سررسید {due}')
        rows.append('، '.join(bits))
    if docs:
        rows.append('مدارک ثبت‌شده: ' + '، '.join(docs))
    if not rows:
        return 'پشتوانه طرح، مطالبات همین فروش است.'
    return '\n'.join(rows)


def _risk(warnings, credit):
    text = (
        'وصول این طرح به سررسید چک‌ها وابسته است. '
        'سود اعلام‌شده تعهد قراردادی مجری است و سود بانکی نیست.'
    )
    if _bounced(credit):
        text += ' در اعتبارسنجی خریدار، سابقه چک برگشتی ثبت شده است.'
    if warnings:
        text += '\nهشدارهای بررسی: ' + '؛ '.join(warnings)
    return text


def _target_amount(invoice, payments, checks):
    check_total = sum(_amount(row.get('amount')) for row in checks)
    if check_total:
        return check_total
    sale_amount = _amount(invoice.get('sale_amount'))
    paid = sum(_amount(row.get('amount')) for row in payments)
    if sale_amount > paid:
        return sale_amount - paid
    return sale_amount or _amount(invoice.get('purchase_amount')) or _amount(invoice.get('cost_amount'))


def _participation_bounds(target):
    site_min = max(get_int('min_investment', 100_000_000), 1)
    if target <= site_min:
        return target, target, target
    step = 10_000_000
    if target % step or site_min % step:
        step = 1
    return site_min, target, step


def _duration_months(sold_on, checks):
    start = _date(sold_on)
    dues = [parsed for parsed in (_date(row.get('due_on')) for row in checks) if parsed]
    fallback = min(max(get_int('default_months', 6), 1), 120)
    if not start or not dues:
        return fallback
    end = max(dues)
    if end <= start:
        return 1
    months = 1
    while add_months(start, months) < end and months < 120:
        months += 1
    return months


def _monthly_rate():
    percent = get_int('default_monthly_rate', 6)
    return (Decimal(percent) / Decimal(100)).quantize(Decimal('0.0001'))


def _buyer_label(customer_type, city):
    if customer_type and city:
        return f'{customer_type} در {city}'
    return customer_type or (f'خریدار در {city}' if city else '')


def _product_names(lines):
    names = []
    for line in lines:
        name = _text(line.get('product_name'), 120)
        if name and name not in names:
            names.append(name)
    return names


def _product_label(names):
    if not names:
        return 'کالا'
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f'{names[0]} و {names[1]}'
    return f'{names[0]} و سایر اقلام'


def _bounced(credit):
    text = _text(credit.get('bouncedCheck'), 40)
    if not text or 'ندارد' in text:
        return False
    return 'دارد' in text


def _sale_id(raw):
    if isinstance(raw, bool):
        raise SalePayloadError('شناسه اعلام فروش نامعتبر است.')
    if isinstance(raw, int):
        value = raw
    elif isinstance(raw, float) and raw.is_integer():
        value = int(raw)
    elif isinstance(raw, str) and raw.strip().isdigit():
        value = int(raw.strip())
    else:
        raise SalePayloadError('شناسه اعلام فروش نامعتبر است.')
    if value <= 0 or value > 2_147_483_647:
        raise SalePayloadError('شناسه اعلام فروش نامعتبر است.')
    return value


def _free_value(field, value, sale_id):
    taken = Plan.objects.filter(**{field: value}).exclude(keshtyar_sale_id=sale_id)
    if taken.exists():
        return f'{value}-s'[:30 if field == 'code' else 140]
    return value


def _dicts(value):
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _texts(value):
    if not isinstance(value, list):
        return []
    return [_text(item, 180) for item in value if _text(item, 180)]


def _unique(values):
    result = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result


def _text(value, limit):
    if value is None:
        return ''
    text = ' '.join(str(value).split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + '…'


def _amount(value):
    if isinstance(value, bool) or value is None:
        return 0
    if isinstance(value, int):
        return max(0, value)
    if isinstance(value, float):
        return max(0, int(value))
    digits = ''.join(ch for ch in str(value).translate(_TO_EN) if ch.isdigit())
    return int(digits) if digits else 0


def _qty_number(value):
    if isinstance(value, bool) or value is None:
        return 0
    if isinstance(value, (int, float)):
        return value if value > 0 else 0
    text = str(value).translate(_TO_EN).replace(',', '').strip()
    try:
        number = float(text)
    except ValueError:
        return 0
    return number if number > 0 else 0


def _qty(value):
    number = _qty_number(value)
    if not number:
        return ''
    if float(number).is_integer():
        return fa(int(number))
    return fa(f'{number:g}')


def _date(value):
    if not isinstance(value, str) or len(value) < 10:
        return None
    try:
        return datetime.strptime(value[:10], '%Y-%m-%d').date()
    except ValueError:
        return None


_TO_EN = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789')
