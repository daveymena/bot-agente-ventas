"""
Modelos de datos para mensajes de WhatsApp
"""
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

@dataclass
class WhatsAppMessage:
    """Representa un mensaje de WhatsApp"""
    message_id: str
    chat_id: str
    content: str
    user_name: str
    message_type: str = "text"
    timestamp: Optional[datetime] = None
    server_url: Optional[str] = None
    instance_name: Optional[str] = None
    api_key: Optional[str] = None

    @classmethod
    def from_webhook_data(cls, data: Dict[str, Any]) -> 'WhatsAppMessage':
        """Crear instancia desde datos del webhook"""
        # Extraer datos básicos
        server_url = (
            data.get('body', {}).get('URL del servidor') or
            data.get('body', {}).get('server_url') or
            data.get('URL del servidor') or
            data.get('server_url') or
            ''
        )

        instance_name = (
            data.get('body', {}).get('nombreInstancia') or
            data.get('body', {}).get('instance') or
            data.get('body', {}).get('instancia') or
            data.get('nombreInstancia') or
            data.get('instance') or
            ''
        )

        api_key = (
            data.get('body', {}).get('clave API') or
            data.get('body', {}).get('apikey') or
            data.get('body', {}).get('apikey') or
            data.get('clave API') or
            data.get('apikey') or
            ''
        )

        # Extraer datos del mensaje
        message_id = (
            data.get('body', {}).get('data', {}).get('identificación') or
            data.get('body', {}).get('data', {}).get('id') or
            data.get('body', {}).get('data', {}).get('ID del mensaje') or
            data.get('data', {}).get('identificación') or
            data.get('data', {}).get('id') or
            ''
        )

        chat_id = (
            data.get('body', {}).get('data', {}).get('Jid remoto') or
            data.get('body', {}).get('data', {}).get('remoteJid') or
            data.get('body', {}).get('data', {}).get('ID de chat') or
            data.get('data', {}).get('Jid remoto') or
            data.get('data', {}).get('remoteJid') or
            ''
        )

        content = (
            data.get('body', {}).get('data', {}).get('mensaje', {}).get('conversación') or
            data.get('body', {}).get('data', {}).get('mensaje', {}).get('text') or
            data.get('body', {}).get('data', {}).get('contenido') or
            data.get('body', {}).get('data', {}).get('message', {}).get('conversation') or
            data.get('body', {}).get('data', {}).get('message', {}).get('text') or
            data.get('data', {}).get('mensaje', {}).get('conversación') or
            data.get('data', {}).get('mensaje', {}).get('text') or
            data.get('data', {}).get('contenido') or
            data.get('data', {}).get('message', {}).get('conversation') or
            data.get('data', {}).get('message', {}).get('text') or
            ''
        )

        user_name = (
            data.get('body', {}).get('data', {}).get('nombrePush') or
            data.get('body', {}).get('data', {}).get('pushName') or
            data.get('body', {}).get('data', {}).get('notifyName') or
            data.get('body', {}).get('data', {}).get('nombre de usuario') or
            data.get('data', {}).get('nombrePush') or
            'Cliente'
        )

        # Determinar tipo de mensaje
        message_type = (
            'conversación' if data.get('body', {}).get('data', {}).get('tipo de mensaje') == 'conversación'
            else 'texto' if data.get('body', {}).get('data', {}).get('tipo de mensaje') == 'texto'
            else data.get('body', {}).get('data', {}).get('messageType') or
            data.get('body', {}).get('data', {}).get('type') or
            'text'
        )

        return cls(
            message_id=message_id,
            chat_id=chat_id,
            content=content,
            user_name=user_name,
            message_type=message_type,
            server_url=server_url,
            instance_name=instance_name,
            api_key=api_key
        )

    def is_valid(self) -> bool:
        """Validar que el mensaje tenga los datos necesarios"""
        return bool(self.content and self.chat_id)

    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario"""
        return {
            'message_id': self.message_id,
            'chat_id': self.chat_id,
            'content': self.content,
            'user_name': self.user_name,
            'message_type': self.message_type,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'server_url': self.server_url,
            'instance_name': self.instance_name,
            'api_key': self.api_key
        }