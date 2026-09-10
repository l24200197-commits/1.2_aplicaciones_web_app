import json
import os

from http.server import BaseHTTPRequestHandler
from openai import OpenAI


# ALLOWED_ORIGIN acepta uno o varios orígenes separados por coma, ej:
# ALLOWED_ORIGIN=https://l24200197-commits.github.io,https://12aplicacioneswebapp1.vercel.app
ALLOWED_ORIGINS = [
    origin.strip().rstrip("/")
    for origin in os.environ.get("ALLOWED_ORIGIN", "").split(",")
    if origin.strip()
]

# --- Reto 1: personalidad del asistente -----------------------------------
INSTRUCTIONS = """
Eres un asistente educativo especializado en Ciberseguridad, dirigido a
estudiantes de Tecnologías de la Información y Comunicaciones.
Responde siempre en español, de forma clara, breve y didáctica.
Cuando ayude a explicar un concepto, incluye ejemplos prácticos, buenas
prácticas o referencias a estándares reconocidos (OWASP, NIST, ISO 27001,
MITRE ATT&CK). Si te preguntan algo totalmente fuera del ámbito de TIC o
ciberseguridad, indícalo con amabilidad y redirige la conversación hacia
el tema del asistente.
"""

# --- Reto 4: límites para controlar el consumo de tokens -------------------
MAX_MESSAGE_LENGTH = 1000
MAX_HISTORY_MESSAGES = 10  # 5 intercambios usuario/asistente como máximo
MAX_BODY_BYTES = 20000     # más margen porque ahora también viaja el historial


class handler(BaseHTTPRequestHandler):

    def add_cors_headers(self):
        origin = self.headers.get("Origin", "")

        if origin in ALLOWED_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")

    def send_json(self, status_code, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")

        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.add_cors_headers()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()

        self.wfile.write(body)

    def do_OPTIONS(self):
        origin = self.headers.get("Origin", "")

        if ALLOWED_ORIGINS and origin not in ALLOWED_ORIGINS:
            self.send_response(403)
            self.end_headers()
            return

        self.send_response(204)
        self.add_cors_headers()
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()

    def do_GET(self):
        self.send_json(
            405,
            {"error": "Este endpoint solamente acepta POST."}
        )

    def _sanear_historial(self, history_raw):
        """Reto 4: valida y recorta el historial recibido del cliente.

        Nunca confiamos en lo que manda el navegador: se limita el número
        de turnos y la longitud de cada mensaje, sin importar lo que el
        cliente haya enviado, para controlar el consumo de tokens.
        """
        if not isinstance(history_raw, list):
            return []

        historial = []
        for item in history_raw[-MAX_HISTORY_MESSAGES:]:
            if not isinstance(item, dict):
                continue

            role = item.get("role")
            content = str(item.get("content", "")).strip()

            if role not in ("user", "assistant") or not content:
                continue

            historial.append({
                "role": role,
                "content": content[:MAX_MESSAGE_LENGTH]
            })

        return historial

    def do_POST(self):
        try:
            origin = self.headers.get("Origin", "")

            if ALLOWED_ORIGINS and origin not in ALLOWED_ORIGINS:
                self.send_json(403, {"error": "Origen no autorizado."})
                return

            content_length = int(self.headers.get("Content-Length", 0))

            if content_length <= 0 or content_length > MAX_BODY_BYTES:
                self.send_json(
                    413,
                    {"error": "Petición no válida o demasiado grande."}
                )
                return

            body = self.rfile.read(content_length)
            data = json.loads(body.decode("utf-8"))

            message = str(data.get("message", "")).strip()

            if not message:
                self.send_json(
                    400,
                    {"error": "Es necesario escribir un mensaje."}
                )
                return

            if len(message) > MAX_MESSAGE_LENGTH:
                self.send_json(
                    400,
                    {"error": f"El mensaje supera los {MAX_MESSAGE_LENGTH} caracteres."}
                )
                return

            api_key = os.environ.get("OPENAI_API_KEY")

            if not api_key:
                self.send_json(
                    500,
                    {"error": "OPENAI_API_KEY no está configurada."}
                )
                return

            # Reto 4: se arma el input con historial + mensaje nuevo
            historial = self._sanear_historial(data.get("history", []))
            input_items = historial + [{"role": "user", "content": message}]

            client = OpenAI(api_key=api_key)

            response = client.responses.create(
                model="gpt-5.6-luna",
                instructions=INSTRUCTIONS,
                input=input_items,
                reasoning={"effort": "none"},
                max_output_tokens=500
            )

            self.send_json(200, {"reply": response.output_text})

        except json.JSONDecodeError:
            self.send_json(400, {"error": "El cuerpo no contiene JSON válido."})

        except Exception as error:
            print(f"Error en /api/chat: {type(error).__name__}: {error}")
            self.send_json(
                500,
                {"error": "No fue posible consultar el modelo de IA."}
            )