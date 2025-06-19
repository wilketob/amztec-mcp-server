"""
Authentication and security utilities for Amazon SP API MCP Server
"""

import os
import hmac
import hashlib
import time
import jwt
from typing import Dict, Any, Optional
from functools import wraps
import logging

logger = logging.getLogger(__name__)

class MCPAuth:
    """Authentication handler for MCP server"""
    
    def __init__(self):
        self.secret_key = os.getenv('MCP_SECRET_KEY', 'your-secret-key-change-in-production')
        self.api_keys = self._load_api_keys()
        self.jwt_algorithm = 'HS256'
        self.jwt_expiry = 3600  # 1 hour
    
    def _load_api_keys(self) -> Dict[str, str]:
        """Load API keys from environment or config"""
        api_keys = {}
        
        # Load from environment variables
        api_keys_env = os.getenv('MCP_API_KEYS', '')
        if api_keys_env:
            for key_pair in api_keys_env.split(','):
                if ':' in key_pair:
                    key_id, key_secret = key_pair.split(':', 1)
                    api_keys[key_id.strip()] = key_secret.strip()
        
        # Default development key (remove in production)
        if not api_keys and os.getenv('ENVIRONMENT') != 'production':
            api_keys['dev-key'] = 'dev-secret-change-me'
            logger.warning("Using default development API key. Change in production!")
        
        return api_keys
    
    def generate_jwt_token(self, user_id: str, additional_claims: Dict = None) -> str:
        """Generate JWT token for user"""
        payload = {
            'user_id': user_id,
            'iat': int(time.time()),
            'exp': int(time.time()) + self.jwt_expiry
        }
        
        if additional_claims:
            payload.update(additional_claims)
        
        return jwt.encode(payload, self.secret_key, algorithm=self.jwt_algorithm)
    
    def verify_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token and return payload"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.jwt_algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            return None
    
    def verify_api_key(self, api_key: str) -> bool:
        """Verify API key"""
        if not api_key:
            return False
        
        # Extract key ID and secret from API key
        if ':' not in api_key:
            return False
        
        key_id, key_secret = api_key.split(':', 1)
        
        # Check if key exists and matches
        stored_secret = self.api_keys.get(key_id)
        if not stored_secret:
            return False
        
        # Use constant-time comparison to prevent timing attacks
        return hmac.compare_digest(stored_secret, key_secret)
    
    def verify_signature(self, payload: str, signature: str, timestamp: str) -> bool:
        """Verify request signature for webhook-style authentication"""
        # Check timestamp (prevent replay attacks)
        try:
            request_time = int(timestamp)
            current_time = int(time.time())
            
            # Allow 5 minute window
            if abs(current_time - request_time) > 300:
                logger.warning("Request timestamp too old")
                return False
        except (ValueError, TypeError):
            logger.warning("Invalid timestamp format")
            return False
        
        # Verify signature
        expected_signature = hmac.new(
            self.secret_key.encode(),
            f"{timestamp}.{payload}".encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)


# Authentication middleware
class AuthenticationMiddleware:
    """Middleware for handling authentication"""
    
    def __init__(self):
        self.auth = MCPAuth()
        self.public_endpoints = ['/health', '/docs']
    
    def authenticate_request(self, headers: Dict[str, str], path: str) -> Optional[Dict[str, Any]]:
        """Authenticate incoming request"""
        # Skip authentication for public endpoints
        if path in self.public_endpoints:
            return {'user_id': 'anonymous', 'authenticated': False}
        
        # Try JWT token authentication
        auth_header = headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]  # Remove 'Bearer ' prefix
            payload = self.auth.verify_jwt_token(token)
            if payload:
                return {'user_id': payload['user_id'], 'authenticated': True, 'method': 'jwt'}
        
        # Try API key authentication
        api_key = headers.get('X-API-Key')
        if api_key and self.auth.verify_api_key(api_key):
            key_id = api_key.split(':', 1)[0]
            return {'user_id': key_id, 'authenticated': True, 'method': 'api_key'}
        
        # Try signature authentication
        signature = headers.get('X-Signature')
        timestamp = headers.get('X-Timestamp')
        if signature and timestamp:
            # This would need the request body, implement based on your needs
            pass
        
        return None


# Rate limiting
class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self):
        self.requests = {}
        self.limits = {
            'default': {'requests': 100, 'window': 3600},  # 100 requests per hour
            'authenticated': {'requests': 1000, 'window': 3600},  # 1000 requests per hour
            'premium': {'requests': 10000, 'window': 3600}  # 10000 requests per hour
        }
    
    def is_allowed(self, identifier: str, tier: str = 'default') -> bool:
        """Check if request is allowed"""
        current_time = int(time.time())
        limit_config = self.limits.get(tier, self.limits['default'])
        
        # Clean old entries
        if identifier in self.requests:
            self.requests[identifier] = [
                req_time for req_time in self.requests[identifier]
                if current_time - req_time < limit_config['window']
            ]
        else:
            self.requests[identifier] = []
        
        # Check limit
        if len(self.requests[identifier]) >= limit_config['requests']:
            return False
        
        # Add current request
        self.requests[identifier].append(current_time)
        return True


# Decorator for protecting endpoints
def require_auth(f):
    """Decorator to require authentication for endpoints"""
    @wraps(f)
    async def wrapper(*args, **kwargs):
        # This would need to be integrated with your web framework
        # Example implementation would extract headers from request
        # and call authentication middleware
        return await f(*args, **kwargs)
    return wrapper


# Example usage in FastAPI/Starlette
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

class MCPAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.auth = AuthenticationMiddleware()
        self.rate_limiter = RateLimiter()
    
    async def dispatch(self, request, call_next):
        # Extract headers
        headers = dict(request.headers)
        path = request.url.path
        
        # Authenticate request
        auth_result = self.auth.authenticate_request(headers, path)
        
        if not auth_result and path not in self.auth.public_endpoints:
            return JSONResponse(
                status_code=401,
                content={"error": "Authentication required"}
            )
        
        # Rate limiting
        identifier = auth_result['user_id'] if auth_result else request.client.host
        tier = 'authenticated' if auth_result and auth_result['authenticated'] else 'default'
        
        if not self.rate_limiter.is_allowed(identifier, tier):
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit exceeded"}
            )
        
        # Add auth info to request state
        request.state.auth = auth_result
        
        response = await call_next(request)
        return response
"""