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
    function renderMessage(data) {
        if (!messageList || !data) return;

        messageList.querySelector(".empty-messages")?.remove();

        const message = document.createElement("div");

        message.classList.add(
            "message",
            data.is_mine ? "sent" : "received"
        );

        const paragraph = document.createElement("p");
        paragraph.textContent = data.content;

        const time = document.createElement("small");
        time.textContent = data.created_at || "";

        message.append(paragraph, time);
        messageList.appendChild(message);

        initializeMessageScroll();
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