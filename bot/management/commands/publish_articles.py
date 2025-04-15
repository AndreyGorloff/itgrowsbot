from django.core.management.base import BaseCommand
from django.utils import timezone
from bot.models import Post, Settings
from bot.services.telegram_service import TelegramService
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Publishes articles to Telegram channel based on priority'

    def handle(self, *args, **options):
        try:
            # Get active settings
            settings = Settings.objects.filter(is_active=True).first()
            if not settings:
                logger.error("No active settings found")
                return

            # Get the next article to publish
            article = Post.objects.filter(
                status='ready',
                published_at__isnull=True
            ).order_by('-priority', '-created_at').first()

            if not article:
                logger.info("No articles ready for publishing")
                return

            # Initialize Telegram service
            telegram_service = TelegramService(
                bot_token=settings.telegram_bot_token,
                channel_id=settings.telegram_channel_id
            )

            # Publish the article
            try:
                message_id = telegram_service.send_message(article.content)
                if message_id:
                    article.status = 'published'
                    article.published_at = timezone.now()
                    article.telegram_message_id = message_id
                    article.save()
                    logger.info(f"Successfully published article: {article.topic.name}")
                else:
                    logger.error(f"Failed to publish article: {article.topic.name}")
            except Exception as e:
                logger.error(f"Error publishing article {article.topic.name}: {str(e)}")
                article.status = 'failed'
                article.save()

        except Exception as e:
            logger.error(f"Error in publish_articles command: {str(e)}") 