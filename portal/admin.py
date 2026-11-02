from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import (
    BankAccount, Document, Faq, Investment, Lead, Notification, Page, Payout, Plan,
    Setting, Ticket, TicketMessage, User,
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        ('کشت‌تامین', {'fields': (
            'role', 'status', 'mobile', 'full_name', 'national_id', 'city',
            'iban', 'bank_name', 'kyc_status',
        )}),
    )
    list_display = ('full_name', 'mobile', 'role', 'status')
    search_fields = ('full_name', 'mobile', 'username')


admin.site.register(Plan)
admin.site.register(Investment)
admin.site.register(Payout)
admin.site.register(Lead)
admin.site.register(Faq)
admin.site.register(Page)
admin.site.register(Ticket)
admin.site.register(TicketMessage)
admin.site.register(Notification)
admin.site.register(Document)
admin.site.register(BankAccount)
admin.site.register(Setting)
