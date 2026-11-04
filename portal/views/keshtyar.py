import hmac
import json
import logging

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from portal.keshtyar_sales import SalePayloadError, upsert_check_sale

logger = logging.getLogger(__name__)


def _json(payload, status=200):
    return JsonResponse(
        payload,
        status=status,
        json_dumps_params={'ensure_ascii': False},
        content_type='application/json; charset=utf-8',
    )


@csrf_exempt
def check_sale(request):
    if request.method != 'POST':
        return _json({'ok': False, 'error': 'فقط متد POST پذیرفته است.'}, 405)

    expected = settings.KESHTTAMIN_API_KEY
    provided = request.headers.get('X-Api-Key', '')
    if not expected or not provided or not hmac.compare_digest(provided.encode('utf-8'), expected.encode('utf-8')):
        return _json({'ok': False, 'error': 'کلید API نامعتبر است.'}, 401)

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return _json({'ok': False, 'error': 'بدنه درخواست JSON نیست.'}, 400)

    try:
        plan, _created = upsert_check_sale(payload)
    except SalePayloadError as exc:
        return _json({'ok': False, 'error': str(exc)[:180]}, 422)
    except Exception:
        logger.exception('keshtyar check sale failed')
        return _json({'ok': False, 'error': 'ذخیره فروش در کشت‌تامین ناموفق بود.'}, 500)

    logger.info('keshtyar check sale %s stored as plan %s', plan.keshtyar_sale_id, plan.pk)
    return _json({'ok': True, 'id': plan.pk})
