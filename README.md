# Amazon SP API MCP Server

A Model Context Protocol (MCP) server that provides seamless access to Amazon's Selling Partner API. This server enables AI assistants and applications to retrieve product information, pricing data, and generate listing optimization suggestions for Amazon products.

## Features

- **Product Information Retrieval**: Get comprehensive product details by SKU including title, description, features, images, attributes, dimensions, and sales rank
- **Pricing Data Access**: Retrieve current competitive pricing information for products
- **Listing Optimization**: Analyze product data and provide structured suggestions for improving Amazon listings
- **Multi-user Support**: Configurable for different seller accounts and user scenarios
- **German Marketplace**: Pre-configured for Amazon Germany (Marketplaces.DE)

## Quick Start

### Prerequisites

- Python 3.10 or higher
- Amazon SP API credentials (refresh token, LWA app credentials, AWS credentials, role ARN)
- Valid Amazon seller account with API access

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd amztec-mcp-server
```

2. Install dependencies using uv (recommended):
```bash
uv sync
```

Or with pip:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
```

Then edit `.env` with your Amazon SP API credentials:
```env
AMAZON_REFRESH_TOKEN=your_refresh_token
AMAZON_LWA_APP_ID=your_lwa_app_id
AMAZON_LWA_CLIENT_SECRET=your_lwa_client_secret
AMAZON_AWS_ACCESS_KEY=your_aws_access_key
AMAZON_AWS_SECRET_KEY=your_aws_secret_key
AMAZON_ROLE_ARN=your_role_arn
SELLER_ID=your_seller_id
```

### Running the Server

Start the MCP server:
```bash
python amazon_mcp_server.py
```

Test the Amazon SP API connection:
```bash
python test.py
```

## MCP Tools

The server exposes three main tools through the MCP interface:

### 1. get_amazon_product_info
Retrieves comprehensive product information by SKU.

**Parameters:**
- `sku` (required): Stock Keeping Unit of the product
- `seller_id` (optional): Seller ID for multi-user scenarios

**Returns:** JSON object with product title, description, features, images, attributes, dimensions, and sales rank data.

### 2. get_amazon_product_pricing
Gets current pricing information for a product.

**Parameters:**
- `sku` (required): Stock Keeping Unit of the product
- `seller_id` (optional): Seller ID for multi-user scenarios

**Returns:** JSON object with competitive pricing data from Amazon.

### 3. optimize_product_listing
Analyzes product data and provides optimization suggestions.

**Parameters:**
- `asin` (required): Amazon Standard Identification Number
- `optimization_focus` (optional): Focus area - 'title', 'description', 'features', or 'all'
- `user_id` (optional): User ID for multi-user scenarios

**Returns:** Structured data for external analysis and optimization recommendations.

## Configuration

### Amazon SP API Setup

1. Register as an Amazon SP API developer
2. Create a Login with Amazon (LWA) application
3. Set up AWS IAM role with necessary permissions
4. Obtain refresh token through the authorization workflow
5. Configure environment variables in `.env` file

### Marketplace Configuration

The server is configured for German marketplace by default. To change the marketplace, modify the `Marketplaces` parameter in the `AmazonSPAPIClient` initialization:

```python
amazon_client = AmazonSPAPIClient(marketplace=Marketplaces.US)  # For US marketplace
```

## Architecture

- **Single-file MCP server**: All functionality contained in `amazon_mcp_server.py`
- **AmazonSPAPIClient class**: Wrapper for Amazon SP API operations with error handling
- **MCP tool definitions**: Standardized interface for AI assistant integration
- **Async support**: Built on asyncio for efficient concurrent operations

## Development

### Project Structure
```
amztec-mcp-server/
   amazon_mcp_server.py    # Main MCP server implementation
   test.py                 # Test/debug script
   hello.py               # Simple hello world script
   pyproject.toml         # Project configuration
   .env                   # Environment variables (not tracked)
   README.md              # This file
```

### Dependencies

- `mcp[cli]>=1.9.3` - Model Context Protocol framework
- `python-amazon-sp-api>=1.9.36` - Amazon SP API client library
- `python-dotenv>=1.1.0` - Environment variable management

### Testing

Run the test script to verify Amazon SP API connectivity:
```bash
python test.py
```

## Multi-user Support

The server supports multi-user scenarios where different users can have their own Amazon SP API credentials. This is useful for SaaS applications or services managing multiple seller accounts.

## Error Handling

The server includes comprehensive error handling for:
- Invalid or missing credentials
- Network connectivity issues
- Amazon API rate limiting
- Product not found scenarios
- Invalid SKU/ASIN formats

## License

[Add your license information here]

## Contributing

[Add contribution guidelines here]

## Support

For issues and questions:
- Check the Amazon SP API documentation
- Review environment variable configuration
- Ensure proper API permissions and rate limits