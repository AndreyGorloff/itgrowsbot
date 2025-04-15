from django.core.management.base import BaseCommand
from django.utils.translation import gettext as _
from bot.models import OllamaModel
from bot.services.ollama_service import OllamaService
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = _('Sync Ollama models with database')

    def handle(self, *args, **options):
        try:
            ollama_service = OllamaService()
            
            # Get available models from Ollama
            available_models = ollama_service.get_available_models()
            if not available_models:
                logger.error("No models found in Ollama")
                return
            
            # Update database with available models
            for model_info in available_models:
                model_name = model_info.get('name')
                model_size = model_info.get('size', '')
                model_details = {
                    'digest': model_info.get('digest', ''),
                    'modified_at': model_info.get('modified_at', ''),
                    'size': model_size,
                }
                
                # Create or update model in database
                OllamaModel.objects.update_or_create(
                    name=model_name,
                    defaults={
                        'is_installed': True,
                        'size': model_size,
                        'details': model_details,
                    }
                )
            
            # Mark uninstalled models
            installed_models = [model_info.get('name') for model_info in available_models]
            OllamaModel.objects.exclude(name__in=installed_models).update(
                is_installed=False,
                size=None,
                details={}
            )
            
            logger.info(f"Successfully synced {len(available_models)} Ollama models with database")
            
        except Exception as e:
            logger.error(f"Error syncing Ollama models: {str(e)}")
            raise 