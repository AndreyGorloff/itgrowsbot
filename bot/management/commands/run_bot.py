import time
import logging
from django.core.management.base import BaseCommand
from django.db import connections
from django.db.utils import OperationalError
from bot.services.telegram_service import TelegramService

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Runs the Telegram bot'

    def wait_for_db(self):
        """Wait for database to be available"""
        logger.info('Waiting for database...')
        db_conn = None
        for _ in range(60):  # try for 60 seconds
            try:
                db_conn = connections['default']
                db_conn.cursor()
                logger.info('Database available!')
                return True
            except OperationalError:
                logger.info('Database unavailable, waiting 1 second...')
                time.sleep(1)
        return False

    def handle(self, *args, **options):
        logger.info('Starting Telegram bot...')
        
        try:
            # Wait for database
            if not self.wait_for_db():
                logger.error('Could not connect to database')
                return

            # Create and run the bot
            bot = TelegramService()
            bot.run()
            
        except KeyboardInterrupt:
            logger.info('Bot stopped by user')
        except Exception as e:
            logger.error(f'Error running bot: {str(e)}', exc_info=True)
        finally:
            logger.info('Bot stopped') 