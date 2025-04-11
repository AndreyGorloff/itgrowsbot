import time
import signal
from django.core.management.base import BaseCommand
from django.db import connections
from django.db.utils import OperationalError
from bot.services.telegram_service import TelegramService

class Command(BaseCommand):
    help = 'Runs the Telegram bot'

    def wait_for_db(self):
        """Wait for database to be available"""
        self.stdout.write('Waiting for database...')
        db_conn = None
        for _ in range(60):  # try for 60 seconds
            try:
                db_conn = connections['default']
                db_conn.cursor()
                self.stdout.write(self.style.SUCCESS('Database available!'))
                return True
            except OperationalError:
                self.stdout.write('Database unavailable, waiting 1 second...')
                time.sleep(1)
        return False

    def handle(self, *args, **options):
        self.stdout.write('Starting Telegram bot...')
        
        try:
            # Wait for database
            if not self.wait_for_db():
                self.stdout.write(self.style.ERROR('Could not connect to database'))
                return

            # Create and run the bot
            bot = TelegramService()
            bot.run()
            
        except KeyboardInterrupt:
            self.stdout.write(self.style.SUCCESS('Bot stopped by user'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error running bot: {str(e)}'))
        finally:
            self.stdout.write(self.style.SUCCESS('Bot stopped')) 