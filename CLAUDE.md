# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an Amazon SP API MCP (Model Context Protocol) Server that provides tools for accessing Amazon's Selling Partner API. The server exposes three main tools through the MCP interface:
- Product information retrieval by SKU
- Product pricing information
- Product listing optimization suggestions

## Architecture

The project follows a simple single-file MCP server architecture:

- `amazon_mcp_server.py` - Main MCP server implementation containing:
  - `AmazonSPAPIClient` class - Wrapper for Amazon SP API operations
  - MCP tool definitions and handlers
  - Server initialization and stdio communication setup
- `test.py` - Test/debug script for Amazon SP API calls
- `hello.py` - Simple hello world script

## Development Commands

### Environment Setup
```bash
# Install dependencies
uv sync

# Run the MCP server
python amazon_mcp_server.py

# Test Amazon SP API connection
python test.py
```

### Required Environment Variables
The server requires Amazon SP API credentials in `.env`:
- `AMAZON_REFRESH_TOKEN`
- `AMAZON_LWA_APP_ID` 
- `AMAZON_LWA_CLIENT_SECRET`
- `AMAZON_AWS_ACCESS_KEY`
- `AMAZON_AWS_SECRET_KEY`
- `AMAZON_ROLE_ARN`
- `SELLER_ID`

## Key Dependencies

- `mcp[cli]>=1.9.3` - Model Context Protocol framework
- `python-amazon-sp-api>=1.9.36` - Amazon SP API client
- `python-dotenv>=1.1.0` - Environment variable management

## MCP Tools

1. **get_amazon_product_info** - Retrieves comprehensive product data by SKU including title, description, features, images, attributes, dimensions, and sales rank
2. **get_amazon_product_pricing** - Gets current pricing information for a product by SKU  
3. **optimize_product_listing** - Analyzes product data and provides optimization suggestions (currently returns formatted data for external analysis)

The server is configured for German marketplace (`Marketplaces.DE`) by default and supports multi-user scenarios through optional user credentials.