from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import authenticate
from .serializers import RegistrationSerializer, LoginSerializer, UserInfoSerializer, WalletSerializer, DepositSerializer, TransferSerializer, TransactionSerializer, ChatPromptSerializer, ChatSessionSerializer, ChatMessageSerializer
from rest_framework.views import APIView
from .models import Wallet, CustomUser, Transaction, ChatSession, ChatMessage
from django.db import transaction
from decimal import Decimal
from django.db.models import Q
import requests

class RegistrationView(generics.CreateAPIView):
    serializer_class = RegistrationSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }, status=status.HTTP_201_CREATED)

class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }, status=status.HTTP_200_OK)

class UserInfoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserInfoSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

class WalletInfoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        wallet = request.user.wallet
        serializer = WalletSerializer(wallet)
        return Response(serializer.data, status=status.HTTP_200_OK)

class DepositView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = DepositSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        amount = serializer.validated_data['amount']
        wallet = request.user.wallet
        wallet.balance += amount
        wallet.save()
        return Response({'message': f'Deposited {amount} successfully.', 'balance': wallet.balance}, status=status.HTTP_200_OK)

class TransferView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = TransferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        step = serializer.validated_data.get('step', 'verify')
        recipient_wallet_number = serializer.validated_data['recipient_wallet_number']
        amount = serializer.validated_data['amount']
        description = serializer.validated_data.get('description', '')
        pin = serializer.validated_data.get('pin', None)

        sender_wallet = request.user.wallet

        if step == 'verify':
            try:
                recipient_wallet = Wallet.objects.get(wallet_number=recipient_wallet_number)
                recipient_user = recipient_wallet.user
                return Response({'recipient_name': recipient_user.full_name}, status=status.HTTP_200_OK)
            except Wallet.DoesNotExist:
                return Response({'error': 'Recipient wallet not found.'}, status=status.HTTP_404_NOT_FOUND)

        elif step == 'transfer':
            if pin is None:
                return Response({'error': 'PIN is required to complete the transfer.'}, status=status.HTTP_400_BAD_REQUEST)

            if pin != request.user.pin:
                return Response({'error': 'Invalid PIN.'}, status=status.HTTP_403_FORBIDDEN)

            if sender_wallet.balance < amount:
                return Response({'error': 'Insufficient balance.'}, status=status.HTTP_400_BAD_REQUEST)

            try:
                recipient_wallet = Wallet.objects.select_for_update().get(wallet_number=recipient_wallet_number)
                recipient_user = recipient_wallet.user
            except Wallet.DoesNotExist:
                return Response({'error': 'Recipient wallet not found.'}, status=status.HTTP_404_NOT_FOUND)

            sender_wallet.balance -= amount
            recipient_wallet.balance += amount
            sender_wallet.save()
            recipient_wallet.save()

            transaction = Transaction.objects.create(
                sender=request.user,
                receiver=recipient_user,
                amount=amount,
                receiver_name=recipient_user.full_name,
                receiver_account_number=recipient_wallet.wallet_number,
                description=description,
            )

            return Response({
                'message': f'Transferred {amount} to {recipient_user.full_name} ({recipient_wallet_number}) successfully.',
                'balance': sender_wallet.balance,
                'recipient_name': recipient_user.full_name,
                'transaction_id': transaction.transaction_id,
                'amount': amount,
                'timestamp': transaction.timestamp
            }, status=status.HTTP_200_OK)

        else:
            return Response({'error': 'Invalid step parameter.'}, status=status.HTTP_400_BAD_REQUEST)

class TransactionListView(generics.ListAPIView):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        transaction_type = self.request.query_params.get('type', None)

        queryset = Transaction.objects.filter(Q(sender=user) | Q(receiver=user)).order_by('-timestamp')

        if transaction_type in ['incoming', 'outgoing']:
            queryset = queryset.filter(transaction_type=transaction_type)

        return queryset

    def get_serializer(self, *args, **kwargs):
        kwargs['context'] = self.get_serializer_context()
        return self.serializer_class(*args, **kwargs)
        

class TransactionDetailView(generics.RetrieveAPIView):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'transaction_id'

    def get_queryset(self):
        user = self.request.user
        return Transaction.objects.filter(Q(sender=user) | Q(receiver=user))

class ChatBotView(APIView):
    permission_classes = [IsAuthenticated]

    system_prompt = """
You are AfriTrade Advisor — a friendly, multilingual assistant dedicated to helping people across Africa understand and succeed in cross-border trade.

🧭 Your Mission:
You guide users—whether they are complete beginners, have limited literacy, or are experienced traders—step by step through exporting and importing goods between African countries.

✅ Core Responsibilities:
1. Explain everything in **clear, friendly, simple language**. Speak like you're helping a friend who is doing this for the first time. Avoid technical terms. Use analogies or examples when helpful.

2. Break down every process into **clear steps**:
   - What documents are needed.
   - Where to get those documents (with links).
   - Which government agencies to contact (with links to official websites).
   - How much each step may cost (mention fees if known).
   - How long it may take.
   - What common mistakes to avoid.

3. Include **official links** for:
   - Government trade portals
   - Certification agencies
   - Customs offices
   - Application forms (with clear instructions on how to fill them)
   - Trade agreements (AfCFTA, ECOWAS, national laws)

4. **Always explain each link**:
   - What the website or form is for.
   - What the user should do once they open the link.
   - Step-by-step help for downloading or submitting forms.
   - If the link is to a portal, explain how to register, login, and navigate.

5. If the user doesn't mention the product or countries involved:
   - Kindly ask them to specify the **origin country**, **destination country**, and the **type of goods** they want to export or import.
   - Then proceed with the most accurate and helpful guidance.

6. For every answer, be:
   - Supportive and positive, like a mentor or friend.
   - Patient and detailed.
   - Focused on **empowering the user** to take action.

7. Do not just refer users to another site. **You must summarize and explain** what they’ll find and do on that site.

8. If web search is available, always provide the most recent and locally relevant information. If not, clarify to the user that your information is based on the latest known standards.

🎯 Example Style:
Instead of saying: "Visit the Kenya Trade Portal for more information."
Say: 
"Go to the Kenya Trade Portal at [https://www.kentrade.go.ke/](https://www.kentrade.go.ke). Once there:
- Click on 'Trade Procedures'.
- Select ‘Export’ or ‘Import’.
- You’ll see a step-by-step list of what you need to do.
For example, if exporting dried hibiscus, choose 'Agricultural Products' to see required forms like the Phytosanitary Certificate."

🌍 Language & Inclusivity:
Always be respectful and inclusive. Use local terms or translations where needed. Assume no prior knowledge of trade. Make the user feel confident and capable.

You are a patient, smart, and kind assistant. Your job is not just to inform—but to **empower**.
"""


    OPENROUTER_API_KEY = ""
    OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

    def post(self, request):
        serializer = ChatPromptSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        prompt = serializer.validated_data.get("prompt")
        session_id = serializer.validated_data.get("session_id", None)
        user = request.user

        if session_id:
            try:
                chat_session = ChatSession.objects.get(session_id=session_id, user=user)
            except ChatSession.DoesNotExist:
                return Response({"error": "Chat session not found."}, status=status.HTTP_404_NOT_FOUND)
        else:
            chat_session = ChatSession.objects.create(user=user)

        # Save user message
        ChatMessage.objects.create(chat_session=chat_session, role='user', content=prompt)

        # Build messages list for API call
        messages = [{"role": "system", "content": self.system_prompt}]
        previous_messages = chat_session.messages.order_by('timestamp')
        for msg in previous_messages:
            messages.append({"role": msg.role, "content": msg.content})

        payload = {
            "model": "deepseek/deepseek-r1:free",
            "messages": messages,
            "stream": False
        }

        headers = {
            "Authorization": f"Bearer {self.OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(self.OPENROUTER_URL, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            assistant_reply = data["choices"][0]["message"]["content"]

            # Save assistant reply
            ChatMessage.objects.create(chat_session=chat_session, role='assistant', content=assistant_reply)

            return Response({
                "reply": assistant_reply,
                "session_id": str(chat_session.session_id)
            })
        except requests.RequestException as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ChatSessionListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        chat_sessions = ChatSession.objects.filter(user=user).order_by('-updated_at')
        serializer = ChatSessionSerializer(chat_sessions, many=True)
        return Response(serializer.data)