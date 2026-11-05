document.addEventListener("DOMContentLoaded", () => {

    // ==============================
    // DOM Elements
    // ==============================

    const chatApp = document.getElementById("chatApp");
    const chatItems = document.querySelectorAll(".chat-item");

    const headerName = document.getElementById("headerName");
    const headerAvatar = document.getElementById("headerAvatar");
    const headerStatus = document.getElementById("headerStatus");

    const backBtn = document.getElementById("backBtn");

    const messageInput = document.getElementById("messageInput");
    const sendBtn = document.getElementById("sendBtn");
    const messageList = document.getElementById("messageList");

    const chatSearch = document.getElementById("chatSearch");

    // Conversation ID
    let conversationId =
        chatApp?.dataset.conversationId ||
        document.querySelector(".chat-item.active")?.dataset.conversationId ||
        null;

    let isSending = false;


    // ==============================
    // CSRF Token
    // ==============================

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
            document.querySelector(
                '[name="csrfmiddlewaretoken"]'
            )?.value ||
            ""
        );
    }


    // ==============================
    // Scroll To Bottom
    // ==============================

    function scrollToBottom() {
        if (!messageList) return;

        messageList.scrollTop = messageList.scrollHeight;
    }


    // ==============================
    // Render Message
    // ==============================

    function renderMessage(data) {

        const message = document.createElement("div");

        message.classList.add(
            "message",
            data.is_mine ? "sent" : "received"
        );

        const paragraph = document.createElement("p");

        paragraph.textContent = data.content;

        const time = document.createElement("small");

        time.textContent = data.created_at;

        message.appendChild(paragraph);
        message.appendChild(time);

        messageList.appendChild(message);

        scrollToBottom();
    }


    // ==============================
    // Select Chat
    // ==============================

    chatItems.forEach(item => {

        item.addEventListener("click", () => {

            chatItems.forEach(chat => {
                chat.classList.remove("active");
            });

            item.classList.add("active");

            conversationId = item.dataset.conversationId || null;

            if (chatApp) {
                chatApp.dataset.conversationId = conversationId || "";
                chatApp.classList.add("chat-open");
            }

            if (headerName) {
                headerName.textContent = item.dataset.name || "";
            }

            if (headerAvatar) {
                headerAvatar.textContent = item.dataset.avatar || "";
            }

            if (headerStatus) {
                headerStatus.textContent = item.dataset.status || "";
            }

        });

    });


    // ==============================
    // Back Button
    // ==============================

    if (backBtn) {

        backBtn.addEventListener("click", () => {

            chatApp?.classList.remove("chat-open");

        });

    }


    // ==============================
    // Send Message - Django API
    // ==============================

    async function sendMessage() {

        const content = messageInput?.value.trim();

        if (!content || isSending) {
            return;
        }

        if (!conversationId) {

            alert("لطفاً ابتدا یک گفتگو انتخاب کنید.");

            return;
        }

        isSending = true;

        if (sendBtn) {
            sendBtn.disabled = true;
        }

        try {

            const response = await fetch(
                chatApp.dataset.sendUrl,
                {
                    method: "POST",

                    headers: {
                        "Content-Type": "application/x-www-form-urlencoded",
                        "X-CSRFToken": getCsrfToken(),
                        "X-Requested-With": "XMLHttpRequest"
                    },

                    credentials: "same-origin",

                    body: new URLSearchParams({
                        content: content
                    })
                }
            );

            const data = await response.json();

            if (!response.ok || !data.success) {

                throw new Error(
                    data.error || "ارسال پیام با خطا مواجه شد."
                );
            }

            // Add message after successful database save
            renderMessage(data.message);

            // Clear input
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


    // ==============================
    // Send Button
    // ==============================

    if (sendBtn) {

        sendBtn.addEventListener("click", sendMessage);

    }


    // ==============================
    // Enter Key
    // ==============================

    if (messageInput) {

        messageInput.addEventListener("keydown", event => {

            if (event.key === "Enter" && !event.shiftKey) {

                event.preventDefault();

                sendMessage();

            }

        });

    }


    // ==============================
    // Search Chats
    // ==============================

    if (chatSearch) {

        chatSearch.addEventListener("input", () => {

            const query = chatSearch.value.trim().toLowerCase();

            chatItems.forEach(item => {

                const name = (
                    item.dataset.name || ""
                ).toLowerCase();

                item.style.display = name.includes(query)
                    ? "flex"
                    : "none";

            });

        });

    }


    // ==============================
    // Initial Scroll
    // ==============================

    // بعد از بارگذاری کامل صفحه، نمایش آخرین پیام
    window.addEventListener("load", () => {
        requestAnimationFrame(() => {
            scrollToBottom();
        });
    });

});