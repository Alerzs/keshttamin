import json
from datetime import date

from django.test import TestCase, override_settings

from portal.models import Notification, Plan, User
from portal.utils import add_months, jalali, money


def _sample():
    today = date.today()
    first = add_months(today, 2)
    second = add_months(today, 5)
    return {
        'sale_amount': 2_000_000,
        'check_count': 2,
        'check_due_dates': [second.isoformat(), first.isoformat()],
    }, first, second


@override_settings(KESHTTAMIN_API_KEY='test-key')
class CheckSaleApiTests(TestCase):
    def setUp(self):
        User.objects.create(mobile='09123334444', full_name='مدیر تست', role=User.Role.ADMIN)
        self.payload, self.first_due, self.last_due = _sample()

    def post(self, payload, key='test-key'):
        return self.client.post(
            '/api/keshtyar/check-sales',
            data=json.dumps(payload, ensure_ascii=False),
            content_type='application/json; charset=utf-8',
            HTTP_X_API_KEY=key,
        )

    def test_creates_plan_from_amount_count_and_due_dates(self):
        response = self.post(self.payload)

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIs(body['ok'], True)
        plan = Plan.objects.get(pk=body['id'])
        self.assertIsNone(plan.keshtyar_sale_id)
        self.assertTrue(plan.code.startswith('KY-'))
        self.assertEqual(plan.slug, plan.code.lower())
        self.assertEqual(plan.status, Plan.Status.OPEN)
        self.assertEqual(plan.title, 'طرح فروش چکی')
        self.assertIn('۲ فقره چک', plan.subtitle)
        self.assertIn(jalali(self.last_due), plan.subtitle)
        self.assertEqual(plan.product_name, 'فروش چکی')
        self.assertEqual(plan.target_amount, 2_000_000)
        self.assertEqual(plan.min_investment, 2_000_000)
        self.assertEqual(plan.max_investment, 2_000_000)
        self.assertEqual(plan.duration_months, 5)
        self.assertEqual(plan.risk_level, Plan.Risk.MEDIUM)
        self.assertIn(money(2_000_000), plan.summary)
        self.assertIn(jalali(self.first_due), plan.description)
        self.assertIn(jalali(self.last_due), plan.guarantee_note)
        self.assertIn('سررسید چک‌ها', plan.risk_note)
        self.assertEqual(Notification.objects.filter(user__role=User.Role.ADMIN).count(), 1)

    def test_each_post_creates_its_own_plan(self):
        first = self.post(self.payload)
        second = self.post(self.payload)

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertNotEqual(first.json()['id'], second.json()['id'])
        self.assertEqual(Plan.objects.count(), 2)
        self.assertEqual(Notification.objects.count(), 2)

    def test_single_check_uses_its_due_date(self):
        due = add_months(date.today(), 1)
        response = self.post({
            'sale_amount': 2_000_000,
            'check_count': 1,
            'check_due_dates': [due.isoformat()],
        })

        self.assertEqual(response.status_code, 200)
        plan = Plan.objects.get(pk=response.json()['id'])
        self.assertEqual(plan.duration_months, 1)
        self.assertIn('۱ فقره چک', plan.subtitle)
        self.assertIn(jalali(due), plan.subtitle)

    def test_past_due_date_still_opens_a_one_month_plan(self):
        response = self.post({
            'sale_amount': 2_000_000,
            'check_count': 1,
            'check_due_dates': ['2020-01-01'],
        })

        self.assertEqual(response.status_code, 200)
        plan = Plan.objects.get(pk=response.json()['id'])
        self.assertEqual(plan.duration_months, 1)

    def test_rejects_bad_key_and_bad_body(self):
        self.assertEqual(self.post(self.payload, key='nope').status_code, 401)
        self.assertEqual(self.client.post('/api/keshtyar/check-sales').status_code, 401)
        self.assertEqual(self.client.get('/api/keshtyar/check-sales', HTTP_X_API_KEY='test-key').status_code, 405)

        broken = self.client.post(
            '/api/keshtyar/check-sales',
            data='{',
            content_type='application/json',
            HTTP_X_API_KEY='test-key',
        )
        self.assertEqual(broken.status_code, 400)
        self.assertIs(broken.json()['ok'], False)

        cases = [
            {},
            {'sale_amount': 0, 'check_count': 1, 'check_due_dates': ['2026-12-01']},
            {'sale_amount': 1.5, 'check_count': 1, 'check_due_dates': ['2026-12-01']},
            {'sale_amount': 2_000_000, 'check_count': 2, 'check_due_dates': ['2026-12-01']},
            {'sale_amount': 2_000_000, 'check_count': 1, 'check_due_dates': ['2026-13-40']},
            {'sale_amount': 2_000_000, 'check_count': 1, 'check_due_dates': ['2026-12-01T00:00:00']},
        ]
        for payload in cases:
            response = self.post(payload)
            self.assertEqual(response.status_code, 422, payload)
            self.assertIs(response.json()['ok'], False)
        self.assertEqual(Plan.objects.count(), 0)
