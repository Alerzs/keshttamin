from django.contrib import messages
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.text import slugify

from portal.decorators import admin_required, staff_required
from portal.forms import FaqForm, PageForm, PlanForm, RejectForm, ReplyForm, SettingsForm
from portal.models import Document, Faq, Investment, Lead, Page, Payout, Plan, Ticket, TicketMessage, User
from portal.services import activate_investment, approve_investment, mark_payout_paid, reject_investment
from portal.site import DEFAULTS, as_dict, set_value
from portal.utils import jalali_year


@staff_required
def dashboard(request):
    capital = Investment.objects.filter(status__in=['active', 'matured', 'settled']).aggregate(s=Sum('amount'))['s'] or 0
    return render(request, 'staff/dashboard.html', {
        'plans': Plan.objects.exclude(status='draft').count(),
        'capital': capital,
        'pending': Investment.objects.filter(status='pending').select_related('user', 'plan')[:8],
        'leads': Lead.objects.filter(status='new')[:6],
        'open_plans': Plan.objects.filter(status='open')[:4],
    })


@staff_required
def plans(request):
    return render(request, 'staff/plans.html', {'plans': Plan.objects.all()})


@staff_required
def plan_edit(request, pk=None):
    plan = get_object_or_404(Plan, pk=pk) if pk else None
    form = PlanForm(request.POST or None, instance=plan)
    if request.method == 'POST' and form.is_valid():
        obj = form.save(commit=False)
        if not obj.slug:
            obj.slug = slugify(obj.title, allow_unicode=True) or f'plan-{jalali_year()}'
        base = obj.slug
        i = 2
        while Plan.objects.filter(slug=obj.slug).exclude(pk=obj.pk).exists():
            obj.slug = f'{base}-{i}'
            i += 1
        if not obj.code:
            obj.code = f'NT-{jalali_year()}-{(Plan.objects.count() + 1):02d}'
        obj.save()
        messages.success(request, 'طرح ذخیره شد.')
        return redirect('staff_plan_edit', pk=obj.pk)
    return render(request, 'staff/plan_form.html', {'form': form, 'plan': plan})


@staff_required
def investments(request):
    qs = Investment.objects.select_related('user', 'plan')
    status = request.GET.get('status', '')
    q = request.GET.get('q', '').strip()
    if status:
        qs = qs.filter(status=status)
    if q:
        qs = qs.filter(Q(contract_no__icontains=q) | Q(user__full_name__icontains=q) | Q(user__mobile__icontains=q))
    return render(request, 'staff/investments.html', {'investments': qs, 'status': status, 'q': q})


@staff_required
def investment_detail(request, pk):
    investment = get_object_or_404(Investment.objects.select_related('user', 'plan'), pk=pk)
    form = RejectForm()
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'approve' and investment.status == Investment.Status.PENDING:
            approve_investment(investment)
            messages.success(request, 'درخواست تأیید شد.')
        elif action == 'activate' and investment.status == Investment.Status.APPROVED:
            activate_investment(investment)
            messages.success(request, 'قرارداد فعال و تقویم سود ساخته شد.')
        elif action == 'reject' and investment.status in (Investment.Status.PENDING, Investment.Status.APPROVED):
            form = RejectForm(request.POST)
            if form.is_valid():
                reject_investment(investment, form.cleaned_data['reason'])
                messages.success(request, 'درخواست رد شد.')
        return redirect('staff_investment', pk=investment.pk)
    return render(request, 'staff/investment.html', {
        'investment': investment,
        'payouts': investment.payouts.all(),
        'form': form,
    })


@staff_required
def payouts(request):
    rows = Payout.objects.select_related('user', 'plan', 'investment')
    if request.GET.get('f') == 'due':
        rows = rows.filter(status='scheduled', due_date__lte=timezone.localdate())
    return render(request, 'staff/payouts.html', {'payouts': rows[:200]})


@staff_required
def payout_paid(request, pk):
    payout = get_object_or_404(Payout, pk=pk)
    if request.method == 'POST' and payout.status != Payout.Status.PAID:
        mark_payout_paid(payout)
        messages.success(request, 'واریز ثبت شد و منتظر تأیید سرمایه‌گذار ماند.')
    return redirect('staff_payouts')


@staff_required
def investors(request):
    q = request.GET.get('q', '').strip()
    qs = User.objects.filter(role=User.Role.INVESTOR)
    if q:
        qs = qs.filter(Q(full_name__icontains=q) | Q(mobile__icontains=q) | Q(national_id__icontains=q))
    return render(request, 'staff/investors.html', {'investors': qs, 'q': q})


@staff_required
def leads(request):
    if request.method == 'POST':
        lead = get_object_or_404(Lead, pk=request.POST.get('id'))
        lead.status = request.POST.get('status', lead.status)
        if lead.status in dict(Lead.Status.choices):
            lead.save(update_fields=['status'])
            messages.success(request, 'وضعیت درخواست به‌روز شد.')
        return redirect('staff_leads')
    return render(request, 'staff/leads.html', {'leads': Lead.objects.select_related('plan')})


@staff_required
def tickets(request):
    return render(request, 'staff/tickets.html', {'tickets': Ticket.objects.select_related('user')})


@staff_required
def ticket_detail(request, pk):
    ticket = get_object_or_404(Ticket.objects.select_related('user'), pk=pk)
    form = ReplyForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        TicketMessage.objects.create(ticket=ticket, author=request.user, body=form.cleaned_data['body'])
        ticket.status = Ticket.Status.ANSWERED
        ticket.save(update_fields=['status', 'updated_at'])
        messages.success(request, 'پاسخ ثبت شد.')
        return redirect('staff_ticket', pk=ticket.pk)
    return render(request, 'staff/ticket.html', {'ticket': ticket, 'form': form})


@staff_required
def content(request):
    tab = request.GET.get('t', 'faq')
    return render(request, 'staff/content.html', {
        'tab': tab,
        'faqs': Faq.objects.all(),
        'pages': Page.objects.all(),
        'docs': Document.objects.all(),
    })


@staff_required
def faq_edit(request, pk=None):
    faq = get_object_or_404(Faq, pk=pk) if pk else None
    form = FaqForm(request.POST or None, instance=faq)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'پرسش ذخیره شد.')
        return redirect('staff_content')
    return render(request, 'staff/faq_form.html', {'form': form, 'faq': faq})


@staff_required
def page_edit(request, pk):
    page = get_object_or_404(Page, pk=pk)
    form = PageForm(request.POST or None, instance=page)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'صفحه ذخیره شد.')
        return redirect('staff_content')
    return render(request, 'staff/page_form.html', {'form': form, 'page': page})


@admin_required
def settings_view(request):
    current = as_dict()
    if request.method == 'POST':
        form = SettingsForm(request.POST)
        if form.is_valid():
            for key, value in form.cleaned_data.items():
                if isinstance(value, bool):
                    value = '1' if value else '0'
                set_value(key, value)
            messages.success(request, 'تنظیمات ذخیره شد.')
            return redirect('staff_settings')
    else:
        initial = {key: current.get(key, DEFAULTS.get(key, '')) for key in SettingsForm.base_fields}
        initial['allow_registration'] = current.get('allow_registration') == '1'
        initial['deposit_accounts_enabled'] = current.get('deposit_accounts_enabled') == '1'
        form = SettingsForm(initial=initial)
    return render(request, 'staff/settings.html', {'form': form})
