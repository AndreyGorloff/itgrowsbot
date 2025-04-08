import openai
from django.conf import settings

def generate_article(topic):
    """
    Генерирует статью на основе заданного топика
    """
    openai.api_key = settings.OPENAI_API_KEY
    
    prompt = f"""
    Напиши информативную статью на тему "{topic}".
    Статья должна быть структурированной, с заголовками и подзаголовками.
    Используй маркированные списки где это уместно.
    Статья должна быть написана в формате HTML.
    """
    
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Ты - опытный копирайтер, который пишет информативные статьи."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=2000
    )
    
    content = response.choices[0].message.content
    
    # Извлекаем заголовок из первого h1 или h2 тега
    title = topic
    if "<h1>" in content:
        title = content.split("<h1>")[1].split("</h1>")[0]
    elif "<h2>" in content:
        title = content.split("<h2>")[1].split("</h2>")[0]
    
    return {
        'title': title,
        'content': content
    } 