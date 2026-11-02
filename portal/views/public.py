from datetime import date

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from portal.forms import InvestForm, LeadForm
from portal.models import Faq, Lead, Page, Plan
from portal.services import create_investment, next_track_code
from portal.site import details_visible, get, get_bool, get_int, plans_visible
from portal.utils import accrual_rows, schedule


def _published(user):
    qs = Plan.objects.all()
    if not (user.is_authenticated and getattr(user, 'is_staff_role', False)):
        qs = qs.exclude(status=Plan.Status.DRAFT)
    return qs


def _save_lead(form):
    data = form.cleaned_data
    plan = Plan.objects.filter(pk=data.get('plan_id') or 0).first()
    return Lead.objects.create(
        track_code=next_track_code(),
        full_name=data['full_name'],
        mobile=data['mobile'],
        city=data.get('city') or '',
        amount=data.get('amount'),
        plan=plan,
        call_time=data.get('call_time') or '',
        message=data.get('message') or '',
    )


def home(request):
    lead_code = None
    form = LeadForm(request.POST or None)
    if request.method == 'POST' and request.POST.get('form') == 'lead':
        if form.is_valid():
            lead = _save_lead(form)
            lead_code = lead.track_code
            messages.success(request, f'درخواست شما ثبت شد. کد پیگیری: {lead_code}')
            form = LeadForm()
    rate = get_int('default_monthly_rate', 6)
    months = get_int('default_months', 6)
    demo = schedule(1_000_000_000, months, rate / 100)
    return render(request, 'public/home.html', {
        'plans': _published(request.user)[:6],
        'faqs': Faq.objects.filter(is_active=True)[:6],
        'form': form,
        'lead_code': lead_code,
        'rate': rate,
        'months': months,
        'demo': demo,
        'demo_rows': accrual_rows(date.today(), months, demo['monthly_profit']),
        'demo_end': accrual_rows(date.today(), months, demo['monthly_profit'])[-1]['date'] if months else None,
        'show_details': details_visible(request.user),
        'show_plans': plans_visible(request.user),
    })


def plans(request):
    if not plans_visible(request.user):
        messages.info(request, 'برای مشاهده فرصت‌ها وارد حساب کاربری شوید.')
        return redirect('login')
    status = request.GET.get('status', '')
    qs = _published(request.user)
    if status:
        qs = qs.filter(status=status)
    return render(request, 'public/plans.html', {
        'plans': qs,
        'status': status,
        'show_details': details_visible(request.user),
    })


def plan_detail(request, slug):
    plan = get_object_or_404(Plan, slug=slug)
    if plan.status == Plan.Status.DRAFT and not (request.user.is_authenticated and request.user.is_staff_role):
        return page_not_found(request, None)
    if not details_visible(request.user):
        return render(request, 'public/plan_locked.html', {'plan': plan})
    calc = schedule(max(plan.min_investment, 1), plan.duration_months, plan.monthly_rate, plan.return_principal)
    rows = accrual_rows(date.today(), plan.duration_months, calc['monthly_profit'])
    form = None
    if request.user.is_authenticated and request.user.role == 'investor' and plan.accepts_investment:
        form = InvestForm(plan, request.POST or None)
        if request.method == 'POST' and form.is_valid():
            investment = create_investment(request.user, plan, form.cleaned_data['amount'], form.cleaned_data.get('note') or '')
            messages.success(request, f'درخواست {investment.contract_no} ثبت شد.')
            return redirect('panel_investment', pk=investment.pk)
    return render(request, 'public/plan.html', {
        'plan': plan,
        'calc': calc,
        'rows': rows,
        'form': form,
        'maturity': rows[-1]['date'] if rows else None,
    })


def how(request):
    rate = get_int('default_monthly_rate', 6)
    months = get_int('default_months', 6)
    demo = schedule(1_000_000_000, months, rate / 100)
    rows = accrual_rows(date.today(), months, demo['monthly_profit'])
    return render(request, 'public/how.html', {
        'rate': rate, 'months': months, 'demo': demo, 'rows': rows,
        'maturity': rows[-1]['date'] if rows else None,
    })


def about(request):
    page = Page.objects.filter(slug='about', is_active=True).first()
    return render(request, 'public/page.html', {'page': page, 'title': 'درباره ما'})


def faq(request):
    return render(request, 'public/faq.html', {'faqs': Faq.objects.filter(is_active=True)})


def contact(request):
    form = LeadForm(request.POST or None)
    lead_code = None
    if request.method == 'POST' and form.is_valid():
        lead = _save_lead(form)
        lead_code = lead.track_code
        messages.success(request, f'پیام شما ثبت شد. کد پیگیری: {lead_code}')
        form = LeadForm()
    page = Page.objects.filter(slug='contact', is_active=True).first()
    return render(request, 'public/contact.html', {'form': form, 'page': page, 'lead_code': lead_code})


def static_page(request, slug):
    page = get_object_or_404(Page, slug=slug, is_active=True)
    return render(request, 'public/page.html', {'page': page, 'title': page.title})


def page_not_found(request, exception):
    return render(request, 'public/404.html', status=404)
