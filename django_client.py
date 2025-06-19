"""
Django Client for Amazon SP API MCP Server
Provides easy integration between Django and the MCP server
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
import httpx
from django.conf import settings
from django.core.cache import cache
import asyncio

logger = logging.getLogger(__name__)

class AmazonMCPClient:
    """Django client for communicating with Amazon SP API MCP Server"""
    
    def __init__(self, base_url: str = None, timeout: int = 30):
        self.base_url = base_url or getattr(settings, 'AMAZON_MCP_BASE_URL', 'http://localhost:8000')
        self.timeout = timeout
        self.session = None
        
    async def _get_session(self) -> httpx.AsyncClient:
        """Get or create HTTP session"""
        if self.session is None:
            self.session = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                }
            )
        return self.session
    
    async def _make_request(self, method: str, endpoint: str, data: Dict = None) -> Dict[str, Any]:
        """Make HTTP request to MCP server"""
        try:
            session = await self._get_session()
            
            if method.upper() == 'POST':
                response = await session.post(endpoint, json=data)
            else:
                response = await session.get(endpoint)
            
            response.raise_for_status()
            return response.json()
            
        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            raise Exception(f"Failed to connect to MCP server: {e}")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"MCP server error: {e.response.status_code}")
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the MCP server"""
        data = {
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        response = await self._make_request('POST', '/sse', data)
        return response
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools from MCP server"""
        data = {
            "method": "tools/list",
            "params": {}
        }
        
        response = await self._make_request('POST', '/sse', data)
        return response.get('result', {}).get('tools', [])
    
    async def get_product_info(self, sku: str, seller_id: str = "default") -> Dict[str, Any]:
        """Get Amazon product information by SKU"""
        cache_key = f"amazon_product_{sku}_{seller_id}"
        
        # Check cache first
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data
        
        arguments = {
            "sku": sku,
            "seller_id": seller_id
        }
        
        result = await self.call_tool("get_amazon_product_info", arguments)
        
        # Cache result for 1 hour
        if 'error' not in result:
            cache.set(cache_key, result, 3600)
        
        return result
    
    async def get_product_pricing(self, sku: str, seller_id: str = "default") -> Dict[str, Any]:
        """Get Amazon product pricing by SKU"""
        cache_key = f"amazon_pricing_{sku}_{seller_id}"
        
        # Check cache first (shorter cache time for pricing)
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data
        
        arguments = {
            "sku": sku,
            "seller_id": seller_id
        }
        
        result = await self.call_tool("get_amazon_product_pricing", arguments)
        
        # Cache result for 15 minutes
        if 'error' not in result:
            cache.set(cache_key, result, 900)
        
        return result
    
    async def optimize_product_listing(self, asin: str, optimization_focus: str = "all", user_id: str = "default") -> Dict[str, Any]:
        """Get product listing optimization suggestions"""
        arguments = {
            "asin": asin,
            "optimization_focus": optimization_focus,
            "user_id": user_id
        }
        
        result = await self.call_tool("optimize_product_listing", arguments)
        return result
    
    async def health_check(self) -> bool:
        """Check if MCP server is healthy"""
        try:
            await self._make_request('GET', '/health')
            return True
        except Exception:
            return False
    
    async def close(self):
        """Close the HTTP session"""
        if self.session:
            await self.session.aclose()
            self.session = None


# Django sync wrapper functions
def run_async_in_django(coro):
    """Helper to run async code in Django sync context"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(coro)


class DjangoAmazonMCPClient:
    """Synchronous wrapper for Django views"""
    
    def __init__(self, base_url: str = None):
        self.client = AmazonMCPClient(base_url)
    
    def get_product_info(self, sku: str, seller_id: str = "default") -> Dict[str, Any]:
        """Synchronous version of get_product_info"""
        return run_async_in_django(self.client.get_product_info(sku, seller_id))
    
    def get_product_pricing(self, sku: str, seller_id: str = "default") -> Dict[str, Any]:
        """Synchronous version of get_product_pricing"""
        return run_async_in_django(self.client.get_product_pricing(sku, seller_id))
    
    def optimize_product_listing(self, asin: str, optimization_focus: str = "all", user_id: str = "default") -> Dict[str, Any]:
        """Synchronous version of optimize_product_listing"""
        return run_async_in_django(self.client.optimize_product_listing(asin, optimization_focus, user_id))
    
    def health_check(self) -> bool:
        """Synchronous version of health_check"""
        return run_async_in_django(self.client.health_check())
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """Synchronous version of list_tools"""
        return run_async_in_django(self.client.list_tools())


# Example Django views
"""
# views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from .django_client import DjangoAmazonMCPClient

# Initialize client
amazon_client = DjangoAmazonMCPClient()

@csrf_exempt
@require_http_methods(["GET"])
def get_product_info(request, sku):
    try:
        seller_id = request.GET.get('seller_id', 'default')
        product_info = amazon_client.get_product_info(sku, seller_id)
        return JsonResponse(product_info)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt  
@require_http_methods(["GET"])
def get_product_pricing(request, sku):
    try:
        seller_id = request.GET.get('seller_id', 'default')
        pricing_info = amazon_client.get_product_pricing(sku, seller_id)
        return JsonResponse(pricing_info)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def optimize_listing(request):
    try:
        data = json.loads(request.body)
        asin = data.get('asin')
        focus = data.get('optimization_focus', 'all')
        user_id = data.get('user_id', 'default')
        
        if not asin:
            return JsonResponse({'error': 'ASIN is required'}, status=400)
        
        optimization = amazon_client.optimize_product_listing(asin, focus, user_id)
        return JsonResponse(optimization)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('api/amazon/product/<str:sku>/', views.get_product_info, name='amazon_product_info'),
    path('api/amazon/pricing/<str:sku>/', views.get_product_pricing, name='amazon_product_pricing'),
    path('api/amazon/optimize/', views.optimize_listing, name='amazon_optimize_listing'),
]

# settings.py additions
AMAZON_MCP_BASE_URL = 'http://your-vps-domain.com'  # or localhost for development

# Add to INSTALLED_APPS if creating as Django app
# INSTALLED_APPS = [
#     ...
#     'amazon_mcp_integration',
# ]
"""