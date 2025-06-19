#!/usr/bin/env python3
"""
Amazon SP API MCP HTTP Server
A Model Context Protocol server that provides tools for accessing Amazon SP API via HTTP/SSE
"""

import asyncio
import json
import logging
from typing import Any, Dict, List
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MCP SDK imports
from mcp.server import Server
from mcp.types import Tool
# TODO: Use proper HTTP transport when available
import mcp.types as types

# Amazon SP API client
from sp_api.api import ListingsItems, Products
from sp_api.base import Marketplaces

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Amazon SP API configuration
AMAZON_CREDENTIALS = {
    'refresh_token': os.getenv('AMAZON_REFRESH_TOKEN'),
    'lwa_app_id': os.getenv('AMAZON_LWA_APP_ID'),
    'lwa_client_secret': os.getenv('AMAZON_LWA_CLIENT_SECRET'),
    'aws_access_key': os.getenv('AMAZON_AWS_ACCESS_KEY'),
    'aws_secret_key': os.getenv('AMAZON_AWS_SECRET_KEY'),
    'role_arn': os.getenv('AMAZON_ROLE_ARN')
}

seller_id = os.getenv('SELLER_ID') or ''

class AmazonSPAPIClient:
    """Wrapper for Amazon SP API operations"""

    def __init__(self, marketplace=Marketplaces.DE, user_credentials=None):
        self.marketplace = marketplace
        # Use provided user credentials or fallback to default
        credentials_to_use = user_credentials or AMAZON_CREDENTIALS
        self.credentials = credentials_to_use
        self.user_id = user_credentials.get('user_id') if user_credentials else 'default'

    async def get_product_info(self, sku: str) -> Dict[str, Any]:
        """Get comprehensive product information by SKU"""
        try:
            # Initialize catalog items API
            catalog_api = ListingsItems(credentials=self.credentials, marketplace=self.marketplace)

            # Get product details
            response = catalog_api.get_listings_item(
                sellerId=seller_id, 
                sku=sku, 
                marketplace_id=self.marketplace.value[1], 
                includedData=['attributes', 'summaries', 'issues', 'offers', 'fulfillmentAvailability', 'procurement', 'relationships', 'productTypes']
            )

            if response.payload:
                return self._format_product_data(response.payload)
            else:
                return {"error": "Product not found"}

        except Exception as e:
            logger.error(f"Error fetching product info for SKU {sku}: {str(e)}")
            return {"error": str(e)}

    async def get_product_pricing(self, sku: str) -> Dict[str, Any]:
        """Get pricing information for a product"""
        try:
            pricing_api = Products(credentials=self.credentials, marketplace=self.marketplace)
            response = pricing_api.get_competitive_pricing_for_skus(seller_sku_list=[sku])

            if response.payload:
                return response.payload
            else:
                return {"error": "Pricing not found"}

        except Exception as e:
            logger.error(f"Error fetching pricing for SKU {sku}: {str(e)}")
            return {"error": str(e)}

    def _format_product_data(self, product_data: Dict) -> Dict[str, Any]:
        """Format product data into a clean structure"""
        formatted = {
            "sku": product_data.get('sku'),
            "asin": "",
            "title": "",
            "description": "",
            "features": [],
            "images": [],
            "attributes": {},
            "dimensions": {},
            "sales_rank": {},
            "product_type": ""
        }

        # Extract summaries
        summaries = product_data.get("summaries", [])
        if summaries:
            summary = summaries[0]
            formatted["title"] = summary.get("itemName", "")
            formatted["product_type"] = summary.get("productType", "")

        # Extract attributes
        attributes = product_data.get("attributes", {})
        for key, value in attributes.items():
            if isinstance(value, list) and value:
                formatted["attributes"][key] = [item.get("value") for item in value if item.get("value")]
            elif isinstance(value, dict) and value.get("value"):
                formatted["attributes"][key] = value["value"]

        # Extract bullet points/features
        if "feature_bullet_point" in formatted["attributes"]:
            formatted["features"] = formatted["attributes"]["feature_bullet_point"]

        # Extract description
        if "item_package_description" in formatted["attributes"]:
            formatted["description"] = formatted["attributes"]["item_package_description"]

        # Extract images
        images = product_data.get("images", [])
        for image_set in images:
            for image in image_set.get("images", []):
                formatted["images"].append({
                    "url": image.get("link"),
                    "height": image.get("height"),
                    "width": image.get("width")
                })

        # Extract dimensions
        dimensions = product_data.get("dimensions", [])
        for dim in dimensions:
            formatted["dimensions"] = {
                "height": dim.get("height"),
                "width": dim.get("width"),
                "length": dim.get("length"),
                "weight": dim.get("weight")
            }
            break

        # Extract sales rank
        sales_ranks = product_data.get("salesRanks", [])
        for rank in sales_ranks:
            category = rank.get("displayGroupRanks", [{}])[0]
            formatted["sales_rank"] = {
                "rank": category.get("rank"),
                "category": category.get("title")
            }
            break

        return formatted

# Initialize the MCP server
server = Server("amazon-sp-api")
amazon_client = AmazonSPAPIClient()

@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """List available tools for Amazon SP API"""
    return [
        Tool(
            name="get_amazon_product_info",
            description="Get comprehensive product information from Amazon using SKU. Returns title, description, features, images, attributes, dimensions, and sales rank data.",
            inputSchema={
                "type": "object",
                "properties": {
                    "sku": {
                        "type": "string",
                        "description": "Stock Keeping Unit (SKU) of the product"
                    },
                    "seller_id": {
                        "type": "string",
                        "description": "Optional seller ID for multi-user scenarios",
                        "default": "default"
                    }
                },
                "required": ["sku"]
            }
        ),
        Tool(
            name="get_amazon_product_pricing",
            description="Get current pricing information for an Amazon product",
            inputSchema={
                "type": "object",
                "properties": {
                    "sku": {
                        "type": "string",
                        "description": "Stock Keeping Unit (SKU) of the product"
                    },
                    "seller_id": {
                        "type": "string",
                        "description": "Optional seller ID for multi-user scenarios",
                        "default": "default"
                    }
                },
                "required": ["sku"]
            }
        ),
        Tool(
            name="optimize_product_listing",
            description="Get product data and provide optimization suggestions for title, description, and bullet points",
            inputSchema={
                "type": "object",
                "properties": {
                    "asin": {
                        "type": "string",
                        "description": "Amazon Standard Identification Number (ASIN) of the product"
                    },
                    "optimization_focus": {
                        "type": "string",
                        "description": "What to focus on: 'title', 'description', 'features', or 'all'",
                        "default": "all"
                    },
                    "user_id": {
                        "type": "string",
                        "description": "Optional user ID for multi-user scenarios",
                        "default": "default"
                    }
                },
                "required": ["asin"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Handle tool calls"""
    
    # Get user credentials if provided (for multi-user scenarios)
    user_credentials = None  # In production, load from database/config

    # Initialize client with appropriate credentials
    client = AmazonSPAPIClient(user_credentials=user_credentials)

    if name == "get_amazon_product_info":
        sku = arguments.get("sku")
        if not sku:
            return [types.TextContent(
                type="text",
                text="Error: SKU is required"
            )]

        product_info = await client.get_product_info(sku)
        return [types.TextContent(
            type="text",
            text=json.dumps(product_info, indent=2, ensure_ascii=False)
        )]

    elif name == "get_amazon_product_pricing":
        sku = arguments.get("sku")
        if not sku:
            return [types.TextContent(
                type="text",
                text="Error: SKU is required"
            )]

        pricing_info = await client.get_product_pricing(sku)
        return [types.TextContent(
            type="text",
            text=json.dumps(pricing_info, indent=2, ensure_ascii=False)
        )]

    elif name == "optimize_product_listing":
        asin = arguments.get("asin")
        optimization_focus = arguments.get("optimization_focus", "all")

        if not asin:
            return [types.TextContent(
                type="text",
                text="Error: ASIN is required"
            )]

        # Get product data
        product_info = await client.get_product_info(asin)

        if "error" in product_info:
            return [types.TextContent(
                type="text",
                text=f"Error fetching product data: {product_info['error']}"
            )]

        # Format data for optimization analysis
        optimization_data = {
            "asin": asin,
            "current_data": product_info,
            "focus": optimization_focus,
            "analysis_request": f"Please analyze this Amazon product listing and provide optimization suggestions focusing on {optimization_focus}. Consider SEO keywords, clarity, and conversion optimization."
        }

        return [types.TextContent(
            type="text",
            text=json.dumps(optimization_data, indent=2, ensure_ascii=False)
        )]

    else:
        return [types.TextContent(
            type="text",
            text=f"Unknown tool: {name}"
        )]

async def main():
    """Run the MCP server with SSE transport"""
    # Configuration
    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_PORT", "8000"))
    
    logger.info(f"Starting Amazon SP API MCP Server on {host}:{port}")
    
    # For now, use stdio transport like the original
    # TODO: Implement proper HTTP/SSE transport when MCP SDK supports it
    from mcp.server.stdio import stdio_server
    
    logger.info("MCP Server running with stdio transport")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())