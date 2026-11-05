document.addEventListener("DOMContentLoaded", () => {

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


    // Select Chat
    chatItems.forEach(item => {

        item.addEventListener("click", () => {

            chatItems.forEach(chat => {
                chat.classList.remove("active");
            });

            item.classList.add("active");

            headerName.textContent = item.dataset.name;
            headerAvatar.textContent = item.dataset.avatar;
            headerStatus.textContent = item.dataset.status;

            chatApp.classList.add("chat-open");

        });

    });


    // Back Button
    backBtn.addEventListener("click", () => {

        chatApp.classList.remove("chat-open");

    });


    // Send Message (Frontend Demo)
    function sendMessage() {

        const text = messageInput.value.trim();

        if (!text) {
            return;
        }

        const message = document.createElement("div");
        message.classList.add("message", "sent");

        const paragraph = document.createElement("p");
        paragraph.textContent = text;

        const time = document.createElement("small");

        const now = new Date();

        time.textContent = now.toLocaleTimeString("fa-IR", {
            hour: "2-digit",
            minute: "2-digit"
        });

        message.appendChild(paragraph);
        message.appendChild(time);

        messageList.appendChild(message);

        messageInput.value = "";

        messageList.scrollTop = messageList.scrollHeight;

    }


    sendBtn.addEventListener("click", sendMessage);


    messageInput.addEventListener("keydown", event => {

        if (event.key === "Enter") {
            sendMessage();
        }

    });


    // Search Chats
    chatSearch.addEventListener("input", () => {

        const query = chatSearch.value.trim().toLowerCase();

        chatItems.forEach(item => {

            const name = item.dataset.name.toLowerCase();

            item.style.display = name.includes(query) ? "flex" : "none";

        });

    });

});