import os
import asyncio
import logging
from typing import Optional, Dict, Any
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
    Defaults
)
from django.conf import settings
from asgiref.sync import sync_to_async
from ..models import Post, Topic, Settings, OpenAISettings
import telegram
import nest_asyncio
from .openai_service import OpenAIService

logger = logging.getLogger(__name__)

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

class TelegramService:
    """
    Сервис для работы с Telegram API
    """
    
    def __init__(self):
        self._loop = None
        self.application = None
        self.settings = None

    async def start_bot(self):
        """
        Запускает бота
        """
        try:
            # Get settings
            self.settings = await sync_to_async(Settings.get_active)()
            if not self.settings or not self.settings.telegram_bot_token:
                raise ValueError("Telegram bot token not configured")
            
            logger.info("Initializing bot...")
            
            # Create application with default settings
            defaults = Defaults(
                parse_mode='HTML'
            )
            
            self.application = Application.builder()\
                .token(self.settings.telegram_bot_token)\
                .defaults(defaults)\
                .build()
            
            # Add handlers
            self.application.add_handler(CommandHandler("start", self._start_command))
            self.application.add_handler(CommandHandler("help", self._help_command))
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))
            
            # Initialize with retries
            max_retries = 3
            retry_delay = 5
            
            for attempt in range(max_retries):
                try:
                    logger.info(f"Attempt {attempt + 1} to initialize bot...")
                    await self.application.initialize()
                    break
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    logger.warning(f"Initialization attempt {attempt + 1} failed: {str(e)}")
                    await asyncio.sleep(retry_delay)
            
            logger.info("Starting bot polling...")
            await self.application.run_polling(drop_pending_updates=True)
            
        except Exception as e:
            logger.error(f"Error running bot: {str(e)}", exc_info=True)
            raise

    def run(self):
        """
        Запускает бота в текущем event loop
        """
        try:
            self._loop = asyncio.get_event_loop()
            self._loop.run_until_complete(self.start_bot())
        except Exception as e:
            logger.error(f"Error in run: {str(e)}", exc_info=True)
            raise
        finally:
            if self._loop and self._loop.is_running():
                self._loop.stop()
            if self.application:
                self._loop.run_until_complete(self.application.stop())
            if self._loop:
                self._loop.close()

    async def _start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Обработчик команды /start
        """
        await update.message.reply_text(
            "Привет! Я бот для генерации контента. "
            "Отправь мне тему, и я помогу сгенерировать статью."
        )

    async def _help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Обработчик команды /help
        """
        await update.message.reply_text(
            "Я могу помочь сгенерировать контент на заданную тему. "
            "Просто отправь мне тему, и я создам статью."
        )

    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle incoming messages."""
        try:
            message = update.message
            if not message or not message.text:
                return

            # Get OpenAI settings
            openai_settings = await sync_to_async(OpenAISettings.get_active)()
            if not openai_settings or not openai_settings.api_key:
                await message.reply_text(
                    "⚠️ OpenAI API ключ не настроен. Пожалуйста, настройте API ключ в админ-панели."
                )
                return

            # Create a random topic
            topic = await sync_to_async(Topic.objects.order_by('?').first)()
            if not topic:
                await message.reply_text(
                    "⚠️ Нет доступных тем. Пожалуйста, добавьте темы в админ-панели."
                )
                return

            # Create a post
            post = await sync_to_async(Post.objects.create)(
                topic=topic,
                status='draft',
                author=message.from_user.username or str(message.from_user.id)
            )

            # Format prompt for content generation
            prompt = f"""
            Напиши статью на тему "{topic.title}" на русском языке.
            {f"Дополнительная информация: {topic.description}" if topic.description else ""}
            
            Требования к статье:
            1. Информативная и полезная
            2. Хорошо структурированная
            3. Легко читаемая
            4. Без технических ошибок
            
            Формат вывода:
            # Заголовок
            
            Введение (2-3 предложения)
            
            Основная часть (3-4 абзаца)
            
            Заключение (2-3 предложения)
            """

            # Generate content
            content = self.openai_service.generate_content(
                prompt=prompt,
                api_key=openai_settings.api_key
            )

            if not content:
                await message.reply_text(
                    "❌ Не удалось сгенерировать контент. Пожалуйста, попробуйте позже."
                )
                return

            # Update post with generated content
            post.content = content
            post.status = 'published'
            await sync_to_async(post.save)()

            # Send the generated content to the user
            await message.reply_text(content)

        except Exception as e:
            logger.error(f"Error handling message: {str(e)}")
            await message.reply_text(
                "❌ Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте позже."
            )

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

    async def generate_content(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        content_type: str = 'random'
    ):
        """Generate content based on type."""
        try:
            # Get random topic from database
            topic = await sync_to_async(Topic.objects.order_by('?').first)()
            if not topic:
                await update.message.reply_text("No topics available in database.")
                return

            # Get OpenAI settings
            openai_settings = await sync_to_async(OpenAISettings.get_active)()
            if not openai_settings or not openai_settings.api_key:
                raise ValueError("OpenAI API key not configured")

            # Generate content using OpenAI
            try:
                content = OpenAIService.generate_content(
                    topic=topic.name,
                    description=topic.description,
                    language=topic.language if hasattr(topic, 'language') else 'ru',
                    api_key=openai_settings.api_key
                )
            except Exception as e:
                logger.error(f"OpenAI error: {str(e)}")
                raise ValueError(f"Ошибка при генерации контента: {str(e)}")

            if not content:
                await update.message.reply_text("Failed to generate content.")
                return

            # Create post in database
            post = await sync_to_async(Post.objects.create)(
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
        post = await sync_to_async(Post.objects.get)(id=post_id)

        if action == "regenerate":
            # Get OpenAI settings
            openai_settings = await sync_to_async(OpenAISettings.get_active)()
            if not openai_settings or not openai_settings.api_key:
                raise ValueError("OpenAI API key not configured")

            # Regenerate content
            try:
                new_content = OpenAIService.generate_content(
                    topic=post.topic.name,
                    description=post.topic.description,
                    language=post.language,
                    api_key=openai_settings.api_key
                )
            except Exception as e:
                logger.error(f"OpenAI error: {str(e)}")
                await query.edit_message_text(
                    text=f"Ошибка при генерации контента: {str(e)}",
                    reply_markup=query.message.reply_markup
                )
                return

            if new_content:
                post.content = new_content
                await sync_to_async(post.save)()
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
                await sync_to_async(post.save)()
                await query.edit_message_text(
                    text=f"{post.content}\n\n✅ Published to channel!",
                    reply_markup=None
                )
            except Exception as e:
                await query.edit_message_text(
                    text=f"{post.content}\n\n❌ Failed to publish: {str(e)}",
                    reply_markup=query.message.reply_markup
                ) 