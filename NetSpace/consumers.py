import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Message, VideoCall, VoiceCall
from django.contrib.auth import get_user_model
from django.utils import timezone
from asgiref.sync import sync_to_async
from datetime import datetime
from .chatbot import ChatBot
from .models import ChatBotMessage

User = get_user_model()
logger = logging.getLogger(__name__)

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            self.room_name = self.scope['url_route']['kwargs']['room_name']
            self.room_group_name = f'chat_{self.room_name}'
            self.user = self.scope['user']

            if not self.user.is_authenticated:
                await self.close()
                return

            # Join room group
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            await self.accept()
            logger.info(f"WebSocket connected for user {self.user.username} in room {self.room_name}")
        except Exception as e:
            logger.error(f"Error in connect: {str(e)}")
            await self.close()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message = data.get('message', '').strip()
            receiver_id = data.get('receiver_id')

            if not message or not receiver_id:
                await self.send(text_data=json.dumps({
                    'status': 'error',
                    'error': 'Invalid message data'
                }))
                return

            # Validate receiver exists
            receiver = await self.get_receiver(receiver_id)
            if not receiver:
                await self.send(text_data=json.dumps({
                    'status': 'error',
                    'error': 'Invalid receiver'
                }))
                return

            # Save message to database
            saved_message = await self.save_message(message, receiver_id)
            if not saved_message:
                await self.send(text_data=json.dumps({
                    'status': 'error',
                    'error': 'Failed to save message'
                }))
                return

            # Send message to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message,
                    'sender': self.user.username,
                    'timestamp': timezone.now().strftime("%I:%M %p")
                }
            )
            logger.info(f"Message sent from {self.user.username} to {receiver.username}")

        except Exception as e:
            logger.error(f"Error in receive: {str(e)}")
            await self.send(text_data=json.dumps({
                'status': 'error',
                'error': 'Internal server error'
            }))

    async def chat_message(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'sender': event['sender'],
            'timestamp': event['timestamp']
        }))

    @database_sync_to_async
    def get_receiver(self, receiver_id):
        try:
            return User.objects.get(id=receiver_id)
        except User.DoesNotExist:
            return None

    @database_sync_to_async
    def save_message(self, message, receiver_id):
        try:
            receiver = User.objects.get(id=receiver_id)
            return Message.objects.create(
                sender=self.scope['user'],
                receiver=receiver,
                content=message
            )
        except Exception as e:
            logger.error(f"Error saving message: {str(e)}")
            return None

class CallConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        if not self.user.is_authenticated:
            await self.close()
            return
            
        self.user_group_name = f'user_{self.user.id}'
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )
        await self.accept()
        logger.info(f"Call WebSocket connected for user {self.user.id}")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.user_group_name,
            self.channel_name
        )
        logger.info(f"Call WebSocket disconnected for user {self.user.id}")

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'call_offer':
                await self.handle_call_offer(data)
            elif message_type == 'call_response':
                await self.handle_call_response(data)
            elif message_type == 'call_status':
                await self.handle_call_status(data)
                
        except Exception as e:
            logger.error(f"Error in call receive: {str(e)}")
            await self.send_error("Failed to process call")

    async def handle_call_offer(self, data):
        receiver_id = data.get('receiver_id')
        call_id = data.get('call_id')
        receiver_group = f'user_{receiver_id}'
        
        await self.channel_layer.group_send(
            receiver_group,
            {
                'type': 'incoming_call',
                'call_id': call_id,
                'caller_id': self.user.id,
                'caller_name': self.user.username,
                'call_type': data.get('call_type')
            }
        )

    async def handle_call_response(self, data):
        caller_id = data.get('caller_id')
        caller_group = f'user_{caller_id}'
        
        await self.channel_layer.group_send(
            caller_group,
            {
                'type': 'call_response',
                'accepted': data.get('accepted'),
                'call_id': data.get('call_id'),
                'responder_name': self.user.username
            }
        )

    async def handle_call_status(self, data):
        call_id = data.get('call_id')
        status = data.get('status')
        other_user_id = data.get('other_user_id')
        
        await self.channel_layer.group_send(
            f'user_{other_user_id}',
            {
                'type': 'call.status_update',
                'call_id': call_id,
                'status': status
            }
        )

    async def incoming_call(self, event):
        await self.send(text_data=json.dumps({
            'type': 'incoming_call',
            'call_id': event['call_id'],
            'caller_id': event['caller_id'],
            'caller_name': event['caller_name'],
            'call_type': event['call_type']
        }))

    async def call_response(self, event):
        await self.send(text_data=json.dumps({
            'type': 'call_response',
            'accepted': event['accepted'],
            'call_id': event['call_id'],
            'responder_name': event['responder_name']
        }))

    async def call_status_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'call_status_update',
            'call_id': event['call_id'],
            'status': event['status']
        }))

    async def send_error(self, message):
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message
        }))

class AIChatConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chatbot = ChatBot()
        self.history = []

    async def connect(self):
        self.user = self.scope['user']
        if not self.user.is_authenticated:
            await self.close()
            return
        await self.accept()
        
        # Load chat history on connect
        history = await self.get_chat_history()
        if history:
            await self.send(text_data=json.dumps({
                'type': 'chat_history',
                'history': history
            }))

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            if data.get('type') == 'message':
                message = data.get('message', '').strip()
                if message:
                    # Get AI response
                    response = self.chatbot.get_response(message, history=self.history)
                    
                    # Save to database
                    await self.save_message(message, response)
                    
                    # Update history
                    self.history.extend([message, response])
                    if len(self.history) > 10:
                        self.history = self.history[-10:]
                    
                    # Send response
                    await self.send(text_data=json.dumps({
                        'type': 'ai_response',
                        'user_message': message,
                        'response': response,
                        'timestamp': datetime.now().strftime('%I:%M %p')
                    }))
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': str(e)
            }))

    @database_sync_to_async
    def save_message(self, user_message, ai_response):
        return ChatBotMessage.objects.create(
            user=self.scope['user'],
            message=user_message,
            response=ai_response
        )

    @database_sync_to_async
    def get_chat_history(self):
        messages = ChatBotMessage.objects.filter(user=self.scope['user']).order_by('-timestamp')[:10]
        return [{
            'user_message': msg.message,
            'response': msg.response,
            'timestamp': msg.timestamp.strftime('%I:%M %p')
        } for msg in reversed(messages)]
