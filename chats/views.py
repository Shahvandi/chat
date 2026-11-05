from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.db import transaction
from django.shortcuts import redirect

from .models import Conversation, ConversationMember, Message


@login_required
def chat_page(request, conversation_id=None):

    # دریافت گفتگوهایی که کاربر عضو آن‌هاست
    memberships = (
        ConversationMember.objects
        .filter(user=request.user)
        .select_related('conversation')
        .order_by('-conversation__updated_at')
    )

    selected_membership = memberships.first()

    if conversation_id:
        selected_membership = get_object_or_404(
            memberships,
            conversation_id=conversation_id
        )

    selected_conversation = (
        selected_membership.conversation
        if selected_membership
        else None
    )

    # دریافت پیام‌های گفتگوی انتخاب‌شده
    messages = []

    if selected_conversation:
        messages = (
            Message.objects
            .filter(conversation=selected_conversation)
            .select_related('sender')
            .order_by('created_at')
        )

    context = {
        'memberships': memberships,
        'selected_membership': selected_membership,
        'selected_conversation': selected_conversation,
        'messages': messages,
    }

    return render(request, 'chats/chat.html', context)


@transaction.atomic
def create_conversation(request, title, contact=None):

    conversation_type = "GROUP" if contact is None else "PRIVATE"

    conversation = Conversation.objects.create(
        title=title,
        type=conversation_type,
        created_by=request.user,
    )

    ConversationMember.objects.create(
        conversation=conversation,
        user=request.user,
    )

    if contact:
        ConversationMember.objects.create(
            conversation=conversation,
            user=contact,
        )

    return redirect(
        "chats:chat_page",
        conversation_id=conversation.id
    )

@login_required
@require_POST
def send_message(request, conversation_id):

    # بررسی عضویت کاربر در گفتگو
    membership = get_object_or_404(
        ConversationMember.objects.select_related('conversation'),
        conversation_id=conversation_id,
        user=request.user
    )

    content = request.POST.get('content', '').strip()

    if not content:
        return JsonResponse({
            'success': False,
            'error': 'متن پیام نمی‌تواند خالی باشد.'
        }, status=400)

    # ذخیره پیام
    message = Message.objects.create(
        conversation=membership.conversation,
        sender=request.user,
        content=content
    )

    # به‌روزرسانی زمان آخرین فعالیت
    Conversation.objects.filter(
        pk=conversation_id
    ).update(updated_at=timezone.now())

    return JsonResponse({
        'success': True,
        'message': {
            'id': str(message.id),
            'content': message.content,
            'sender_id': str(request.user.pk),
            'sender_name': f"{request.user.first_name} {request.user.last_name}".strip(),
            'created_at': timezone.localtime(
                message.created_at
            ).strftime('%H:%M'),
            'is_mine': True,
        }
    })
