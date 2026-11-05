from django.urls import path
from . import views

app_name = 'chats'

urlpatterns = [
    path('', views.chat_page, name='chat_page'),
    path('create/private/', views.create_private_conversation, name='create_private_conversation'),
    path('create/group/', views.create_group_conversation, name='create_group_conversation'),
    path('<uuid:conversation_id>/', views.chat_page, name='conversation'),
    path('<uuid:conversation_id>/send/', views.send_message, name='send_message'),
]
