from django.urls import path
from .views import RegistrationView, LoginView, UserInfoView, WalletInfoView, DepositView, TransferView, TransactionListView, TransactionDetailView, ChatBotView, ChatSessionListView

urlpatterns = [
    path('register/', RegistrationView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('user-info/', UserInfoView.as_view(), name='user-info'),
    path('wallet/', WalletInfoView.as_view(), name='wallet-info'),
    path('wallet/deposit/', DepositView.as_view(), name='wallet-deposit'),
    path('wallet/transfer/', TransferView.as_view(), name='wallet-transfer'),
    path('wallet/transactions/', TransactionListView.as_view(), name='wallet-transactions'),
    path('wallet/transactions/<uuid:transaction_id>/', TransactionDetailView.as_view(), name='wallet-transaction-detail'),
    path('chatbot/', ChatBotView.as_view(), name='chatbot'),
    path('chatbot/sessions/', ChatSessionListView.as_view(), name='chatbot-sessions'),


]
