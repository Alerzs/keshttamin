from django.contrib.auth.models import AbstractUser
from django.db import models
from django.templatetags.static import static


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'admin', 'مدیر ارشد'
        OPERATOR = 'operator', 'کارشناس'
        INVESTOR = 'investor', 'سرمایه‌گذار'

    class Status(models.TextChoices):
        ACTIVE = 'active', 'فعال'
        PENDING = 'pending', 'در انتظار تأیید'
        DISABLED = 'disabled', 'غیرفعال'

    class Kyc(models.TextChoices):
        NONE = 'none', 'ثبت نشده'
        PENDING = 'pending', 'در انتظار بررسی'
        VERIFIED = 'verified', 'تأیید شده'
        REJECTED = 'rejected', 'رد شده'

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.INVESTOR)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    mobile = models.CharField('موبایل', max_length=15, unique=True)
    full_name = models.CharField('نام و نام خانوادگی', max_length=150)
    national_id = models.CharField('کد ملی', max_length=10, blank=True)
    father_name = models.CharField('نام پدر', max_length=100, blank=True)
    province = models.CharField('استان', max_length=60, blank=True)
    city = models.CharField('شهر', max_length=60, blank=True)
    address = models.CharField('نشانی', max_length=500, blank=True)
    postal_code = models.CharField('کد پستی', max_length=10, blank=True)
    bank_name = models.CharField('بانک', max_length=80, blank=True)
    iban = models.CharField('شبا', max_length=30, blank=True)
    card_number = models.CharField('شماره کارت', max_length=20, blank=True)
    account_number = models.CharField('شماره حساب', max_length=40, blank=True)
    account_owner = models.CharField('صاحب حساب', max_length=150, blank=True)
    kyc_status = models.CharField(max_length=20, choices=Kyc.choices, default=Kyc.NONE)
    avatar = models.ImageField(upload_to='avatars/', blank=True)

    class Meta:
        verbose_name = 'کاربر'
        verbose_name_plural = 'کاربران'

    def save(self, *args, **kwargs):
        if self.full_name:
            self.first_name = self.full_name[:150]
        if not self.username:
            self.username = self.mobile
        self.is_staff = self.role in (self.Role.ADMIN, self.Role.OPERATOR)
        self.is_superuser = self.role == self.Role.ADMIN
        super().save(*args, **kwargs)

    def __str__(self):
        return self.full_name or self.mobile

    @property
    def is_staff_role(self):
        return self.role in (self.Role.ADMIN, self.Role.OPERATOR)

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN

    @property
    def role_label(self):
        return self.get_role_display()

    @property
    def initial(self):
        return (self.full_name or 'ک')[:1]


class Setting(models.Model):
    key = models.CharField(max_length=100, primary_key=True)
    value = models.TextField(blank=True, default='')

    def __str__(self):
        return self.key


class Plan(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'پیش‌نویس'
        OPEN = 'open', 'در حال جذب'
        FUNDED = 'funded', 'تأمین شد'
        ACTIVE = 'active', 'در حال اجرا'
        COMPLETED = 'completed', 'پایان‌یافته'
        CLOSED = 'closed', 'بسته'

    class Risk(models.TextChoices):
        LOW = 'low', 'ریسک کم'
        MEDIUM = 'medium', 'ریسک متوسط'
        HIGH = 'high', 'ریسک بالا'

    class PayoutMode(models.TextChoices):
        LUMP = 'lump', 'یکجا در پایان دوره'
        MONTHLY = 'monthly', 'سود ماهانه'
        MATURITY = 'maturity', 'در سررسید'

    code = models.CharField(max_length=30, unique=True)
    slug = models.SlugField(max_length=140, unique=True, allow_unicode=True)
    title = models.CharField(max_length=180)
    subtitle = models.CharField(max_length=255, blank=True)
    summary = models.TextField(blank=True)
    description = models.TextField(blank=True)
    usage_of_funds = models.TextField(blank=True)
    risk_note = models.TextField(blank=True)
    guarantee_note = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    risk_level = models.CharField(max_length=20, choices=Risk.choices, default=Risk.MEDIUM)
    is_featured = models.BooleanField(default=False)
    target_amount = models.BigIntegerField(default=0)
    raised_amount = models.BigIntegerField(default=0)
    min_investment = models.BigIntegerField(default=100_000_000)
    max_investment = models.BigIntegerField(null=True, blank=True)
    invest_step = models.BigIntegerField(default=10_000_000)
    monthly_rate = models.DecimalField(max_digits=6, decimal_places=4, default='0.0600')
    duration_months = models.PositiveSmallIntegerField(default=6)
    payout_mode = models.CharField(max_length=20, choices=PayoutMode.choices, default=PayoutMode.LUMP)
    return_principal = models.BooleanField(default=True)
    product_name = models.CharField(max_length=120, default='نوار تیپ')
    unit_label = models.CharField(max_length=40, default='حلقه')
    region = models.CharField(max_length=120, blank=True)
    cover = models.ImageField(upload_to='plans/', blank=True)
    cover_preset = models.PositiveSmallIntegerField(default=1)
    investors_count = models.PositiveIntegerField(default=0)
    sort_order = models.IntegerField(default=0)
    keshtyar_sale_id = models.PositiveIntegerField(
        'شناسه اعلام فروش کشت‌یار', null=True, blank=True, unique=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', '-is_featured', '-id']
        verbose_name = 'طرح'
        verbose_name_plural = 'طرح‌ها'

    def __str__(self):
        return self.title

    @property
    def cover_url(self):
        if self.cover:
            return self.cover.url
        n = self.cover_preset if 1 <= self.cover_preset <= 6 else 1
        return static(f'img/covers/cover-{n}.jpg')

    @property
    def rate_percent(self):
        return float(self.monthly_rate) * 100

    @property
    def funding_percent(self):
        if not self.target_amount:
            return 0
        return min(100, round(self.raised_amount * 100 / self.target_amount, 1))

    @property
    def accepts_investment(self):
        return self.status == self.Status.OPEN


class Investment(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'در انتظار بررسی'
        APPROVED = 'approved', 'تأیید شده'
        ACTIVE = 'active', 'در حال اجرا'
        MATURED = 'matured', 'رسیده به سررسید'
        SETTLED = 'settled', 'تسویه شده'
        REJECTED = 'rejected', 'رد شده'
        CANCELLED = 'cancelled', 'لغو شده'

    contract_no = models.CharField(max_length=30, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='investments')
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name='investments')
    amount = models.BigIntegerField()
    months = models.PositiveSmallIntegerField(default=6)
    monthly_rate = models.DecimalField(max_digits=6, decimal_places=4, default='0.0600')
    payout_mode = models.CharField(max_length=20, default=Plan.PayoutMode.LUMP)
    return_principal = models.BooleanField(default=True)
    monthly_profit = models.BigIntegerField(default=0)
    total_profit = models.BigIntegerField(default=0)
    total_return = models.BigIntegerField(default=0)
    paid_profit = models.BigIntegerField(default=0)
    paid_principal = models.BigIntegerField(default=0)
    received_amount = models.BigIntegerField(default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    request_date = models.DateField(null=True, blank=True)
    deposit_deadline = models.DateField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    maturity_date = models.DateField(null=True, blank=True)
    settled_at = models.DateTimeField(null=True, blank=True)
    investor_note = models.TextField(blank=True)
    admin_note = models.TextField(blank=True)
    reject_reason = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-id']
        verbose_name = 'سرمایه‌گذاری'
        verbose_name_plural = 'سرمایه‌گذاری‌ها'

    def __str__(self):
        return self.contract_no

    @property
    def rate_percent(self):
        return float(self.monthly_rate) * 100


class Payout(models.Model):
    class Kind(models.TextChoices):
        PROFIT = 'profit', 'سود'
        PRINCIPAL = 'principal', 'اصل سرمایه'

    class Status(models.TextChoices):
        SCHEDULED = 'scheduled', 'زمان‌بندی‌شده'
        PAID = 'paid', 'واریز شده'

    class Confirm(models.TextChoices):
        NONE = 'none', '—'
        AWAITING = 'awaiting', 'منتظر تأیید سرمایه‌گذار'
        CONFIRMED = 'confirmed', 'تأیید شد'

    investment = models.ForeignKey(Investment, on_delete=models.CASCADE, related_name='payouts')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payouts')
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name='payouts')
    kind = models.CharField(max_length=20, choices=Kind.choices)
    due_date = models.DateField()
    amount = models.BigIntegerField()
    paid_amount = models.BigIntegerField(default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SCHEDULED)
    confirm_status = models.CharField(max_length=20, choices=Confirm.choices, default=Confirm.NONE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['due_date', 'id']

    def __str__(self):
        return f'{self.investment.contract_no} {self.get_kind_display()}'


class BankAccount(models.Model):
    title = models.CharField(max_length=120)
    bank_name = models.CharField(max_length=80, blank=True)
    owner_name = models.CharField(max_length=150, blank=True)
    iban = models.CharField(max_length=30, blank=True)
    account_number = models.CharField(max_length=40, blank=True)
    note = models.CharField(max_length=500, blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'id']

    def __str__(self):
        return self.title


class Lead(models.Model):
    class Status(models.TextChoices):
        NEW = 'new', 'جدید'
        CONTACTED = 'contacted', 'تماس گرفته شد'
        CLOSED = 'closed', 'بسته'

    track_code = models.CharField(max_length=20, unique=True)
    full_name = models.CharField(max_length=150)
    mobile = models.CharField(max_length=15)
    city = models.CharField(max_length=80, blank=True)
    amount = models.BigIntegerField(null=True, blank=True)
    plan = models.ForeignKey(Plan, null=True, blank=True, on_delete=models.SET_NULL)
    call_time = models.CharField(max_length=60, blank=True)
    message = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return self.track_code


class Faq(models.Model):
    question = models.CharField(max_length=300)
    answer = models.TextField()
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['sort_order', 'id']

    def __str__(self):
        return self.question


class Page(models.Model):
    slug = models.SlugField(max_length=80, unique=True, allow_unicode=True)
    title = models.CharField(max_length=180)
    body = models.TextField()
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class Ticket(models.Model):
    class Status(models.TextChoices):
        OPEN = 'open', 'باز'
        ANSWERED = 'answered', 'پاسخ داده شد'
        USER_REPLY = 'user_reply', 'پاسخ سرمایه‌گذار'
        CLOSED = 'closed', 'بسته'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tickets')
    subject = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return self.subject


class TicketMessage(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='messages')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id']


class Notification(models.Model):
    class Level(models.TextChoices):
        INFO = 'info', 'اطلاع'
        WARN = 'warn', 'هشدار'
        OK = 'ok', 'موفق'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    level = models.CharField(max_length=20, choices=Level.choices, default=Level.INFO)
    url = models.CharField(max_length=300, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-id']


class Document(models.Model):
    class Visibility(models.TextChoices):
        PUBLIC = 'public', 'عمومی'
        INVESTORS = 'investors', 'سرمایه‌گذاران'

    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    plan = models.ForeignKey(Plan, null=True, blank=True, on_delete=models.SET_NULL, related_name='documents')
    visibility = models.CharField(max_length=20, choices=Visibility.choices, default=Visibility.INVESTORS)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-published_at']

    def __str__(self):
        return self.title
