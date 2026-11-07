document.addEventListener("DOMContentLoaded", () => {

    // Elements
    const chatApp = document.getElementById("chatApp");
    const messageList = document.getElementById("messageList");
    const messageInput = document.getElementById("messageInput");
    const sendBtn = document.getElementById("sendBtn");
    const chatSearch = document.getElementById("chatSearch");
    const backBtn = document.getElementById("backBtn");

    const chatItems = document.querySelectorAll(".chat-item");

    let conversationId = chatApp?.dataset.conversationId || null;
    let isSending = false;


    // ==============================
    // WebSocket - Online / Offline
    // ==============================

    const headerStatus = document.getElementById("headerStatus");

    const peerUserId = chatApp?.dataset.peerUserId || null;

    const isSelfChat = !peerUserId;

    if (isSelfChat && headerStatus) {
        headerStatus.hidden = true;
    }

    let presenceSocket = null;
    let reconnectTimer = null;

    function updatePresence(userId, isOnline) {

        // Update sidebar presence dots
        document.querySelectorAll("[data-presence-user-id]")
            .forEach(dot => {

                if (dot.dataset.presenceUserId === userId) {
                    dot.classList.toggle("is-online", isOnline);
                }

            });

        // Update selected conversation header
        if (!isSelfChat && peerUserId === userId && headerStatus) {

            headerStatus.textContent = isOnline
                ? "آنلاین"
                : "آفلاین";

            headerStatus.classList.toggle(
                "is-online",
                isOnline
            );
        }
    }

    function connectPresence() {

        if (
            presenceSocket &&
            (
                presenceSocket.readyState === WebSocket.OPEN ||
                presenceSocket.readyState === WebSocket.CONNECTING
            )
        ) {
            return;
        }

        const protocol = window.location.protocol === "https:"
            ? "wss:"
            : "ws:";

        const socketUrl =
            `${protocol}//${window.location.host}/ws/presence/`;

        presenceSocket = new WebSocket(socketUrl);

        presenceSocket.onopen = () => {

            console.log("Presence WebSocket Connected");

            if (reconnectTimer) {
                clearTimeout(reconnectTimer);
                reconnectTimer = null;
            }
        };

        presenceSocket.onmessage = event => {

            const data = JSON.parse(event.data);

            // دریافت پیام جدید
            if (data.type === "chat.message") {

                handleIncomingChatMessage(data.message);

                return;
            }

            // Initial online users
            if (data.type === "presence.snapshot") {

                // ابتدا همه کاربران را Offline فرض می‌کنیم
                document.querySelectorAll("[data-presence-user-id]")
                    .forEach(dot => {
                        dot.classList.remove("is-online");
                    });

                if (!isSelfChat && headerStatus) {
                    headerStatus.textContent = "آفلاین";
                    headerStatus.classList.remove("is-online");
                }

                data.users.forEach(user => {
                    updatePresence(user.user_id, true);
                });

                return;
            }

            // Online / Offline event
            if (data.type === "presence.update") {

                updatePresence(
                    data.user_id,
                    data.is_online
                );
            }
        };

        presenceSocket.onerror = error => {

            console.error("Presence WebSocket Error:", error);

            presenceSocket.close();
        };

        presenceSocket.onclose = () => {

            console.log("Presence WebSocket Disconnected");

            if (headerStatus) {
                headerStatus.textContent = "اتصال قطع شد";
                headerStatus.classList.remove("is-online");
            }

            reconnectTimer = setTimeout(() => {
                connectPresence();
            }, 3000);
        };
    }

    connectPresence();

    // CSRF
    function getCookie(name) {
        const cookies = document.cookie.split(";");

        for (let cookie of cookies) {
            cookie = cookie.trim();

            if (cookie.startsWith(name + "=")) {
                return decodeURIComponent(
                    cookie.substring(name.length + 1)
                );
            }
        }

        return null;
    }

    function getCsrfToken() {
        return (
            getCookie("csrftoken") ||
            document.querySelector('[name="csrfmiddlewaretoken"]')?.value ||
            ""
        );
    }

    // Scroll
    function scrollToBottom() {
        if (!messageList) return;

        messageList.scrollTop = messageList.scrollHeight;
    }

    function initializeMessageScroll() {
        if (!messageList) return;

        requestAnimationFrame(() => {
            requestAnimationFrame(scrollToBottom);
        });
    }

    // Render Message
    // جلوگیری از نمایش دوباره پیام دریافتی از HTTP و WebSocket
    function renderMessage(data) {

        if (!messageList || !data) return;

        // بررسی پیام تکراری
        if (
            data.id &&
            Array.from(messageList.children).some(
                item => item.dataset.messageId === String(data.id)
            )
        ) {
            return;
        }

        messageList.querySelector(".empty-messages")?.remove();

        const currentUserId = String(
            chatApp?.dataset.userId || ""
        );

        const isMine = data.is_mine !== undefined
            ? data.is_mine
            : String(data.sender_id) === currentUserId;

        const message = document.createElement("div");

        message.classList.add(
            "message",
            isMine ? "sent" : "received"
        );

        if (data.id) {
            message.dataset.messageId = String(data.id);
        }

        // نام فرستنده در پیام‌های دریافتی
        if (!isMine && data.sender_name) {

            const sender = document.createElement("div");

            sender.className = "message-sender";
            sender.textContent = data.sender_name;

            message.appendChild(sender);
        }

        const paragraph = document.createElement("p");

        paragraph.textContent = data.content;

        const time = document.createElement("small");

        time.textContent = data.created_at || "";

        message.append(paragraph, time);

        messageList.appendChild(message);

        initializeMessageScroll();
    }

    // به‌روزرسانی پیش‌نمایش گفتگو در Sidebar
    function updateConversationPreview(data) {

        const item = Array.from(
            document.querySelectorAll(".chat-item")
        ).find(element =>
            element.dataset.conversationId ===
            String(data.conversation_id)
        );

        if (!item) return;

        const preview = item.querySelector(
            ".chat-bottom span"
        );

        const time = item.querySelector(
            ".chat-top small"
        );

        if (preview) {
            preview.textContent = data.content || "";
        }

        if (time) {
            time.textContent = data.created_at || "";
        }

        // انتقال گفتگو به ابتدای فهرست
        if (item.parentElement) {
            item.parentElement.insertBefore(
                item,
                item.parentElement.firstChild
            );
        }
    }

    // نمایش اعلان Toast
    function showMessageToast(data) {

        if (!window.bootstrap?.Toast) return;

        let container = document.getElementById(
            "messageToastContainer"
        );

        if (!container) {

            container = document.createElement("div");

            container.id = "messageToastContainer";

            container.className =
                "toast-container position-fixed bottom-0 start-0 p-3";

            container.style.zIndex = "1080";

            document.body.appendChild(container);
        }

        const toastElement = document.createElement("div");

        toastElement.className = "toast";

        toastElement.setAttribute("role", "status");

        toastElement.setAttribute("aria-live", "polite");

        // Header
        const header = document.createElement("div");

        header.className = "toast-header";

        const title = document.createElement("strong");

        title.className = "me-auto";

        const conversationItem = Array.from(
            document.querySelectorAll(".chat-item")
        ).find(item =>
            item.dataset.conversationId ===
            String(data.conversation_id)
        );

        title.textContent =
            conversationItem?.dataset.name || "پیام جدید";

        const close = document.createElement("button");

        close.type = "button";

        close.className = "btn-close";

        close.setAttribute("data-bs-dismiss", "toast");

        close.setAttribute("aria-label", "بستن");

        header.append(title, close);

        // Body
        const body = document.createElement("div");

        body.className = "toast-body";

        body.textContent =
            `${data.sender_name || "کاربر"}: ${data.content || ""}`;

        body.style.cursor = "pointer";

        body.addEventListener("click", () => {

            const target = Array.from(
                document.querySelectorAll(".chat-item")
            ).find(item =>
                item.dataset.conversationId ===
                String(data.conversation_id)
            );

            if (
                target &&
                String(data.conversation_id) !==
                String(conversationId)
            ) {
                window.location.href = target.href;
            }
        });

        toastElement.append(header, body);

        container.appendChild(toastElement);

        const toast = new bootstrap.Toast(
            toastElement,
            { delay: 5000 }
        );

        toast.show();

        toastElement.addEventListener(
            "hidden.bs.toast",
            () => toastElement.remove()
        );
    }

    // مدیریت پیام دریافتی
    function handleIncomingChatMessage(data) {

        if (!data) return;

        // به‌روزرسانی Sidebar
        updateConversationPreview(data);

        // اگر کاربر در همین گفتگو باشد
        if (
            String(data.conversation_id) ===
            String(conversationId)
        ) {

            renderMessage(data);

            return;
        }

        // جلوگیری از اعلان برای پیام خود کاربر
        const currentUserId = String(
            chatApp?.dataset.userId || ""
        );

        if (String(data.sender_id) !== currentUserId) {

            showMessageToast(data);
        }
    }

    // Back Button
    backBtn?.addEventListener("click", () => {
        chatApp?.classList.remove("conversation-open");
    });

    // Send Message
    async function sendMessage() {
        const content = messageInput?.value.trim();

        if (!content || isSending) return;

        if (!conversationId || !chatApp?.dataset.sendUrl) {
            alert("لطفاً ابتدا یک گفتگو انتخاب کنید.");
            return;
        }

        isSending = true;

        if (sendBtn) {
            sendBtn.disabled = true;
        }

        try {
            const response = await fetch(chatApp.dataset.sendUrl, {
                method: "POST",
                headers: {
                    "Content-Type": "application/x-www-form-urlencoded",
                    "X-CSRFToken": getCsrfToken(),
                    "X-Requested-With": "XMLHttpRequest"
                },
                credentials: "same-origin",
                body: new URLSearchParams({content})
            });

            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error(
                    data.error || "ارسال پیام با خطا مواجه شد."
                );
            }

            renderMessage(data.message);

            messageInput.value = "";
            messageInput.focus();

        } catch (error) {
            console.error("Send Message Error:", error);
            alert(error.message || "خطا در ارتباط با سرور.");

        } finally {
            isSending = false;

            if (sendBtn) {
                sendBtn.disabled = false;
            }
        }
    }

    sendBtn?.addEventListener("click", sendMessage);

    messageInput?.addEventListener("keydown", event => {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            sendMessage();
        }
    });

    // Search Chats
    chatSearch?.addEventListener("input", () => {
        const query = chatSearch.value.trim().toLowerCase();

        chatItems.forEach(item => {
            const name = (item.dataset.name || "").toLowerCase();

            item.style.display = name.includes(query) ? "flex" : "none";
        });
    });

    // Create Chat Forms
    function setupCreateForm({
                                 buttonId,
                                 modalId,
                                 formId,
                                 url,
                                 errorId,
                                 submitId
                             }) {
        const button = document.getElementById(buttonId);
        const modalElement = document.getElementById(modalId);
        const form = document.getElementById(formId);
        const errorBox = document.getElementById(errorId);
        const submitButton = document.getElementById(submitId);

        if (!button || !modalElement || !form) return;

        const modal = new bootstrap.Modal(modalElement);

        button.addEventListener("click", () => {
            form.reset();
            errorBox?.classList.add("d-none");
            modal.show();
        });

        form.addEventListener("submit", async event => {
            event.preventDefault();

            errorBox?.classList.add("d-none");

            const originalText = submitButton?.textContent;

            if (submitButton) {
                submitButton.disabled = true;
                submitButton.textContent = "در حال انجام...";
            }

            try {
                const response = await fetch(url, {
                    method: "POST",
                    headers: {
                        "X-CSRFToken": getCsrfToken(),
                        "X-Requested-With": "XMLHttpRequest"
                    },
                    credentials: "same-origin",
                    body: new FormData(form)
                });

                const data = await response.json();

                if (!response.ok || !data.success) {
                    throw new Error(data.error || "عملیات انجام نشد.");
                }

                if (!data.redirect_url) {
                    throw new Error("آدرس گفتگو از سرور دریافت نشد.");
                }

                window.location.href = data.redirect_url;

            } catch (error) {
                if (errorBox) {
                    errorBox.textContent = error.message;
                    errorBox.classList.remove("d-none");
                } else {
                    alert(error.message);
                }

            } finally {
                if (submitButton) {
                    submitButton.disabled = false;
                    submitButton.textContent = originalText || "ثبت";
                }
            }
        });
    }

    setupCreateForm({
        buttonId: "newPrivateChatBtn",
        modalId: "privateChatModal",
        formId: "privateChatForm",
        url: "/create/private/",
        errorId: "privateChatError",
        submitId: "privateChatSubmit"
    });

    setupCreateForm({
        buttonId: "newGroupChatBtn",
        modalId: "groupChatModal",
        formId: "groupChatForm",
        url: "/create/group/",
        errorId: "groupChatError",
        submitId: "groupChatSubmit"
    });

    // Initial Scroll
    initializeMessageScroll();
    window.addEventListener("load", initializeMessageScroll);

    // Initial Focus
    if (window.location.pathname === "/") {
        chatSearch?.focus();
    } else if (conversationId) {
        messageInput?.focus();
    } else {
        chatSearch?.focus();
    }
});