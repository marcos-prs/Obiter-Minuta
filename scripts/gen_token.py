"""
Gera um JWT de teste assinado com o SECRET_KEY do .env.
Uso: python scripts/gen_token.py
"""
import sys
import os

# Permite rodar da raiz do projeto
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from jose import jwt
from app.config import get_settings

settings = get_settings()
token = jwt.encode({"sub": "test-client"}, settings.secret_key, algorithm="HS256")

print("=" * 60)
print("Bearer token para testes:")
print(token)
print("=" * 60)
print(f"\nExemplo de uso:")
print(f'  curl -H "Authorization: Bearer {token}" http://localhost:8000/health')
