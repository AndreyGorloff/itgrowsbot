import asyncio
from django.core.management.base import BaseCommand
from bot.services.telegram_service import TelegramService

class Command(BaseCommand):
    help = 'Runs the Telegram bot'

    def handle(self, *args, **options):
        self.stdout.write('Starting Telegram bot...')
        
        try:
            # Create and run the bot
            bot = TelegramService()
            
            # Run the bot
            asyncio.run(bot.run())
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error running bot: {str(e)}'))
            return
            
        self.stdout.write(self.style.SUCCESS('Bot stopped')) 