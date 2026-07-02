#!/usr/bin/env python3
"""
Script to create .env file for local backend development
"""
import os

env_content = """# Environment
ENVIRONMENT=development
DEBUG=true

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_VERSION=v1

# Security
SECRET_KEY=your-local-dev-secret-key-change-in-production-12345

# Firebase Configuration (from flowmind-ai-123-firebase-adminsdk-fbsvc-6361e78988.json)
FIREBASE_PROJECT_ID=flowmind-ai-123
FIREBASE_PRIVATE_KEY_ID=6361e7898817b5c0bec96d284ec742b63fcb6b10
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQCsMM4wdfx2I5xu\\n4P+DpADbFs079YmrNaaBUk9m9rjbQC/mFsaX8g5ZTRntoy2QFREdy9NNZEEdVL2M\\nYWRt/ok0gyLSlJ64e0Vbd2sIkm7u3ovkRhz3u44i9FKXzjJ4PP9bx7UQsCglx49S\\ne/URwXvYthbP9BAwhpgowDx5zkFytGs5KtIZf+xjK9K2dGTFpRELAc9GdmbzcYEi\\nmtUrltdjrXRKdBwvaS/WLWuVFRhJvnDtsEKuEVDIzYkToORlMi/mcvBl07BVsc/T\\nn4P4bMQpIqwOEqfmO2vHop2Hk/96UsaV/4X2S/YTSXam7TQrIe88FwqO83nk+lSH\\nGwCX9u7VAgMBAAECggEAHiw/NUa3gowi8VsD6zFl5P5N4F/aS+IO10JxH33ETsck\\nnZEII8AKu6NDE90wMrs+UJZS5JDYyCb9QAgg7RVZPZZtF7FrTrBrKuf2HX5rafgd\\nU1bl5JM9COr/PhKnzWIC7TZFiDMWFeiuOKn3+7CH3yWpQa9m1tn+98UX09BMr6ic\\nJTv6KJRHYJzGvF2j/iRxVkUzmPyWFyEsTWsXE1ste++q5N+0jKuOnH/m5mRktU6f\\n5W6TVgSq8ypeZwLUY02ZuFAjTK5Na5cOb2ci9RueG4Vz41S19KtnBM5KSrZf9o4X\\nyA8MXpIAt60fCT6l13ZfE1507NOpyWM/dZI6OuAe0QKBgQDcqFJVt5g7QSXOhSON\\nPcMVw2wsrUkjvWu6M6VYrgs97AUUwfq9HUsZE+ElLOJFZpvbGFEKZTB4reoizkaQ\\n38VSVo6IBTlOCpT17dQqQh8qwCJEwm6XtEDaiM4Gy/T3IqnpaQlODD965qJ6A+1k\\nZwg2ZJRklknhmz74s6iMEeNE2wKBgQDHxS8rlZFg85BUav+xA+ezK/mjtXBWTJkv\\nBfpKUt98xnTFcITucZ0UWaX9rzEPe7czZCnKmGpoeJLveA/Lq+a8FOOGUcP6ddA2\\nCsOKTZAiv1NXrHal90a5MBaum4GMM1KWPU43nFS5BO6HJnvdLuseuLagXqgy+GNU\\n2kaAAHOSDwKBgQCzVP1tesP3THA8kwoczVhSxLuS59asfFMkRrsYAoNSdRKAF1MA\\nBeG15OkzfHH9M3JxsyaSC0FEoxvJ49mH/sVwsLYwKAa1vXXpFbw8B/cqmHKBbX/S\\nPYYD1fGTpolVnU94SoxsaRniebUM80opMm+DPWU5BsfO2oxoNiNCi3soxwKBgQCQ\\ngAw/vX+cHnH+7iqns0hs7Nk1Vq+8bMm9HtjN3CY2TiL3Eg3FoD7cEoCkAI4/QeDh\\ndolYN2l4ygaW20SpsV1EHOP7K7fTulZyUNTifHpO+A/j8icco8HvgF5XzLonXJRX\\ngl7KkPUjo/KZpfegpSiDX18Sn4WQ4OSQ4xZtzmXKdwKBgCnjbU4TwvY4kbO92uTc\\nhJ36n2l/ll0eQ5TEfqYKrVZQ6tTHF8/mJbWj03+dE3cSr13FZXuigp4uVFk6p0rU\\nFlGDA5Y2GNfrBZYYWtKSNi6FEJJOboJD9VjwAkwY4h5XDZIZRotQIGdnn7mNRQnj\\nB0FQmcrwu8XkBhNQWVEnEADD\\n-----END PRIVATE KEY-----\\n"
FIREBASE_CLIENT_EMAIL=firebase-adminsdk-fbsvc@flowmind-ai-123.iam.gserviceaccount.com
FIREBASE_CLIENT_ID=104750455099643691741
FIREBASE_AUTH_URI=https://accounts.google.com/o/oauth2/auth
FIREBASE_TOKEN_URI=https://oauth2.googleapis.com/token
FIREBASE_AUTH_PROVIDER_CERT_URL=https://www.googleapis.com/oauth2/v1/certs
FIREBASE_CLIENT_CERT_URL=https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-fbsvc%40flowmind-ai-123.iam.gserviceaccount.com

# CORS Configuration (for local development)
CORS_ORIGINS=http://localhost:3000,http://localhost:3001

# Logging
LOG_LEVEL=INFO
"""

# Write to .env file
env_path = os.path.join(os.path.dirname(__file__), '.env')
with open(env_path, 'w') as f:
    f.write(env_content)

print(f"✅ Created .env file at: {env_path}")
print("📝 Next steps:")
print("   1. Install dependencies: pip install -r requirements.txt")
print("   2. Run backend: python run.py")
print("   3. Update frontend .env.local with: NEXT_PUBLIC_BACKEND_API_URL=http://localhost:8000")

