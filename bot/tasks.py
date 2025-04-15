from celery import shared_task
from django.utils import timezone
from .models import Post, Topic, OpenAISettings, OllamaModel
from .services.openai_service import OpenAIService
from .services.telegram_service import TelegramService
from django.contrib.auth import get_user_model

@shared_task
def generate_content_for_topic(topic_id: int, style: str = 'expert') -> bool:
    """
    Generate content for a specific topic using OpenAI.
    
    Args:
        topic_id: ID of the topic to generate content for
        style: Content style (expert, casual, humorous)
        
    Returns:
        bool: True if content was generated successfully
    """
    try:
        topic = Topic.objects.get(id=topic_id)
        
        content = OpenAIService.generate_content(
            topic=topic.name,
            description=topic.description,
            language=topic.language if hasattr(topic, 'language') else 'ru',
            style=style
        )
        
        if content:
            Post.objects.create(
                topic=topic,
                content=content,
                language=topic.language if hasattr(topic, 'language') else 'ru',
                created_by=topic.created_by if hasattr(topic, 'created_by') else None
            )
            return True
            
        return False
        
    except Exception as e:
        print(f"Error generating content: {str(e)}")
        return False

@shared_task
def publish_post_to_telegram(post_id: int) -> bool:
    """
    Publish a post to Telegram channel.
    
    Args:
        post_id: ID of the post to publish
        
    Returns:
        bool: True if post was published successfully
    """
    try:
        post = Post.objects.get(id=post_id)
        telegram_service = TelegramService()
        
        # Send message to channel
        message = telegram_service.bot.send_message(
            chat_id=telegram_service.channel_id,
            text=post.content
        )
        
        # Update post status
        post.telegram_message_id = message.message_id
        post.status = 'published'
        post.published_at = timezone.now()
        post.save()
        
        return True
        
    except Exception as e:
        print(f"Error publishing post: {str(e)}")
        post.status = 'failed'
        post.save()
        return False

@shared_task
def schedule_posts():
    """
    Schedule posts for publishing.
    This task should be run periodically to check for posts
    that need to be published.
    """
    # Get all draft posts
    draft_posts = Post.objects.filter(status='draft')
    
    for post in draft_posts:
        # You can add your scheduling logic here
        # For example, publish posts that are older than 1 hour
        if (timezone.now() - post.created_at).total_seconds() > 3600:
            publish_post_to_telegram.delay(post.id)

@shared_task(bind=True)
def generate_article_for_topic(self, topic_id: int, user_id: int) -> int:
    """
    Generate an article for a specific topic asynchronously.
    
    Args:
        topic_id: ID of the topic to generate content for
        user_id: ID of the user who initiated the generation
        
    Returns:
        int: ID of the created post
    """
    try:
        topic = Topic.objects.get(id=topic_id)
        user = get_user_model().objects.get(id=user_id)
        
        # Create post with generating status
        post = Post.objects.create(
            topic=topic,
            status='generating',
            progress=0,
            created_by=user
        )
        
        try:
            # Check if we should use local model
            openai_settings = OpenAISettings.get_active()
            if openai_settings and openai_settings.use_local_model:
                # Validate that the model exists and is active
                model_name = openai_settings.local_model_name
                ollama_model = OllamaModel.objects.filter(
                    name=model_name,
                    is_active=True,
                    is_installed=True
                ).first()
                
                if not ollama_model:
                    raise ValueError(f"Model {model_name} is not available or not active")
                
                # Update progress
                post.progress = 10
                post.save()
                
                # Initialize Ollama service
                from bot.services.ollama_service import OllamaService
                ollama_service = OllamaService()
                
                # Update progress
                post.progress = 20
                post.save()
                
                # Generate content
                prompt = f"Write an article about {topic.name}"
                content = ollama_service.generate_content(prompt)
                
                # Update progress
                post.progress = 100
                post.content = content
                post.status = 'draft'
                post.save()
                
            else:
                # Use OpenAI
                openai_service = OpenAIService()
                article = openai_service.generate_article(topic.name)
                
                # Update post with generated content
                post.content = article['content']
                post.status = 'draft'
                post.progress = 100
                post.save()
            
            return post.id
            
        except Exception as e:
            post.status = 'failed'
            post.progress = 0
            post.save()
            raise e
            
    except Exception as e:
        print(f"Error generating article: {str(e)}")
        raise 