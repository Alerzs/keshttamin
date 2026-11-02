from .models import BankAccount, Investment, Lead, Notification, Ticket
from .site import as_dict, get_bool


def site_context(request):
    user = request.user
    data = {'site': as_dict()}
    if get_bool('deposit_accounts_enabled', True):
        data['bank_accounts'] = BankAccount.objects.filter(is_active=True)
    if not user.is_authenticated:
        return data
    data['unread_count'] = Notification.objects.filter(user=user, read_at__isnull=True).count()
    if user.role == 'investor':
        data['investor_todo'] = Investment.objects.filter(user=user, status=Investment.Status.APPROVED).count()
        data['investor_awaiting'] = user.payouts.filter(confirm_status='awaiting').count()
    if getattr(user, 'is_staff_role', False):
        data['staff_pending'] = Investment.objects.filter(status=Investment.Status.PENDING).count()
        data['staff_leads'] = Lead.objects.filter(status=Lead.Status.NEW).count()
        data['staff_tickets'] = Ticket.objects.filter(status__in=['open', 'user_reply']).count()
    return data
