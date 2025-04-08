import secrets
import string

# Generate a random string of 50 characters
chars = string.ascii_letters + string.digits + string.punctuation
secret_key = ''.join(secrets.choice(chars) for _ in range(50))
print(secret_key) 