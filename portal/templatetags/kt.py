from django import template

from portal.utils import fa, jalali, money, money_short, pct

register = template.Library()

TONES = {
    'open': 'ok', 'funded': 'info', 'active': 'info', 'draft': 'muted',
    'completed': 'muted', 'closed': 'muted', 'pending': 'warn', 'approved': 'info',
    'matured': 'accent', 'settled': 'ok', 'rejected': 'danger', 'cancelled': 'muted',
    'low': 'ok', 'medium': 'warn', 'high': 'danger', 'new': 'warn',
    'contacted': 'info', 'answered': 'ok', 'user_reply': 'warn',
    'scheduled': 'muted', 'paid': 'ok', 'awaiting': 'warn', 'confirmed': 'ok',
    'none': 'muted', 'verified': 'ok',
}


@register.filter
def fanum(value):
    return fa(value)


@register.filter
def toman(value):
    return money(value)


@register.filter
def toman_short(value):
    return money_short(value)


@register.filter
def percent(value):
    return pct(value, 1)


@register.filter
def jdate(value):
    return jalali(value)


@register.filter
def tone(value):
    return TONES.get(str(value), 'muted')


@register.simple_tag
def active(request, *names):
    match = getattr(request, 'resolver_match', None)
    if match and match.url_name in names:
        return 'on'
    return ''
