from django.contrib import messages
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from portal.decorators import investor_required
from portal.forms import InvestForm, ProfileForm, ReplyForm, TicketForm
from portal.models import Document, Investment, Notification, Plan, Ticket, TicketMessage
from portal.services import confirm_payout, create_investment
from portal.site import get_bool


@investor_required
def dashboard(request):
    user = request.user
    investments = user.investments.exclude(status__in=['rejected', 'cancelled']).select_related('plan')
    live = investments.filter(status__in=['active', 'matured', 'settled'])
    active_capital = investments.filter(status__in=['active', 'matured']).aggregate(s=Sum('amount'))['s'] or 0
    profit = live.aggregate(s=Sum('total_profit'))['s'] or 0
    paid = live.aggregate(s=Sum('paid_profit'))['s'] or 0
    upcoming = user.payouts.filter(status='scheduled').select_related('plan', 'investment')[:5]
    awaiting = user.payouts.filter(confirm_status='awaiting').select_related('investment')
    return render(request, 'panel/dashboard.html', {
        'investments': investments[:6],
        'contract_count': investments.count(),
        'active_capital': active_capital,
        'profit': profit,
        'paid': paid,
        'upcoming': upcoming,
        'awaiting': awaiting,
        'missing_iban': not user.iban,
        'docs': Document.objects.filter(published_at__isnull=False)[:4],
    })


@investor_required
def opportunities(request):
    plans = Plan.objects.exclude(status=Plan.Status.DRAFT)
    return render(request, 'panel/opportunities.html', {'plans': plans})


@investor_required
def invest(request, slug):
    plan = get_object_or_404(Plan, slug=slug)
    if not plan.accepts_investment:
        messages.error(request, 'این طرح در حال جذب سرمایه نیست.')
        return redirect('panel_opportunities')
    form = InvestForm(plan, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        investment = create_investment(request.user, plan, form.cleaned_data['amount'], form.cleaned_data.get('note') or '')
        messages.success(request, f'درخواست {investment.contract_no} ثبت شد.')
        return redirect('panel_investment', pk=investment.pk)
    return render(request, 'panel/invest.html', {
        'plan': plan,
        'form': form,
        'show_accounts': get_bool('deposit_accounts_enabled', True),
    })


@investor_required
def investments(request):
    qs = request.user.investments.select_related('plan')
    status = request.GET.get('status', '')
    if status:
        qs = qs.filter(status=status)
    return render(request, 'panel/investments.html', {'investments': qs, 'status': status})


@investor_required
def investment_detail(request, pk):
    investment = get_object_or_404(Investment.objects.select_related('plan'), pk=pk, user=request.user)
    return render(request, 'panel/investment.html', {
        'investment': investment,
        'payouts': investment.payouts.all(),
        'show_accounts': get_bool('deposit_accounts_enabled', True),
    })


@investor_required
def calendar(request):
    payouts = request.user.payouts.select_related('plan', 'investment')
    filt = request.GET.get('f', '')
    if filt == 'awaiting':
        payouts = payouts.filter(confirm_status='awaiting')
    elif filt == 'paid':
        payouts = payouts.filter(status='paid')
    return render(request, 'panel/calendar.html', {'payouts': payouts, 'filt': filt})


@investor_required
def confirm(request, pk):
    payout = get_object_or_404(request.user.payouts, pk=pk)
    if request.method == 'POST':
        confirm_payout(payout, request.user)
        messages.success(request, 'دریافت وجه تأیید شد.')
    return redirect('panel_calendar')


@investor_required
def documents(request):
    docs = Document.objects.filter(published_at__isnull=False).select_related('plan')
    return render(request, 'panel/documents.html', {'docs': docs})


@investor_required
def tickets(request):
    form = TicketForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        ticket = Ticket.objects.create(user=request.user, subject=form.cleaned_data['subject'])
        TicketMessage.objects.create(ticket=ticket, author=request.user, body=form.cleaned_data['body'])
        messages.success(request, 'تیکت ثبت شد.')
        return redirect('panel_ticket', pk=ticket.pk)
    return render(request, 'panel/tickets.html', {
        'tickets': request.user.tickets.all(),
        'form': form,
    })


@investor_required
def ticket_detail(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk, user=request.user)
    form = ReplyForm(request.POST or None)
    if request.method == 'POST' and form.is_valid() and ticket.status != Ticket.Status.CLOSED:
        TicketMessage.objects.create(ticket=ticket, author=request.user, body=form.cleaned_data['body'])
        ticket.status = Ticket.Status.USER_REPLY
        ticket.save(update_fields=['status', 'updated_at'])
        messages.success(request, 'پاسخ شما ثبت شد.')
        return redirect('panel_ticket', pk=ticket.pk)
    return render(request, 'panel/ticket.html', {'ticket': ticket, 'form': form})


@investor_required
def notifications(request):
    items = request.user.notifications.all()
    if request.method == 'POST':
        items.filter(read_at__isnull=True).update(read_at=timezone.now())
        messages.success(request, 'همه اعلان‌ها خوانده شد.')
        return redirect('panel_notifications')
    return render(request, 'panel/notifications.html', {'items': items})


@investor_required
def profile(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'پروفایل ذخیره شد.')
        return redirect('panel_profile')
    return render(request, 'panel/profile.html', {'form': form})
