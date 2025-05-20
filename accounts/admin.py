from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Wallet, Transaction

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('email', 'full_name', 'business_type', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_active', 'business_type')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('full_name', 'phone_number', 'country', 'state_province', 'preferred_language', 'language', 'business_type', 'pin', 'voice_mode', 'enable_biometrics_login')}),
        ('Permissions', {'fields': ('is_staff', 'is_active', 'is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'full_name', 'phone_number', 'country', 'state_province', 'preferred_language', 'language', 'business_type', 'pin', 'voice_mode', 'enable_biometrics_login', 'is_staff', 'is_active')}
        ),
    )
    search_fields = ('email', 'full_name')
    ordering = ('email',)

admin.site.register(CustomUser, CustomUserAdmin)

from .models import Wallet

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'wallet_number', 'balance')
    search_fields = ('user__email', 'wallet_number')


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'sender', 'receiver_name', 'receiver_account_number', 'amount', 'timestamp')
    search_fields = ('transaction_id', 'sender__email', 'receiver_name', 'receiver_account_number')
    list_filter = ('timestamp',)
    ordering = ('-timestamp',)


