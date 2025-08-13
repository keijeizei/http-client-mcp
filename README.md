# HTTP Client MCP Server

A Model Context Protocol (MCP) server that provides HTTP client capabilities.

## Features

- Full HTTP method support (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS)
- Custom headers and query parameters
- Request body support (JSON, form data, text)
- Configurable timeouts and SSL verification
- Detailed response information including status codes and headers

## Setup for Claude Desktop

### 1. Install Dependencies

```bash
pip install fastmcp httpx pydantic
```

Or use the requirements file:

```bash
pip install -r requirements.txt
```

### 2. Configure Claude Desktop

Add this server to your Claude Desktop configuration file:

**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`  
**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`  
**Linux**: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "http-client": {
      "command": "python",
      "args": ["/path/to/http-client-mcp/src/http_client_mcp/server.py"]
    }
  }
}
```

**Note**: Replace `/path/to/http-client-mcp` with the actual location where you cloned this repository.

### 3. Restart Claude Desktop

After saving the configuration, restart Claude Desktop to load the MCP server.

## Usage Examples

Once configured, you can use these tools:

**Simple GET request:**

```
Use the http_get tool to fetch data from https://api.github.com/users/octocat
```

**POST request with JSON:**

```
Use the http_post tool to send {"name": "test"} to https://httpbin.org/post
```

**Custom request:**

```
Use the http_request tool to make a PUT request to https://httpbin.org/put with custom headers
```

## Available Tools

- `http_request` - Full control over HTTP requests
- `http_get` - Simplified GET requests
- `http_post` - Simplified POST requests
- `http_put` - Simplified PUT requests
- `http_delete` - Simplified DELETE requests
- `http_patch` - Simplified PATCH requests

## License

MIT License - see [LICENSE](LICENSE) file for details.

## AI-Assisted Development

This repository was created with the assistance of AI tools. The time invested in building a solution should not exceed the time it saves compared to not building it at all.
