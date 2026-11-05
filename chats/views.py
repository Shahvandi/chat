import uuid
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Conversation, ConversationMember, Message


User = get_user_model()


@login_required
def chat_page(request, conversation_id=None):

    # دریافت گفتگوهایی که کاربر عضو آن‌هاست
    memberships = (
        ConversationMember.objects
        .filter(user=request.user)
        .select_related('conversation')
        .prefetch_related('conversation__members__user')
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
        if selected_membership else None
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

    users = User.objects.filter(
        is_active=True
    ).order_by('first_name', 'last_name')

    return render(request, 'chats/chat.html', {
        'memberships': memberships,
        'selected_membership': selected_membership,
        'selected_conversation': selected_conversation,
        'selected_display_title': (
            selected_membership.display_title
            if selected_membership else 'گفتگوها'
        ),
        'messages': messages,
        'users': users,
    })


def _private_conversation_key(user_a_id, user_b_id):
    """کلید مستقل از ترتیب دو کاربر؛ A-B و B-A یک کلید دارند."""
    return ':'.join(sorted((str(user_a_id), str(user_b_id))))


@login_required
@require_POST
@transaction.atomic
def create_private_conversation(request):

    contact_id = request.POST.get('contact_id', '').strip()

    if not contact_id:
        return JsonResponse({
            'success': False,
            'error': 'لطفاً مخاطب را انتخاب کنید.'
        }, status=400)

    contact = get_object_or_404(
        User,
        pk=contact_id,
        is_active=True
    )

    is_self_chat = contact.pk == request.user.pk

    key = _private_conversation_key(
        request.user.pk,
        contact.pk
    )

    member_count = 1 if is_self_chat else 2

    # جستجوی گفتگوی خصوصی قبلی
    existing_query = (
        Conversation.objects
        .filter(
            type=Conversation.ConversationType.PRIVATE
        )
        .annotate(
            member_count=Count('members', distinct=True)
        )
        .filter(member_count=member_count)
    )

    # چت با خود کاربر: فقط یک عضو دارد.
    if is_self_chat:

        existing_query = existing_query.filter(
            members__user=request.user
        )

    # چت با کاربر دیگر: دو عضو دارد.
    else:

        existing_query = (
            existing_query
            .filter(members__user=request.user)
            .filter(members__user=contact)
        )

    existing = existing_query.first()

    if existing:

        conversation = existing
        reused = True

        if is_self_chat:
            conversation.title = 'پیام‌های شخصی'

        if not conversation.private_key:
            conversation.private_key = key

        conversation.save(
            update_fields=['title', 'private_key']
        )

    else:

        conversation, created = Conversation.objects.get_or_create(
            private_key=key,
            defaults={
                'title': (
                    'پیام‌های شخصی'
                    if is_self_chat
                    else (
                        f'{contact.first_name} {contact.last_name}'.strip()
                        or contact.mobile
                    )
                ),
                'type': Conversation.ConversationType.PRIVATE,
                'created_by': request.user,
            }
        )

        reused = not created

        # عضویت سازنده
        ConversationMember.objects.get_or_create(
            conversation=conversation,
            user=request.user
        )

        # فقط اگر مخاطب شخص دیگری باشد، عضو دوم اضافه می‌شود.
        if not is_self_chat:

            ConversationMember.objects.get_or_create(
                conversation=conversation,
                user=contact
            )

        # اصلاح عنوان چت با خود
        if is_self_chat and conversation.title != 'پیام‌های شخصی':
            conversation.title = 'پیام‌های شخصی'
            conversation.save(update_fields=['title'])

    return JsonResponse({
        'success': True,
        'existing': reused,
        'conversation_id': str(conversation.pk),
        'redirect_url': reverse(
            'chats:conversation',
            args=[conversation.pk]
        ),
    })


@login_required
@require_POST
@transaction.atomic
def create_group_conversation(request):
    title = request.POST.get('title', '').strip()
    member_ids = list(dict.fromkeys(request.POST.getlist('members')))

    if not title:
        return JsonResponse({
            'success': False,
            'error': 'عنوان گروه الزامی است.'
        }, status=400)

    if len(title) > 150:
        return JsonResponse({
            'success': False,
            'error': 'عنوان گروه حداکثر ۱۵۰ کاراکتر است.'
        }, status=400)

    if not member_ids:
        return JsonResponse({
            'success': False,
            'error': 'حداقل یک عضو برای گروه انتخاب کنید.'
        }, status=400)

    selected_users = list(
        User.objects.filter(
            pk__in=member_ids,
            is_active=True
        ).exclude(pk=request.user.pk)
    )

    if len(selected_users) != len(member_ids):
        return JsonResponse({
            'success': False,
            'error': 'یک یا چند عضو انتخاب‌شده معتبر نیستند.'
        }, status=400)

    # ساخت گروه با کلید یکتای تصادفی
    conversation = Conversation.objects.create(
        title=title,
        type=Conversation.ConversationType.GROUP,
        created_by=request.user,
        private_key=f'group:{uuid.uuid4()}',
    )

    # اضافه کردن ایجادکننده گروه
    ConversationMember.objects.create(
        conversation=conversation,
        user=request.user
    )

    # اضافه کردن سایر اعضا
    ConversationMember.objects.bulk_create([
        ConversationMember(
            conversation=conversation,
            user=user
        )
        for user in selected_users
    ])

    return JsonResponse({
        'success': True,
        'conversation_id': str(conversation.pk),
        'redirect_url': reverse(
            'chats:conversation',
            args=[conversation.pk]
        ),
    })


@login_required
@require_POST
def send_message(request, conversation_id):

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

    message = Message.objects.create(
        conversation=membership.conversation,
        sender=request.user,
        content=content
    )

    Conversation.objects.filter(
        pk=conversation_id
    ).update(
        updated_at=timezone.now()
    )

    return JsonResponse({
        'success': True,
        'message': {
            'id': str(message.id),
            'content': message.content,
            'sender_id': str(request.user.pk),
            'sender_name': (
                f'{request.user.first_name} {request.user.last_name}'.strip()
                or request.user.mobile
            ),
            'created_at': timezone.localtime(
                message.created_at
            ).strftime('%H:%M'),
            'is_mine': True,
        }
    })
