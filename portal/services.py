import secrets
from datetime import timedelta

from django.utils import timezone

from .models import Investment, Notification, Payout, Plan, User
from .site import get_int
from .utils import add_months, jalali_year, schedule


def notify(user, title, body='', url='', level=Notification.Level.INFO):
    return Notification.objects.create(user=user, title=title, body=body, url=url, level=level)


def notify_staff(title, body='', url='', level=Notification.Level.WARN):
    staff = User.objects.filter(role__in=[User.Role.ADMIN, User.Role.OPERATOR], status=User.Status.ACTIVE)
    for user in staff:
        notify(user, title, body, url, level)


def next_contract_no():
    year = jalali_year()
    prefix = f'KT-{year}-'
    count = Investment.objects.filter(contract_no__startswith=prefix).count() + 1
    return f'{prefix}{count:04d}'


def next_track_code():
    return 'REQ-' + secrets.token_hex(3).upper()


def create_investment(user, plan, amount, note=''):
    calc = schedule(amount, plan.duration_months, plan.monthly_rate, plan.return_principal)
    investment = Investment.objects.create(
        contract_no=next_contract_no(),
        user=user,
        plan=plan,
        amount=amount,
        months=plan.duration_months,
        monthly_rate=plan.monthly_rate,
        payout_mode=plan.payout_mode,
        return_principal=plan.return_principal,
        monthly_profit=calc['monthly_profit'],
        total_profit=calc['total_profit'],
        total_return=calc['total_return'],
        status=Investment.Status.PENDING,
        request_date=timezone.localdate(),
        investor_note=note,
    )
    notify(
        user,
        'درخواست مشارکت ثبت شد',
        f'قرارداد {investment.contract_no} در انتظار بررسی کارشناس است.',
        f'/panel/investments/{investment.id}/',
    )
    notify_staff(
        'درخواست مشارکت جدید',
        f'{user.full_name} — {investment.contract_no}',
        f'/manage/investments/{investment.id}/',
    )
    return investment


def approve_investment(investment):
    days = get_int('default_funding_days', 7)
    investment.status = Investment.Status.APPROVED
    investment.deposit_deadline = timezone.localdate() + timedelta(days=days)
    investment.save(update_fields=['status', 'deposit_deadline', 'updated_at'])
    notify(
        investment.user,
        'مشارکت شما تأیید شد',
        f'مهلت واریز قرارداد {investment.contract_no} اعلام شد.',
        f'/panel/investments/{investment.id}/',
        Notification.Level.OK,
    )


def reject_investment(investment, reason):
    investment.status = Investment.Status.REJECTED
    investment.reject_reason = reason
    investment.save(update_fields=['status', 'reject_reason', 'updated_at'])
    notify(
        investment.user,
        'درخواست مشارکت رد شد',
        reason or investment.contract_no,
        f'/panel/investments/{investment.id}/',
        Notification.Level.WARN,
    )


def build_payouts(investment):
    investment.payouts.all().delete()
    if investment.payout_mode == Plan.PayoutMode.MONTHLY:
        last = investment.start_date
        for index in range(1, investment.months + 1):
            last = add_months(investment.start_date, index)
            Payout.objects.create(
                investment=investment, user=investment.user, plan=investment.plan,
                kind=Payout.Kind.PROFIT, due_date=last, amount=investment.monthly_profit,
            )
        if investment.return_principal:
            Payout.objects.create(
                investment=investment, user=investment.user, plan=investment.plan,
                kind=Payout.Kind.PRINCIPAL, due_date=last, amount=investment.amount,
            )
        investment.maturity_date = last
    else:
        due = investment.maturity_date or add_months(investment.start_date, investment.months)
        investment.maturity_date = due
        if investment.total_profit:
            Payout.objects.create(
                investment=investment, user=investment.user, plan=investment.plan,
                kind=Payout.Kind.PROFIT, due_date=due, amount=investment.total_profit,
            )
        if investment.return_principal:
            Payout.objects.create(
                investment=investment, user=investment.user, plan=investment.plan,
                kind=Payout.Kind.PRINCIPAL, due_date=due, amount=investment.amount,
            )
    investment.save(update_fields=['maturity_date', 'updated_at'])


def activate_investment(investment):
    if investment.status == Investment.Status.ACTIVE:
        return
    today = timezone.localdate()
    investment.status = Investment.Status.ACTIVE
    investment.start_date = today
    investment.maturity_date = add_months(today, investment.months)
    investment.received_amount = investment.amount
    investment.save()
    build_payouts(investment)
    plan = investment.plan
    plan.raised_amount += investment.amount
    plan.investors_count += 1
    plan.save(update_fields=['raised_amount', 'investors_count', 'updated_at'])
    notify(
        investment.user,
        'قرارداد فعال شد',
        f'تقویم سود {investment.contract_no} ساخته شد.',
        f'/panel/investments/{investment.id}/',
        Notification.Level.OK,
    )


def sync_paid_totals(investment):
    profit = 0
    principal = 0
    for payout in investment.payouts.all():
        if payout.kind == Payout.Kind.PROFIT:
            profit += payout.paid_amount
        else:
            principal += payout.paid_amount
    investment.paid_profit = profit
    investment.paid_principal = principal
    investment.save(update_fields=['paid_profit', 'paid_principal', 'updated_at'])


def mark_payout_paid(payout):
    payout.paid_amount = payout.amount
    payout.status = Payout.Status.PAID
    payout.confirm_status = Payout.Confirm.AWAITING
    payout.save()
    sync_paid_totals(payout.investment)
    notify(
        payout.user,
        'واریز ثبت شد',
        f'{payout.get_kind_display()} قرارداد {payout.investment.contract_no} منتظر تأیید شماست.',
        '/panel/calendar/',
        Notification.Level.WARN,
    )


def confirm_payout(payout, user):
    if payout.user_id != user.id or payout.confirm_status != Payout.Confirm.AWAITING:
        return
    payout.confirm_status = Payout.Confirm.CONFIRMED
    payout.save(update_fields=['confirm_status'])
    investment = payout.investment
    pending = investment.payouts.exclude(confirm_status=Payout.Confirm.CONFIRMED).exists()
    unpaid = investment.payouts.exclude(status=Payout.Status.PAID).exists()
    if not pending and not unpaid:
        investment.status = Investment.Status.SETTLED
        investment.settled_at = timezone.now()
        investment.save(update_fields=['status', 'settled_at', 'updated_at'])
