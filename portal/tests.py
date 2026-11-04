import json

from django.test import TestCase, override_settings

from portal.models import Notification, Plan, User


SAMPLE = {
    'source': 'keshtyar',
    'event': 'check_sale_approved',
    'sale_request_id': 42,
    'sold_on': '2026-10-22',
    'sold_on_jalali': '۱۴۰۵/۰۷/۳۰',
    'settlement': 'قسطی',
    'note': 'تحویل درب گلخانه',
    'review_note': 'مدارک کامل بود',
    'seller': {'id': 3, 'username': 'ali', 'full_name': 'علی محمدی'},
    'customer': {
        'id': 18,
        'name': 'رضا کریمی',
        'phone': '09121234567',
        'city': 'کرمان',
        'address': 'رفسنجان، خیابان مطهری',
        'customer_type': 'کشاورز',
        'credit': {
            'fatherName': 'حسین',
            'nationalId': '0012345678',
            'mainBank': 'ملت',
            'accountNo': '1234567890',
            'iban': 'IR120170000000123456789001',
            'bouncedCheck': 'ندارد',
        },
    },
    'invoice': {
        'id': 90,
        'number': '00015',
        'status': 'در حال پیگیری',
        'settlement': 'قسطی',
        'sold_on': '2026-10-22',
        'sold_on_jalali': '۱۴۰۵/۰۷/۳۰',
        'purchase_amount': 800000,
        'sale_amount': 2000000,
        'cost_amount': 800000,
        'note': 'تحویل درب گلخانه',
    },
    'lines': [
        {'id': 120, 'product_name': 'کود', 'qty': 2, 'unit_price': 1000000, 'unit_cost': 400000},
    ],
    'payments': [
        {'id': 70, 'amount': 500000, 'method': 'شبا', 'paid_on': '2026-10-22', 'note': 'پیش‌پرداخت'},
    ],
    'checks': [
        {
            'id': 33,
            'number': '123456',
            'amount': 1500000,
            'bank': 'ملت',
            'status': 'در جریان',
            'due_on': '2026-12-01',
            'due_on_jalali': '۱۴۰۵/۰۹/۱۰',
        },
    ],
    'guarantees': [{'type': 'چک صیادی', 'holder': 'رضا کریمی', 'amount': 1500000}],
    'references': [{'name': 'حسن رضایی', 'relation': 'همکار صنفی', 'phone': '09120000000'}],
    'docs': ['کپی کارت ملی', 'نمونه چک'],
    'warnings': [],
    'files': [{'name': 'kart-melli.jpg', 'uploaded_at': '2026-10-22T08:00:00+00:00'}],
}

PRIVATE = ('09121234567', '09120000000', '0012345678', 'رضا کریمی', 'رفسنجان', '1234567890', 'kart-melli', 'علی محمدی')


@override_settings(KESHTTAMIN_API_KEY='test-key')
class CheckSaleApiTests(TestCase):
    def setUp(self):
        User.objects.create(mobile='09123334444', full_name='مدیر تست', role=User.Role.ADMIN)

    def post(self, payload, key='test-key'):
        return self.client.post(
            '/api/keshtyar/check-sales',
            data=json.dumps(payload, ensure_ascii=False),
            content_type='application/json; charset=utf-8',
            HTTP_X_API_KEY=key,
        )

    def test_creates_display_plan_and_hides_private_fields(self):
        response = self.post(SAMPLE)

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['ok'], True)
        plan = Plan.objects.get(pk=body['id'])
        self.assertEqual(plan.keshtyar_sale_id, 42)
        self.assertEqual(plan.code, 'KY-42')
        self.assertEqual(plan.slug, 'ky-42')
        self.assertEqual(plan.status, Plan.Status.OPEN)
        self.assertEqual(plan.title, 'طرح فروش کود در کرمان')
        self.assertIn('00015', plan.subtitle)
        self.assertIn('۱۴۰۵/۰۷/۳۰', plan.subtitle)
        self.assertEqual(plan.region, 'کرمان')
        self.assertEqual(plan.product_name, 'کود')
        self.assertEqual(plan.target_amount, 1_500_000)
        self.assertEqual(plan.min_investment, 1_500_000)
        self.assertEqual(plan.duration_months, 2)
        self.assertEqual(plan.risk_level, Plan.Risk.MEDIUM)
        self.assertIn('کشاورز در کرمان', plan.description)
        self.assertIn('تحویل درب گلخانه', plan.description)
        self.assertIn('۸۰۰', plan.usage_of_funds)
        self.assertIn('چک صیادی', plan.guarantee_note)
        self.assertIn('ملت', plan.guarantee_note)
        self.assertIn('کپی کارت ملی', plan.guarantee_note)
        shown = '\n'.join([
            plan.title, plan.subtitle, plan.summary, plan.description,
            plan.usage_of_funds, plan.guarantee_note, plan.risk_note,
        ])
        for secret in PRIVATE:
            self.assertNotIn(secret, shown)
        self.assertEqual(Notification.objects.filter(user__role=User.Role.ADMIN).count(), 1)

    def test_repeat_updates_same_plan(self):
        first = self.post(SAMPLE)
        plan = Plan.objects.get(pk=first.json()['id'])
        plan.status = Plan.Status.CLOSED
        plan.raised_amount = 25_000
        plan.save(update_fields=['status', 'raised_amount'])

        again = dict(SAMPLE)
        again['invoice'] = dict(SAMPLE['invoice'], number='00099')
        second = self.post(again)

        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json()['id'], plan.pk)
        self.assertEqual(Plan.objects.filter(keshtyar_sale_id=42).count(), 1)
        plan.refresh_from_db()
        self.assertIn('00099', plan.subtitle)
        self.assertEqual(plan.status, Plan.Status.CLOSED)
        self.assertEqual(plan.raised_amount, 25_000)
        self.assertEqual(Notification.objects.count(), 1)

    def test_rejects_bad_key_and_bad_body(self):
        self.assertEqual(self.post(SAMPLE, key='nope').status_code, 401)
        self.assertEqual(self.client.post('/api/keshtyar/check-sales').status_code, 401)
        self.assertEqual(self.client.get('/api/keshtyar/check-sales', HTTP_X_API_KEY='test-key').status_code, 405)

        broken = self.client.post(
            '/api/keshtyar/check-sales',
            data='{',
            content_type='application/json',
            HTTP_X_API_KEY='test-key',
        )
        self.assertEqual(broken.status_code, 400)
        self.assertFalse(broken.json()['ok'])

        missing = self.post({'source': 'keshtyar', 'event': 'check_sale_approved'})
        self.assertEqual(missing.status_code, 422)
        self.assertEqual(Plan.objects.count(), 0)
