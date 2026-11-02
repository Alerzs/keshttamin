from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from portal.models import (
    BankAccount, Document, Faq, Investment, Notification, Page, Payout, Plan, Ticket,
    TicketMessage, User,
)
from portal.services import build_payouts
from portal.site import DEFAULTS, set_value
from portal.utils import schedule


class Command(BaseCommand):
    help = 'داده‌های نمونه کشت‌تامین را می‌سازد'

    def handle(self, *args, **options):
        for key, value in DEFAULTS.items():
            set_value(key, value)

        admin, created = User.objects.get_or_create(
            mobile='09120000000',
            defaults={
                'username': 'admin',
                'full_name': 'مدیر کشت‌تامین',
                'role': User.Role.ADMIN,
                'status': User.Status.ACTIVE,
            },
        )
        if created:
            admin.set_password('KeshtAdmin@1405')
            admin.save()

        investor, created = User.objects.get_or_create(
            mobile='09121111111',
            defaults={
                'username': 'investor',
                'full_name': 'سارا محمدی',
                'role': User.Role.INVESTOR,
                'status': User.Status.ACTIVE,
                'city': 'اصفهان',
                'national_id': '0088888888',
                'bank_name': 'ملت',
                'iban': 'IR120170000000123456789001',
                'account_owner': 'سارا محمدی',
            },
        )
        if created:
            investor.set_password('KeshtInvest@1405')
            investor.save()

        BankAccount.objects.get_or_create(
            title='حساب عملیاتی نوار تیپ',
            defaults={
                'bank_name': 'ملت',
                'owner_name': 'کشت‌تامین',
                'iban': 'IR490120000000009876543210',
                'account_number': '9876543210',
                'note': 'واریز فقط از حساب به نام خود سرمایه‌گذار.',
                'is_active': True,
            },
        )

        pages = {
            'about': ('درباره ما', '''<p>ما یک مجموعه فعال در زنجیره تأمین و توزیع تجهیزات آبیاری قطره‌ای هستیم. محصول اصلی ما نوار تیپ است که در سراسر کشور به فروشگاه‌داران، کشاورزان و گلخانه‌داران عرضه می‌شود.</p>
<p>مدل فروش ترکیبی است: بخشی از هر معامله نقدی تسویه می‌شود و بخش دیگر اقساط و چک مدت‌دار. سرمایه‌گذار فاصله خرید نقدی تا وصول مطالبات را پر می‌کند و در پایان دوره، سود توافق‌شده به همراه اصل سرمایه بازمی‌گردد.</p>'''),
            'terms': ('شرایط و قوانین', '''<h3>۱. ماهیت همکاری</h3><p>مشارکت در طرح‌ها، تأمین سرمایه در گردش خرید کالاست و به منزله سپرده بانکی یا اوراق بهادار نیست.</p>
<h3>۲. سود و زمان‌بندی</h3><p>نرخ، مدت و تاریخ واریز پیش از تأیید در قرارداد ثبت می‌شود. سود ساده و ماهانه روی اصل سرمایه محاسبه می‌گردد.</p>
<h3>۳. ریسک</h3><p>هر فعالیت تجاری با ریسک همراه است. پشتوانه طرح، کالا و مطالبات اسنادی است.</p>'''),
            'privacy': ('حریم خصوصی', '''<h3>اطلاعات</h3><p>نام، موبایل، کد ملی و شبای بانکی فقط برای قرارداد، احراز هویت و واریز وجوه استفاده می‌شود.</p>
<h3>نگهداری</h3><p>رمز عبور به صورت درهم‌سازی‌شده ذخیره می‌شود و قابل بازیابی نیست.</p>'''),
            'contact': ('تماس با ما', '<p>برای هماهنگی جلسه، بررسی طرح‌ها یا پیگیری مشارکت، فرم روبه‌رو را پر کنید یا با شماره پشتیبانی تماس بگیرید.</p>'),
        }
        for slug, (title, body) in pages.items():
            Page.objects.update_or_create(slug=slug, defaults={'title': title, 'body': body, 'is_active': True})

        faqs = [
            ('سود چگونه محاسبه می‌شود؟', 'سود ساده و ماهانه روی اصل سرمایه است. با نرخ ۶ درصد، هر یک میلیارد تومان در ماه ۶۰ میلیون تومان سود می‌سازد.'),
            ('سود چه زمانی واریز می‌شود؟', 'سود هر ماه قطعی و در پنل دیده می‌شود. در حالت یکجا، مجموع سود و اصل سرمایه در پایان دوره به شبا واریز می‌شود.'),
            ('حداقل مبلغ چقدر است؟', 'حداقل هر طرح جداگانه در صفحه همان طرح نوشته شده است.'),
            ('سرمایه صرف چه می‌شود؟', 'خرید نوار تیپ از تولیدکننده و فروش ترکیبی نقد و اقساط به شبکه توزیع.'),
            ('برداشت زودتر از سررسید؟', 'تسویه زودهنگام فقط با توافق کتبی و بررسی نقدینگی طرح ممکن است.'),
            ('چه مدارکی لازم است؟', 'موبایل به نام خودتان و شبای بانکی به نام خودتان. کد ملی و مدارک تکمیلی اختیاری است.'),
        ]
        for order, (q, a) in enumerate(faqs, start=1):
            Faq.objects.update_or_create(question=q, defaults={'answer': a, 'sort_order': order, 'is_active': True})

        plan_specs = [
            dict(
                code='NT-1405-01', slug='bahar-1405', title='طرح نوار تیپ بهار ۱۴۰۵',
                subtitle='خرید عمده از تولیدکننده و توزیع در شبکه فروشگاه‌های غرب کشور',
                summary='سرمایه این طرح صرف خرید نقدی نوار تیپ و فروش ترکیبی ۵۰ درصد نقد و ۵۰ درصد چک مدت‌دار می‌شود.',
                description='کالا از تولیدکننده با پرداخت نقدی خریداری می‌شود تا قیمت تمام‌شده پایین بماند. فروش به فروشگاه‌داران و کشاورزان با ترکیب نقد و اقساط انجام می‌گیرد و چک‌های مدت‌دار پشتوانه وصول هستند.',
                usage_of_funds='خرید نوار تیپ، حمل تا انبار منطقه‌ای و تأمین اعتبار فروش اقساطی.',
                guarantee_note='پشتوانه طرح، موجودی کالا و چک‌های مدت‌دار مشتریان شبکه توزیع است.',
                risk_note='تأخیر در وصول چک یا تغییر قیمت کالا می‌تواند زمان تسویه را جابه‌جا کند. سود، تعهد قراردادی مجری است و سود بانکی نیست.',
                status=Plan.Status.OPEN, risk_level=Plan.Risk.MEDIUM, is_featured=True,
                target_amount=5_000_000_000, raised_amount=1_800_000_000, min_investment=100_000_000,
                invest_step=10_000_000, monthly_rate='0.0600', duration_months=6,
                payout_mode=Plan.PayoutMode.LUMP, region='غرب کشور', cover_preset=1,
                investors_count=12, sort_order=1,
            ),
            dict(
                code='NT-1405-02', slug='golkhane-jonub', title='طرح گلخانه‌های جنوب',
                subtitle='تأمین نوار تیپ گلخانه‌های جیرفت و کهنوج',
                summary='این طرح خرید و توزیع نوار تیپ برای گلخانه‌داران جنوب را با دوره نه ماهه پوشش می‌دهد.',
                description='تمرکز طرح بر گلخانه‌هایی است که خرید اقساطی فصل کشت دارند. نیمی از فروش نقد و نیم دیگر با چک سررسیددار ثبت می‌شود.',
                usage_of_funds='خرید نقدی کالا و پوشش فاصله وصول اقساط گلخانه‌داران.',
                guarantee_note='مطالبات با چک و قرارداد فروش ثبت می‌شود و در گزارش دوره‌ای پنل می‌آید.',
                risk_note='فصل کشت و توان پرداخت گلخانه‌دار بر زمان وصول اثر می‌گذارد.',
                status=Plan.Status.OPEN, risk_level=Plan.Risk.MEDIUM, is_featured=False,
                target_amount=3_000_000_000, raised_amount=900_000_000, min_investment=200_000_000,
                invest_step=10_000_000, monthly_rate='0.0550', duration_months=9,
                payout_mode=Plan.PayoutMode.MONTHLY, region='جنوب کرمان', cover_preset=2,
                investors_count=7, sort_order=2,
            ),
            dict(
                code='NT-1404-08', slug='paeez-1404', title='طرح پاییزه ۱۴۰۴',
                subtitle='دوره قبلی که ظرفیتش تکمیل شده است',
                summary='این طرح مرحله جذب را پشت سر گذاشته و اکنون در حال اجراست.',
                description='نمونه یک طرح تأمین‌شده برای دیدن وضعیت پس از پایان جذب سرمایه.',
                usage_of_funds='خرید و توزیع نوار تیپ در شبکه شمال غرب.',
                guarantee_note='کالا تحویل شده و مطالبات در حال وصول است.',
                risk_note='ریسک اصلی، تأخیر وصول چک‌های باقی‌مانده است.',
                status=Plan.Status.ACTIVE, risk_level=Plan.Risk.LOW, is_featured=False,
                target_amount=2_000_000_000, raised_amount=2_000_000_000, min_investment=100_000_000,
                invest_step=10_000_000, monthly_rate='0.0600', duration_months=6,
                payout_mode=Plan.PayoutMode.LUMP, region='آذربایجان', cover_preset=4,
                investors_count=18, sort_order=3,
            ),
        ]
        plans = {}
        for spec in plan_specs:
            code = spec['code']
            plans[code], _ = Plan.objects.update_or_create(code=code, defaults=spec)

        plan = plans['NT-1405-02']
        calc = schedule(500_000_000, plan.duration_months, plan.monthly_rate, True)
        investment, made = Investment.objects.get_or_create(
            contract_no='KT-1405-0007',
            defaults={
                'user': investor,
                'plan': plan,
                'amount': 500_000_000,
                'months': plan.duration_months,
                'monthly_rate': plan.monthly_rate,
                'payout_mode': plan.payout_mode,
                'return_principal': True,
                'monthly_profit': calc['monthly_profit'],
                'total_profit': calc['total_profit'],
                'total_return': calc['total_return'],
                'status': Investment.Status.ACTIVE,
                'request_date': timezone.localdate() - timedelta(days=50),
                'start_date': timezone.localdate() - timedelta(days=40),
                'received_amount': 500_000_000,
            },
        )
        if made:
            build_payouts(investment)
            first = investment.payouts.filter(kind=Payout.Kind.PROFIT).first()
            if first:
                first.paid_amount = first.amount
                first.status = Payout.Status.PAID
                first.confirm_status = Payout.Confirm.AWAITING
                first.save()
                investment.paid_profit = first.amount
                investment.save(update_fields=['paid_profit'])

        other = plans['NT-1405-01']
        calc2 = schedule(200_000_000, other.duration_months, other.monthly_rate, True)
        Investment.objects.get_or_create(
            contract_no='KT-1405-0012',
            defaults={
                'user': investor,
                'plan': other,
                'amount': 200_000_000,
                'months': other.duration_months,
                'monthly_rate': other.monthly_rate,
                'payout_mode': other.payout_mode,
                'monthly_profit': calc2['monthly_profit'],
                'total_profit': calc2['total_profit'],
                'total_return': calc2['total_return'],
                'status': Investment.Status.PENDING,
                'request_date': timezone.localdate(),
                'investor_note': 'درخواست نمونه برای بررسی کارشناس.',
            },
        )

        Document.objects.get_or_create(
            title='گزارش عملکرد ماه اول — گلخانه‌های جنوب',
            defaults={
                'plan': plan,
                'body': 'کالای خریداری‌شده به انبار منطقه‌ای رسیده و بخش نقدی فروش ثبت شده است. وصول چک‌های ماه نخست طبق برنامه پیش می‌رود.',
                'visibility': Document.Visibility.INVESTORS,
                'published_at': timezone.now(),
            },
        )

        ticket, _ = Ticket.objects.get_or_create(
            user=investor, subject='زمان واریز سود ماه اول',
            defaults={'status': Ticket.Status.ANSWERED},
        )
        if not ticket.messages.exists():
            TicketMessage.objects.create(ticket=ticket, author=investor, body='سود ماه اول چه زمانی به شبا واریز می‌شود؟')
            TicketMessage.objects.create(ticket=ticket, author=admin, body='در این طرح سود هر ماه قطعی می‌شود و طبق تقویم قرارداد واریز می‌گردد. ردیف ماه اول در بخش سود و پرداخت‌ها منتظر تأیید شماست.')

        Notification.objects.get_or_create(
            user=investor,
            title='واریز سود منتظر تأیید شماست',
            defaults={
                'body': 'پس از دیدن مبلغ در حساب، دریافت را در تقویم پرداخت تأیید کنید.',
                'level': Notification.Level.WARN,
                'url': '/panel/calendar/?f=awaiting',
            },
        )

        self.stdout.write(self.style.SUCCESS('داده نمونه آماده است.'))
        self.stdout.write('مدیر: 09120000000 / KeshtAdmin@1405')
        self.stdout.write('سرمایه‌گذار: 09121111111 / KeshtInvest@1405')
