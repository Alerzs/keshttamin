from django import forms
from django.contrib.auth.password_validation import validate_password

from .models import Faq, Investment, Page, Plan, Ticket, User
from .utils import letters_only, norm_mobile, parse_int


class LoginForm(forms.Form):
    identity = forms.CharField(label='شماره موبایل یا نام کاربری')
    password = forms.CharField(label='رمز عبور', widget=forms.PasswordInput)


class RegisterForm(forms.Form):
    full_name = forms.CharField(label='نام و نام خانوادگی', max_length=150)
    mobile = forms.CharField(label='شماره همراه', max_length=15)
    city = forms.CharField(label='شهر', required=False, max_length=60)
    password = forms.CharField(label='رمز عبور', widget=forms.PasswordInput)
    password2 = forms.CharField(label='تکرار رمز عبور', widget=forms.PasswordInput)

    def clean_full_name(self):
        value = self.cleaned_data['full_name'].strip()
        if not letters_only(value, 3):
            raise forms.ValidationError('نام و نام خانوادگی فقط باید حرف باشد.')
        return value

    def clean_mobile(self):
        mobile = norm_mobile(self.cleaned_data['mobile'])
        if not mobile:
            raise forms.ValidationError('شماره موبایل معتبر نیست.')
        if User.objects.filter(mobile=mobile).exists():
            raise forms.ValidationError('این شماره قبلاً ثبت شده است.')
        return mobile

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get('password')
        if password and password != cleaned.get('password2'):
            self.add_error('password2', 'تکرار رمز عبور یکسان نیست.')
        if password:
            validate_password(password)
        return cleaned


class ForgotForm(forms.Form):
    mobile = forms.CharField(label='شماره همراه')

    def clean_mobile(self):
        mobile = norm_mobile(self.cleaned_data['mobile'])
        if not mobile:
            raise forms.ValidationError('شماره موبایل معتبر نیست.')
        return mobile


class ResetForm(forms.Form):
    password = forms.CharField(label='رمز عبور جدید', widget=forms.PasswordInput)
    password2 = forms.CharField(label='تکرار رمز عبور', widget=forms.PasswordInput)

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get('password')
        if password and password != cleaned.get('password2'):
            self.add_error('password2', 'تکرار رمز عبور یکسان نیست.')
        if password:
            validate_password(password)
        return cleaned


class LeadForm(forms.Form):
    full_name = forms.CharField(label='نام و نام خانوادگی', max_length=150)
    mobile = forms.CharField(label='شماره همراه', max_length=15)
    city = forms.CharField(label='شهر', required=False, max_length=80)
    amount = forms.CharField(label='سرمایه تقریبی', required=False)
    plan_id = forms.IntegerField(required=False)
    call_time = forms.CharField(required=False)
    message = forms.CharField(required=False, widget=forms.Textarea, max_length=1000)
    website = forms.CharField(required=False)

    def clean_full_name(self):
        value = self.cleaned_data['full_name'].strip()
        if not letters_only(value, 3):
            raise forms.ValidationError('نام و نام خانوادگی فقط باید حرف باشد.')
        return value

    def clean_mobile(self):
        mobile = norm_mobile(self.cleaned_data['mobile'])
        if not mobile:
            raise forms.ValidationError('شماره موبایل معتبر نیست.')
        return mobile

    def clean_city(self):
        value = self.cleaned_data.get('city', '').strip()
        if value and not letters_only(value, 2):
            raise forms.ValidationError('نام شهر فقط باید حرف باشد.')
        return value

    def clean_amount(self):
        raw = self.cleaned_data.get('amount')
        return parse_int(raw) or None

    def clean_website(self):
        if (self.cleaned_data.get('website') or '').strip():
            raise forms.ValidationError('درخواست نامعتبر است.')
        return ''


class InvestForm(forms.Form):
    amount = forms.CharField(label='مبلغ مشارکت')
    note = forms.CharField(label='توضیح', required=False, widget=forms.Textarea)

    def __init__(self, plan, *args, **kwargs):
        self.plan = plan
        super().__init__(*args, **kwargs)

    def clean_amount(self):
        amount = parse_int(self.cleaned_data['amount'])
        plan = self.plan
        if amount < plan.min_investment:
            raise forms.ValidationError('مبلغ از حداقل ورود این طرح کمتر است.')
        if plan.max_investment and amount > plan.max_investment:
            raise forms.ValidationError('مبلغ از سقف این طرح بیشتر است.')
        if plan.invest_step and amount % plan.invest_step:
            raise forms.ValidationError('مبلغ باید مضرب گام سرمایه‌گذاری باشد.')
        pending = plan.investments.filter(
            status__in=[Investment.Status.PENDING, Investment.Status.APPROVED]
        ).aggregate(total=models_sum())['total'] or 0
        remaining = plan.target_amount - plan.raised_amount - pending
        if plan.target_amount and amount > remaining:
            raise forms.ValidationError('این مبلغ از ظرفیت باقی‌مانده طرح بیشتر است.')
        return amount


def models_sum():
    from django.db.models import Sum
    return Sum('amount')


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            'full_name', 'national_id', 'father_name', 'province', 'city',
            'address', 'postal_code', 'bank_name', 'iban', 'card_number',
            'account_number', 'account_owner',
        ]

    def clean_full_name(self):
        value = self.cleaned_data['full_name'].strip()
        if not letters_only(value, 3):
            raise forms.ValidationError('نام فقط باید حرف باشد.')
        return value

    def clean_iban(self):
        value = (self.cleaned_data.get('iban') or '').replace(' ', '').upper()
        if value and not value.startswith('IR'):
            value = 'IR' + value
        return value


class TicketForm(forms.Form):
    subject = forms.CharField(label='موضوع', max_length=200)
    body = forms.CharField(label='متن', widget=forms.Textarea)


class ReplyForm(forms.Form):
    body = forms.CharField(label='پاسخ', widget=forms.Textarea)


class PlanForm(forms.ModelForm):
    rate_percent = forms.DecimalField(label='سود ماهانه (درصد)', max_digits=5, decimal_places=2, min_value=0)

    class Meta:
        model = Plan
        fields = [
            'title', 'subtitle', 'code', 'summary', 'description', 'usage_of_funds',
            'risk_note', 'guarantee_note', 'status', 'risk_level', 'is_featured',
            'target_amount', 'min_investment', 'max_investment', 'invest_step',
            'duration_months', 'payout_mode', 'region', 'product_name', 'cover_preset',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['code'].required = False
        if self.instance and self.instance.pk:
            self.fields['rate_percent'].initial = round(self.instance.rate_percent, 2)
        else:
            self.fields['rate_percent'].initial = 6

    def save(self, commit=True):
        plan = super().save(commit=False)
        plan.monthly_rate = self.cleaned_data['rate_percent'] / 100
        if commit:
            plan.save()
        return plan


class FaqForm(forms.ModelForm):
    class Meta:
        model = Faq
        fields = ['question', 'answer', 'sort_order', 'is_active']


class PageForm(forms.ModelForm):
    class Meta:
        model = Page
        fields = ['title', 'body', 'is_active']


class SettingsForm(forms.Form):
    site_name = forms.CharField(label='نام سایت')
    site_name_en = forms.CharField(label='نام انگلیسی')
    site_tagline = forms.CharField(label='شعار')
    site_description = forms.CharField(label='توضیح', widget=forms.Textarea)
    support_phone = forms.CharField(label='تلفن', required=False)
    support_email = forms.CharField(label='ایمیل', required=False)
    company_address = forms.CharField(label='نشانی', required=False)
    instagram = forms.CharField(label='اینستاگرام', required=False)
    telegram = forms.CharField(label='تلگرام', required=False)
    currency_label = forms.CharField(label='واحد پول')
    default_monthly_rate = forms.CharField(label='نرخ پیش‌فرض ماهانه')
    default_months = forms.CharField(label='مدت پیش‌فرض')
    min_investment = forms.CharField(label='حداقل سرمایه')
    public_plans_mode = forms.ChoiceField(
        label='نمایش طرح‌ها برای مهمان',
        choices=[('full', 'جزئیات کامل'), ('teaser', 'فقط عنوان و تصویر'), ('hidden', 'پنهان')],
    )
    allow_registration = forms.BooleanField(label='ثبت‌نام آزاد', required=False)
    deposit_accounts_enabled = forms.BooleanField(label='نمایش حساب مقصد', required=False)
    legal_disclaimer = forms.CharField(label='سلب مسئولیت', widget=forms.Textarea)


class RejectForm(forms.Form):
    reason = forms.CharField(label='دلیل رد', widget=forms.Textarea)
