from django.contrib import admin

from .models import XeroConnection, OpenInvoiceSnapshot, Invoice, SyncRun


@admin.register(XeroConnection)
class XeroConnectionAdmin(admin.ModelAdmin):
    list_display = ('tenant_name', 'tenant_id', 'token_expires_at', 'updated_at')


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'contact_name', 'status', 'invoice_date', 'due_date', 'total', 'amount_due', 'currency')
    list_filter = ('status', 'currency')
    search_fields = ('invoice_number', 'contact_name')
    date_hierarchy = 'due_date'


@admin.register(OpenInvoiceSnapshot)
class OpenInvoiceSnapshotAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'contact_name', 'bucket', 'days_past_due', 'amount_due', 'due_date')
    list_filter = ('bucket',)
    search_fields = ('invoice_number', 'contact_name')


@admin.register(SyncRun)
class SyncRunAdmin(admin.ModelAdmin):
    list_display = ('tenant_id', 'started_at', 'finished_at', 'status', 'invoice_count')
    list_filter = ('status',)
