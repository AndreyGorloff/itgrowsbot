from celery import shared_task
from django.utils import timezone
from .models import Post, Topic
from .services.openai_service import OpenAIService
from .services.telegram_service import TelegramService

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
        openai_service = OpenAIService()
        
        content = openai_service.generate_content(
            topic=topic.title,
            description=topic.description,
            language=topic.language,
            style=style
        )
        
        if content:
            Post.objects.create(
                topic=topic,
                content=content,
                language=topic.language,
                created_by=topic.created_by
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