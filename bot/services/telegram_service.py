import os
import asyncio
from typing import Optional, Dict, Any
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)
from django.conf import settings
from ..models import Post, Topic, Settings
import telegram
import nest_asyncio

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

class TelegramService:
    """
    Сервис для работы с Telegram API
    """
    
    def __init__(self):
        settings_obj = Settings.get_active()
        if not settings_obj:
            raise ValueError("Telegram settings not configured. Please configure Telegram settings in admin panel.")
        
        self.bot_token = settings_obj.telegram_bot_token
        self.channel_id = settings_obj.telegram_channel_id
        self.bot = telegram.Bot(token=self.bot_token)
        self.application = None

    def setup_handlers(self):
        """Setup command and callback handlers."""
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("content", self.generate_content))
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))

    async def start_bot(self):
        """Start the bot."""
        try:
            # Initialize application
            self.application = Application.builder().token(self.bot_token).build()
            
            # Setup handlers
            self.setup_handlers()
            
            # Start the bot
            await self.application.initialize()
            await self.application.start()
            await self.application.run_polling(close_loop=False)
            
        except Exception as e:
            print(f"Error starting bot: {str(e)}")
            if self.application and self.application.running:
                await self.application.stop()
            raise

    def run(self):
        """Run the bot."""
        try:
            # Get or create event loop
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Run the bot
            loop.run_until_complete(self.start_bot())
            
        except KeyboardInterrupt:
            print("Bot stopped by user")
        except Exception as e:
            print(f"Error running bot: {str(e)}")
            raise

    def send_message(self, text, parse_mode='HTML'):
        """
        Отправляет сообщение в канал
        """
        return self.bot.send_message(
            chat_id=self.channel_id,
            text=text,
            parse_mode=parse_mode
        )
    
    def edit_message(self, message_id, text, parse_mode='HTML'):
        """
        Редактирует сообщение в канале
        """
        return self.bot.edit_message_text(
            chat_id=self.channel_id,
            message_id=message_id,
            text=text,
            parse_mode=parse_mode
        )

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /start command."""
        welcome_text = (
            "👋 Welcome to Content Generator Bot!\n\n"
            "Available commands:\n"
            "/content - Generate random content\n"
            "/checklist - Generate checklist content\n"
            "/mistake - Generate common mistakes content\n"
            "/lang - Switch language (ru/en)"
        )
        await update.message.reply_text(welcome_text)

    async def generate_content(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        content_type: str = 'random'
    ):
        """Generate content based on type."""
        try:
            # Get random topic from database
            topic = Topic.objects.order_by('?').first()
            if not topic:
                await update.message.reply_text("No topics available in database.")
                return

            # Generate content using OpenAI
            from .openai_service import OpenAIService
            content = OpenAIService.generate_content(
                topic=topic.name,
                description=topic.description,
                language=topic.language if hasattr(topic, 'language') else 'ru'
            )

            if not content:
                await update.message.reply_text("Failed to generate content.")
                return

            # Create post in database
            post = Post.objects.create(
                topic=topic,
                content=content,
                language=topic.language if hasattr(topic, 'language') else 'ru',
                created_by=update.effective_user
            )

            # Send content with inline buttons
            keyboard = [
                [
                    InlineKeyboardButton("🔄 Regenerate", callback_data=f"regenerate_{post.id}"),
                    InlineKeyboardButton("📝 Edit", callback_data=f"edit_{post.id}")
                ],
                [
                    InlineKeyboardButton("📢 Publish", callback_data=f"publish_{post.id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                content,
                reply_markup=reply_markup
            )

        except Exception as e:
            await update.message.reply_text(f"Error: {str(e)}")

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries from inline buttons."""
        query = update.callback_query
        await query.answer()

        action, post_id = query.data.split('_')
        post = Post.objects.get(id=post_id)

        if action == "regenerate":
            # Regenerate content
            from .openai_service import OpenAIService
            new_content = OpenAIService.generate_content(
                topic=post.topic.name,
                description=post.topic.description,
                language=post.language
            )
            if new_content:
                post.content = new_content
                post.save()
                await query.edit_message_text(
                    text=new_content,
                    reply_markup=query.message.reply_markup
                )

        elif action == "publish":
            # Publish to channel
            try:
                message = await self.bot.send_message(
                    chat_id=self.channel_id,
                    text=post.content
                )
                post.telegram_message_id = message.message_id
                post.status = 'published'
                post.save()
                await query.edit_message_text(
                    text=f"{post.content}\n\n✅ Published to channel!",
                    reply_markup=None
                )
            except Exception as e:
                await query.edit_message_text(
                    text=f"{post.content}\n\n❌ Failed to publish: {str(e)}",
                    reply_markup=query.message.reply_markup
                ) 