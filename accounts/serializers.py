from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import CustomUser, Wallet, Transaction, ChatSession, ChatMessage
import re

class RegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    confirm_password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    pin = serializers.CharField(write_only=True, required=True, max_length=4, min_length=4)
    voice_mode = serializers.BooleanField(required=True)
    enable_biometrics_login = serializers.BooleanField(required=True)

    class Meta:
        model = CustomUser
        fields = ['email', 'password', 'confirm_password', 'business_type', 'full_name', 'phone_number', 'country', 'state_province', 'preferred_language', 'language', 'pin', 'voice_mode', 'enable_biometrics_login']

    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        pin = attrs.get('pin')
        if not re.fullmatch(r'\d{4}', str(pin)):
            raise serializers.ValidationError({"pin": "Pin must be exactly 4 digits."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        password = validated_data.pop('password')
        user = CustomUser.objects.create(**validated_data)
        user.set_password(password)
        user.save()
        return user

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            user = authenticate(request=self.context.get('request'), email=email, password=password)
            if not user:
                raise serializers.ValidationError("Unable to log in with provided credentials.")
        else:
            raise serializers.ValidationError("Must include 'email' and 'password'.")
        attrs['user'] = user
        return attrs

class UserInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['email', 'full_name']


class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ['wallet_number', 'balance']

class DepositSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)



class TransferSerializer(serializers.Serializer):
    recipient_wallet_number = serializers.CharField(max_length=6)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    description = serializers.CharField(max_length=255, required=False, allow_blank=True)
    pin = serializers.CharField(max_length=4, required=False, allow_blank=True)
    step = serializers.ChoiceField(choices=['verify', 'transfer'], default='verify')

    
class TransactionSerializer(serializers.ModelSerializer):
    transaction_direction = serializers.SerializerMethodField()
    sender_name = serializers.CharField(source='sender.full_name', read_only=True)
    receiver_name_display = serializers.CharField(source='receiver.full_name', read_only=True)

    class Meta:
        model = Transaction
        fields = [
            'transaction_id',
            'sender_name',
            'receiver_name_display',
            'amount',
            'receiver_name',
            'receiver_account_number',
            'description',
            'timestamp',
            'transaction_direction',
        ]
        read_only_fields = ['transaction_id', 'timestamp']

    def get_transaction_direction(self, obj):
        request = self.context.get('request', None)
        if request and hasattr(request, 'user'):
            user = request.user
            if obj.sender == user:
                return 'outgoing'
            elif obj.receiver == user:
                return 'incoming'
        return 'unknown'
    
class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ['id', 'role', 'content', 'timestamp']

class ChatSessionSerializer(serializers.ModelSerializer):
    messages = ChatMessageSerializer(many=True, read_only=True)

    class Meta:
        model = ChatSession
        fields = ['session_id', 'title', 'created_at', 'updated_at', 'messages']
        read_only_fields = ['session_id', 'created_at', 'updated_at', 'messages']

class ChatPromptSerializer(serializers.Serializer):
    prompt = serializers.CharField(max_length=2000)
    session_id = serializers.UUIDField(required=False)

