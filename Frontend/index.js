import { clinicsArray, medicinesArray } from "./data.js";

const API_BASE = "/api";
const MAX_QUANTITY = 20;

const clinicsGrid = document.getElementById("clinics-grid");
const pharmacyGrid = document.getElementById("pharmacy-grid");
const bookingModal = document.getElementById("booking-modal");
const checkoutModal = document.getElementById("checkout-modal");
const bookingMessage = document.getElementById("booking-msg");
const bookingMessageText = document.getElementById("booking-msg-text");
const checkoutMessage = document.getElementById("checkout-msg");
const checkoutMessageText = document.getElementById("checkout-msg-text");
const chatPanel = document.getElementById("chat-panel");
const chatToggle = document.getElementById("chat-toggle");
const chatClose = document.getElementById("chat-close");
const chatMessages = document.getElementById("chat-messages");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const chatSend = document.getElementById("chat-send");
const chatSuggestions = document.getElementById("chat-suggestions");
const navLinks = document.getElementById("nav-links");
const mobileMenu = document.querySelector(".mobile-menu");
const dateField = document.getElementById("date-field");

const state = {
    busy: false,
    started: false,
    checkout: null,
    lastFocused: null,
};

const SUGGESTIONS = [
    "Book a dentist tomorrow at 5 pm",
    "How much is Panadol Extra?",
    "Buy two packs of Betadine",
    "What are your opening hours?",
];

function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}

function renderClinics() {
    clinicsGrid.innerHTML = clinicsArray
        .map(
            (clinic) => `
            <article class="clinic-item">
                <h3>${escapeHtml(clinic.name)}</h3>
                <p>${escapeHtml(clinic.description)}</p>
                <button type="button" data-book="${escapeHtml(clinic.name)}">Book appointment</button>
            </article>`
        )
        .join("");
}

function renderMedicines() {
    pharmacyGrid.innerHTML = medicinesArray
        .map(
            (medicine) => `
            <article class="pharmacy-item" data-medicine-card="${escapeHtml(medicine.name)}">
                <img src="${escapeHtml(medicine.img)}" class="medicine-img" alt="${escapeHtml(medicine.name)}" loading="lazy">
                <h3>${escapeHtml(medicine.name)}</h3>
                <p>${medicine.price} EGP</p>
                <button type="button" class="buy-btn" data-buymedicine="${escapeHtml(medicine.name)}">Buy now</button>
            </article>`
        )
        .join("");

    pharmacyGrid.querySelectorAll(".medicine-img").forEach((image) => {
        image.addEventListener(
            "error",
            () => {
                image.src = "images/app-logo.png";
            },
            { once: true }
        );
    });
}

function localDateString(date = new Date()) {
    const offset = date.getTimezoneOffset() * 60000;
    return new Date(date.getTime() - offset).toISOString().slice(0, 10);
}

function formatDate(value) {
    if (!value) return "the selected date";
    const parsed = new Date(`${value}T00:00:00`);
    if (Number.isNaN(parsed.getTime())) return value;
    return parsed.toLocaleDateString("en-GB", {
        weekday: "long",
        day: "numeric",
        month: "long",
        year: "numeric",
    });
}

function formatTime(value) {
    if (!value) return "the selected time";
    const [hours, minutes] = value.split(":").map(Number);
    if (Number.isNaN(hours) || Number.isNaN(minutes)) return value;
    const suffix = hours >= 12 ? "PM" : "AM";
    const hour = hours % 12 || 12;
    return `${hour}:${String(minutes).padStart(2, "0")} ${suffix}`;
}

function scrollToSection(selector) {
    const section = document.querySelector(selector);
    if (section) {
        section.scrollIntoView({ behavior: "smooth", block: "start" });
    }
}

function setModalState(modal, open) {
    if (open) {
        modal.classList.add("open");
        modal.setAttribute("aria-hidden", "false");
        document.body.classList.add("modal-open");
    } else {
        modal.classList.remove("open");
        modal.setAttribute("aria-hidden", "true");
        if (!document.querySelector(".modal.open")) {
            document.body.classList.remove("modal-open");
        }
    }
}

function openModal(modal) {
    state.lastFocused = document.activeElement;
    setModalState(modal, true);
    const focusable = modal.querySelector("input:not([readonly]), button");
    if (focusable) {
        focusable.focus();
    }
}

function closeModal(modal) {
    setModalState(modal, false);
    if (state.lastFocused && document.body.contains(state.lastFocused)) {
        state.lastFocused.focus();
    }
}

function showMessage(element) {
    element.classList.add("show");
    element.setAttribute("aria-hidden", "false");
}

function hideMessage(element) {
    element.classList.remove("show");
    element.setAttribute("aria-hidden", "true");
}

function openBooking(entities = {}) {
    document.getElementById("clinic-name-field").value = entities.clinic || "";
    document.getElementById("patient-name-field").value = entities.name || "";
    dateField.value = entities.date || "";
    dateField.min = localDateString();
    document.getElementById("time-field").value = entities.time || "";
    openModal(bookingModal);
    document.getElementById("patient-name-field").focus();
}

function openCheckout(entities = {}) {
    const requested = String(entities.medicine || "").toLowerCase();
    const medicine =
        medicinesArray.find((item) => item.name.toLowerCase() === requested) ||
        medicinesArray.find((item) => item.name.toLowerCase().includes(requested));

    if (!medicine) {
        scrollToSection("#pharmacy");
        return;
    }

    state.checkout = medicine;
    const image = document.getElementById("checkout-image");
    image.onerror = () => {
        image.src = "images/app-logo.png";
    };
    image.src = medicine.img;
    image.alt = medicine.name;

    document.getElementById("checkout-name").textContent = medicine.name;
    document.getElementById("checkout-price").textContent = `${medicine.price} EGP`;
    document.getElementById("checkout-name-input").value = entities.name || "";

    const quantity = document.getElementById("checkout-quantity");
    const requestedQuantity = Number.parseInt(entities.quantity, 10) || 1;
    quantity.value = Math.min(Math.max(requestedQuantity, 1), MAX_QUANTITY);
    updateCheckoutTotal();
    openModal(checkoutModal);
    document.getElementById("checkout-name-input").focus();
}

function updateCheckoutTotal() {
    if (!state.checkout) return;
    const quantityInput = document.getElementById("checkout-quantity");
    let quantity = Number.parseInt(quantityInput.value, 10) || 1;
    quantity = Math.min(Math.max(quantity, 1), MAX_QUANTITY);
    quantityInput.value = quantity;
    document.getElementById("checkout-total").textContent = `${state.checkout.price * quantity} EGP`;
}

function highlightMedicine(name) {
    const cards = Array.from(pharmacyGrid.querySelectorAll("[data-medicine-card]"));
    const card = cards.find((item) => item.dataset.medicineCard === name);
    if (!card) return;
    card.scrollIntoView({ behavior: "smooth", block: "center" });
    card.classList.remove("highlight");
    void card.offsetWidth;
    card.classList.add("highlight");
    window.setTimeout(() => card.classList.remove("highlight"), 1600);
}

function openChat() {
    chatPanel.hidden = false;
    chatToggle.setAttribute("aria-expanded", "true");
    if (!state.started) {
        state.started = true;
        addBotMessage(
            "Hello. I can help you find a clinic, book an appointment, check medicine prices, or answer general health questions."
        );
    }
    chatInput.focus();
    scrollChatToBottom();
}

function closeChat() {
    chatPanel.hidden = true;
    chatToggle.setAttribute("aria-expanded", "false");
    chatToggle.focus();
}

function scrollChatToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function addMessage(text, className = "bot") {
    const message = document.createElement("div");
    message.className = `msg ${className}`;
    message.textContent = text;
    chatMessages.append(message);
    scrollChatToBottom();
    return message;
}

function addBotMessage(text, intent = "", sources = []) {
    const message = addMessage(text, intent === "emergency" ? "bot emergency" : "bot");
    const safeSources = Array.isArray(sources) ? sources : [];
    const links = safeSources.filter((source) => source && /^https?:\/\//i.test(source.url || ""));

    if (links.length) {
        const wrapper = document.createElement("div");
        wrapper.className = "sources";
        links.forEach((source) => {
            const link = document.createElement("a");
            link.href = source.url;
            link.target = "_blank";
            link.rel = "noopener noreferrer";
            link.textContent = source.title || source.url;
            wrapper.append(link);
        });
        message.append(wrapper);
        scrollChatToBottom();
    }
}

function addTyping() {
    const message = document.createElement("div");
    message.className = "msg bot typing";
    message.setAttribute("aria-label", "Assistant is typing");
    for (let index = 0; index < 3; index += 1) {
        message.append(document.createElement("span"));
    }
    chatMessages.append(message);
    scrollChatToBottom();
    return message;
}

function renderSuggestions() {
    SUGGESTIONS.forEach((text) => {
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = text;
        button.addEventListener("click", () => sendMessage(text));
        chatSuggestions.append(button);
    });
}

async function sendMessage(value) {
    const message = String(value || "").trim();
    if (!message || state.busy) return;

    state.busy = true;
    chatSend.disabled = true;
    chatInput.value = "";
    addMessage(message, "user");
    const typing = addTyping();

    try {
        const response = await fetch(`${API_BASE}/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message }),
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(data.detail || "The assistant could not answer that. Please try again.");
        }
        typing.remove();
        addBotMessage(data.reply, data.intent, data.sources);
        handleIntent(data.intent, data.entities || {});
    } catch (error) {
        typing.remove();
        const text =
            error instanceof TypeError
                ? "I could not reach the server. Please check the connection and try again."
                : error.message;
        addMessage(text, "error");
    } finally {
        state.busy = false;
        chatSend.disabled = false;
        chatInput.focus();
    }
}

function handleIntent(intent, entities) {
    switch (intent) {
        case "navigate_home":
            scrollToSection("#home");
            break;
        case "navigate_clinics":
            scrollToSection("#clinics");
            break;
        case "navigate_pharmacy":
            scrollToSection("#pharmacy");
            break;
        case "navigate_contact":
            scrollToSection("#contact");
            break;
        case "book_appointment":
            if (entities.clinic) {
                openBooking(entities);
            } else {
                scrollToSection("#clinics");
            }
            break;
        case "buy_medicine":
            if (entities.medicine) {
                openCheckout(entities);
            } else {
                scrollToSection("#pharmacy");
            }
            break;
        case "price":
        case "dosage":
        case "medicine_info":
            if (entities.medicine) {
                highlightMedicine(entities.medicine);
            }
            break;
        default:
            break;
    }
}

function handleBookingSubmit(event) {
    event.preventDefault();
    if (!bookingModal.reportValidity()) return;

    const clinic = document.getElementById("clinic-name-field").value;
    const name = document.getElementById("patient-name-field").value.trim();
    const date = dateField.value;
    const time = document.getElementById("time-field").value;

    bookingMessageText.textContent = `Thank you, ${name}. Your appointment at ${clinic} is booked for ${formatDate(
        date
    )} at ${formatTime(time)}. This is a demo confirmation.`;

    bookingModal.reset();
    closeModal(bookingModal);
    showMessage(bookingMessage);
}

function handleCheckoutSubmit(event) {
    event.preventDefault();
    if (!checkoutModal.reportValidity() || !state.checkout) return;

    const quantity = document.getElementById("checkout-quantity").value;
    const name = document.getElementById("checkout-name-input").value.trim();
    const address = document.getElementById("checkout-address").value.trim();
    const total = state.checkout.price * Number(quantity);
    const orderId = `MC-${String(Date.now()).slice(-6)}`;

    checkoutMessageText.textContent = `Demo order ${orderId} confirmed for ${quantity} x ${state.checkout.name}, total ${total} EGP. Delivery for ${name} to ${address}. No payment was collected.`;

    checkoutModal.reset();
    state.checkout = null;
    closeModal(checkoutModal);
    showMessage(checkoutMessage);
}

function handleDocumentClick(event) {
    const openChatButton = event.target.closest("[data-open-chat]");
    if (openChatButton) {
        event.preventDefault();
        openChat();
        return;
    }

    const bookButton = event.target.closest("[data-book]");
    if (bookButton) {
        openBooking({ clinic: bookButton.dataset.book });
        return;
    }

    const buyButton = event.target.closest("[data-buymedicine]");
    if (buyButton) {
        openCheckout({ medicine: buyButton.dataset.buymedicine });
        return;
    }

    const closeButton = event.target.closest("[data-close-modal]");
    if (closeButton) {
        const target = closeButton.dataset.closeModal;
        if (target === "booking") closeModal(bookingModal);
        if (target === "checkout") closeModal(checkoutModal);
        if (target === "message") {
            hideMessage(bookingMessage);
            hideMessage(checkoutMessage);
        }
    }
}

function handleBackdropPress(event) {
    [bookingModal, checkoutModal].forEach((modal) => {
        if (modal.classList.contains("open") && !modal.contains(event.target)) {
            closeModal(modal);
        }
    });

    [bookingMessage, checkoutMessage].forEach((message) => {
        if (message.classList.contains("show") && !message.contains(event.target)) {
            hideMessage(message);
        }
    });
}

function handleKeydown(event) {
    if (event.key === "Escape") {
        const openModalElement = document.querySelector(".modal.open");
        if (openModalElement) {
            closeModal(openModalElement);
            return;
        }
        if (!chatPanel.hidden) {
            closeChat();
        }
        hideMessage(bookingMessage);
        hideMessage(checkoutMessage);
    }

    if (event.key !== "Tab") return;
    const modal = document.querySelector(".modal.open");
    if (!modal) return;

    const focusable = Array.from(modal.querySelectorAll("button, input, a[href]")).filter(
        (element) => !element.disabled && element.offsetParent !== null
    );
    if (!focusable.length) return;

    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
    }
}

function setupNavigation() {
    mobileMenu.addEventListener("click", () => {
        const open = navLinks.classList.toggle("open");
        mobileMenu.setAttribute("aria-expanded", String(open));
    });

    navLinks.addEventListener("click", (event) => {
        if (event.target.closest("a")) {
            navLinks.classList.remove("open");
            mobileMenu.setAttribute("aria-expanded", "false");
        }
    });
}

function setupModals() {
    [bookingModal, checkoutModal].forEach((modal) => {
        modal.setAttribute("role", "dialog");
        modal.setAttribute("aria-modal", "true");
        modal.setAttribute("aria-hidden", "true");
    });
    [bookingMessage, checkoutMessage].forEach((message) => message.setAttribute("aria-hidden", "true"));

    bookingModal.addEventListener("submit", handleBookingSubmit);
    checkoutModal.addEventListener("submit", handleCheckoutSubmit);
    document.getElementById("checkout-quantity").addEventListener("input", updateCheckoutTotal);
}

function setupChat() {
    chatToggle.addEventListener("click", () => {
        if (chatPanel.hidden) openChat();
        else closeChat();
    });
    chatClose.addEventListener("click", closeChat);
    chatForm.addEventListener("submit", (event) => {
        event.preventDefault();
        sendMessage(chatInput.value);
    });
    renderSuggestions();
}

function setupDemoLinks() {
    const params = new URLSearchParams(window.location.search);
    if (params.get("chat") === "1") openChat();
    const booking = params.get("book");
    if (booking) openBooking({ clinic: booking });
    const checkout = params.get("checkout");
    if (checkout) openCheckout({ medicine: checkout });
}

renderClinics();
renderMedicines();
setupNavigation();
setupModals();
setupChat();
setupDemoLinks();

document.addEventListener("click", handleDocumentClick);
document.addEventListener("pointerdown", handleBackdropPress);
document.addEventListener("keydown", handleKeydown);
