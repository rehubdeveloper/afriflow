from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
import random
from django.conf import settings
import uuid
from django.utils import timezone

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)

class CustomUser(AbstractBaseUser, PermissionsMixin):
    BUSINESS_TYPE_CHOICES = [
        ('business', 'Business'),
        ('individual', 'Individual'),
    ]

    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20)
    country = models.CharField(max_length=100)
    state_province = models.CharField(max_length=100)
    preferred_language = models.CharField(max_length=50)
    business_type = models.CharField(max_length=10, choices=BUSINESS_TYPE_CHOICES)
    language = models.CharField(max_length=50)

    pin = models.CharField(max_length=4, default='0000')
    voice_mode = models.BooleanField(default=False)
    enable_biometrics_login = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name', 'phone_number', 'country', 'state_province', 'preferred_language', 'business_type', 'language']

    def __str__(self):
        return self.email
    
from django.conf import settings

class Wallet(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wallet')
    wallet_number = models.CharField(max_length=6, unique=True, blank=True)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    def save(self, *args, **kwargs):
        if not self.wallet_number:
            self.wallet_number = self._generate_unique_wallet_number()
        super().save(*args, **kwargs)

    def _generate_unique_wallet_number(self):
        while True:
            number = f"{random.randint(0, 999999):06d}"
            if not Wallet.objects.filter(wallet_number=number).exists():
                return number

    def __str__(self):
        return f"{self.user.email} Wallet {self.wallet_number} - Balance: {self.balance}"



from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=CustomUser)
def create_user_wallet(sender, instance, created, **kwargs):
    if created:
        from .models import Wallet
        Wallet.objects.create(user=instance)




class Transaction(models.Model):
    transaction_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_transactions')
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_transactions')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    receiver_name = models.CharField(max_length=255)
    receiver_account_number = models.CharField(max_length=20)
    description = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Transaction {self.transaction_id} from {self.sender.email} to {self.receiver.email}"
    
class ChatSession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chat_sessions')
    session_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    title = models.CharField(max_length=255, blank=True, null=True)  # Optional title for the chat session
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"ChatSession {self.session_id} for {self.user.email}"

class ChatMessage(models.Model):
    ROLE_CHOICES = [
        ('system', 'System'),
        ('user', 'User'),
        ('assistant', 'Assistant'),
    ]

    chat_session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.role} message at {self.timestamp} in session {self.chat_session.session_id}"