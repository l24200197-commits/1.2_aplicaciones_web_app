const API_URL = "https://12aplicacioneswebapp1.vercel.app/api/chat";
const MAX_MESSAGE_LENGTH = 1000;
const MAX_HISTORY_MESSAGES = 10; // 5 intercambios usuario/asistente

const SALUDO_INICIAL =
    "Hola, soy tu asistente de Inteligencia Artificial especializado " +
    "en Ciberseguridad. ¿En qué puedo ayudarte?";

// Reto 5: un mensaje distinto según el código de estado HTTP
const MENSAJES_ERROR = {
    400: "Tu mensaje no es válido: revisa que no esté vacío ni exceda el límite de caracteres.",
    403: "Este sitio no está autorizado para usar el asistente (origen no permitido).",
    413: "El mensaje (o el historial) es demasiado grande para procesarse.",
    500: "Ocurrió un error en el servidor de IA. Intenta de nuevo en unos segundos."
};

const form = document.getElementById("chatForm");
const input = document.getElementById("messageInput");
const messages = document.getElementById("messages");
const sendButton = document.getElementById("sendButton");
const charCounter = document.getElementById("charCounter");
const newChatButton = document.getElementById("newChatButton");

// Reto 4: historial de la conversación (se envía al backend en cada turno)
let conversationHistory = [];

function addMessage(text, type) {
    const container = document.createElement("div");
    container.classList.add("message", type);

    const label = document.createElement("div");
    label.classList.add("message-label");
    label.textContent = type === "user" ? "Tú" : "IA";

    const content = document.createElement("div");
    content.classList.add("message-content");
    content.textContent = text;

    container.appendChild(label);
    container.appendChild(content);
    messages.appendChild(container);

    messages.scrollTop = messages.scrollHeight;

    return container;
}

// Reto 2: contador de caracteres, actualizado con el evento "input"
function actualizarContador() {
    if (!charCounter) {
        return;
    }

    const longitud = input.value.length;
    charCounter.textContent = `${longitud} / ${MAX_MESSAGE_LENGTH}`;
    charCounter.classList.toggle(
        "char-counter--limite",
        longitud > MAX_MESSAGE_LENGTH
    );
}

// Reto 3: nueva conversación (limpia mensajes, historial y saludo inicial)
function iniciarNuevaConversacion() {
    messages.innerHTML = "";
    conversationHistory = [];
    addMessage(SALUDO_INICIAL, "assistant");
    input.value = "";
    actualizarContador();
    input.focus();
}

if (input) {
    input.addEventListener("input", actualizarContador);
}

if (newChatButton) {
    newChatButton.addEventListener("click", iniciarNuevaConversacion);
}

form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const message = input.value.trim();

    if (!message) {
        return;
    }

    if (message.length > MAX_MESSAGE_LENGTH) {
        addMessage(
            `Tu mensaje supera el límite de ${MAX_MESSAGE_LENGTH} caracteres.`,
            "assistant"
        );
        return;
    }

    addMessage(message, "user");

    input.value = "";
    actualizarContador();
    input.disabled = true;
    sendButton.disabled = true;

    const loading = addMessage("Pensando...", "loading");

    try {
        const response = await fetch(API_URL, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                message: message,
                history: conversationHistory // Reto 4
            })
        });

        const data = await response.json();

        loading.remove();

        if (!response.ok) {
            // Reto 5: mensaje específico según el código de estado
            const mensaje =
                MENSAJES_ERROR[response.status] ||
                data.error ||
                "Error del servidor.";
            throw new Error(mensaje);
        }

        addMessage(data.reply, "assistant");

        // Reto 4: actualiza el historial y lo recorta para no crecer sin límite
        conversationHistory.push({ role: "user", content: message });
        conversationHistory.push({ role: "assistant", content: data.reply });

        if (conversationHistory.length > MAX_HISTORY_MESSAGES) {
            conversationHistory =
                conversationHistory.slice(-MAX_HISTORY_MESSAGES);
        }
    }
    catch (error) {
        loading.remove();
        addMessage("Error: " + error.message, "assistant");
    }
    finally {
        input.disabled = false;
        sendButton.disabled = false;
        input.focus();
    }
});

actualizarContador();
addMessage(SALUDO_INICIAL, "assistant");