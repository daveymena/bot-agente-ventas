import requests
import time

def send_test_webhook():
    url = "http://192.168.18.69:8000/webhook"
    # Usar timestamp para ID único, contenido único y chat único
    timestamp = int(time.time())
    message_id = f"test_message_{timestamp}"
    chat_id = f"{timestamp}@c.us"
    content = f"Hola, ¿qué productos tienes? {timestamp}"
    payload = {
        "body": {
            "data": {
                "id": message_id,
                "remoteJid": chat_id,
                "message": {
                    "conversation": content
                },
                "pushName": "Cliente de Prueba",
                "tipo de mensaje": "conversación"
            }
        }
    }
    headers = {"Content-Type": "application/json"}

    response = requests.post(url, json=payload, headers=headers)
    print(f"Status code: {response.status_code}")
    print(f"Response: {response.text}")

if __name__ == "__main__":
    send_test_webhook()
