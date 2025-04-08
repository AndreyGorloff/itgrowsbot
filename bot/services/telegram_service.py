import os
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

class TelegramService:
    def __init__(self):
        settings_obj = Settings.get_active()
        if not settings_obj:
            raise ValueError("No active settings found in database")
            
        self.bot = Bot(token=settings_obj.telegram_bot_token)
        self.channel_id = settings_obj.telegram_channel_id
        self.application = Application.builder().token(settings_obj.telegram_bot_token).build()

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
            openai_service = OpenAIService()
            content = openai_service.generate_content(
                topic=topic.title,
                description=topic.description,
                language=topic.language
            )

            if not content:
                await update.message.reply_text("Failed to generate content.")
                return

            # Create post in database
            post = Post.objects.create(
                topic=topic,
                content=content,
                language=topic.language,
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
            openai_service = OpenAIService()
            new_content = openai_service.generate_content(
                topic=post.topic.title,
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

    def setup_handlers(self):
        """Setup command and callback handlers."""
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("content", self.generate_content))
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))

    async def run(self):
        """Run the bot."""
        self.setup_handlers()
        await self.application.initialize()
        await self.application.start()
        await self.application.run_polling() 