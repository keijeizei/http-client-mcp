#!/usr/bin/env python3
"""
HTTP Client MCP Server

A Model Context Protocol server that provides comprehensive tools for making HTTP requests
with full support for all HTTP methods, custom headers, request bodies, and more.
"""

import json
import logging
from typing import Any, Dict, Optional, Union
from urllib.parse import urlencode

import httpx
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field, field_validator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("http-client")


class HttpResponse(BaseModel):
    """Structured HTTP Response model."""

    status_code: int
    headers: Dict[str, str]
    content: str
    content_type: Optional[str] = None
    elapsed_ms: float


class HttpRequestParams(BaseModel):
    """Validated HTTP Request parameters."""

    url: str = Field(description="The URL to make the request to")
    method: str = Field(
        default="GET",
        description="HTTP method (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS)",
    )
    headers: Optional[Dict[str, str]] = Field(
        default=None, description="Custom headers as key-value pairs"
    )
    params: Optional[Dict[str, str]] = Field(
        default=None, description="Query parameters as key-value pairs"
    )
    body: Optional[Union[str, Dict[str, Any]]] = Field(
        default=None, description="Request body (JSON object, form data, or raw string)"
    )
    body_type: str = Field(
        default="json", description="Body type: 'json', 'form', 'text', or 'raw'"
    )
    timeout: float = Field(
        default=30.0, ge=0.1, le=300.0, description="Request timeout in seconds (0.1-300)"
    )
    follow_redirects: bool = Field(default=True, description="Whether to follow redirects")
    verify_ssl: bool = Field(default=True, description="Whether to verify SSL certificates")

    @field_validator("method")
    @classmethod
    def validate_method(cls, v: str) -> str:
        """Validate HTTP method."""
        valid_methods = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}
        method_upper = v.upper()
        if method_upper not in valid_methods:
            raise ValueError(f"Invalid HTTP method: {v}. Must be one of {valid_methods}")
        return method_upper

    @field_validator("body_type")
    @classmethod
    def validate_body_type(cls, v: str) -> str:
        """Validate body type."""
        valid_types = {"json", "form", "text", "raw"}
        if v.lower() not in valid_types:
            raise ValueError(f"Invalid body type: {v}. Must be one of {valid_types}")
        return v.lower()

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Basic URL validation."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v


async def make_http_request(params: HttpRequestParams) -> HttpResponse:
    """
    Execute an HTTP request with the given parameters.

    Args:
        params: Validated HTTP request parameters

    Returns:
        HttpResponse object containing the response data

    Raises:
        Exception: On timeout, request error, or unexpected errors
    """
    headers = params.headers or {}

    request_body = None
    if params.body is not None:
        if params.body_type == "json":
            if isinstance(params.body, dict):
                request_body = json.dumps(params.body)
                headers.setdefault("Content-Type", "application/json")
            else:
                try:
                    json.loads(params.body)
                    request_body = params.body
                    headers.setdefault("Content-Type", "application/json")
                except (json.JSONDecodeError, TypeError):
                    raise ValueError("Invalid JSON body provided")

        elif params.body_type == "form":
            if isinstance(params.body, dict):
                request_body = urlencode(params.body)
                headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
            else:
                request_body = params.body
                headers.setdefault("Content-Type", "application/x-www-form-urlencoded")

        elif params.body_type == "text":
            request_body = str(params.body)
            headers.setdefault("Content-Type", "text/plain")

        else:  # raw
            request_body = (
                params.body if isinstance(params.body, (str, bytes)) else str(params.body)
            )

    async with httpx.AsyncClient(
        timeout=params.timeout,
        follow_redirects=params.follow_redirects,
        verify=params.verify_ssl,
    ) as client:
        try:
            response = await client.request(
                method=params.method,
                url=params.url,
                headers=headers,
                params=params.params,
                content=request_body,
            )

            content = response.text
            content_type = response.headers.get("content-type")

            return HttpResponse(
                status_code=response.status_code,
                headers=dict(response.headers),
                content=content,
                content_type=content_type,
                elapsed_ms=response.elapsed.total_seconds() * 1000,
            )

        except httpx.TimeoutException:
            raise Exception(f"Request timed out after {params.timeout} seconds")
        except httpx.RequestError as e:
            raise Exception(f"Request failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in HTTP request: {e}", exc_info=True)
            raise Exception(f"Unexpected error: {str(e)}")


@mcp.tool()
async def http_request(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, str]] = None,
    body: Optional[Union[str, Dict[str, Any]]] = None,
    body_type: str = "json",
    timeout: float = 30.0,
    follow_redirects: bool = True,
    verify_ssl: bool = True,
) -> str:
    """
    Make an HTTP request to any URL with full customization support.

    Args:
        url: The URL to make the request to
        method: HTTP method (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS)
        headers: Custom headers as key-value pairs
        params: Query parameters as key-value pairs
        body: Request body (JSON object, form data, or raw string)
        body_type: Body type - 'json', 'form', 'text', or 'raw'
        timeout: Request timeout in seconds (0.1-300, default: 30.0)
        follow_redirects: Whether to follow redirects (default: True)
        verify_ssl: Whether to verify SSL certificates (default: True)

    Returns:
        JSON string containing the response with status, headers, and content

    Example:
        >>> await http_request(
        ...     url="https://api.example.com/users",
        ...     method="POST",
        ...     body={"name": "John", "email": "john@example.com"},
        ...     headers={"Authorization": "Bearer token123"}
        ... )
    """
    try:
        request_params = HttpRequestParams(
            url=url,
            method=method,
            headers=headers,
            params=params,
            body=body,
            body_type=body_type,
            timeout=timeout,
            follow_redirects=follow_redirects,
            verify_ssl=verify_ssl,
        )

        response = await make_http_request(request_params)

        result = {
            "request": {
                "method": request_params.method,
                "url": url,
                "headers": headers or {},
                "params": params or {},
                "body_type": body_type if body else None,
                "timeout": timeout,
            },
            "response": {
                "status_code": response.status_code,
                "status_text": _get_status_text(response.status_code),
                "headers": response.headers,
                "content_type": response.content_type,
                "content": response.content,
                "elapsed_ms": round(response.elapsed_ms, 2),
            },
            "success": 200 <= response.status_code < 300,
        }

        return json.dumps(result, indent=2)

    except Exception as e:
        error_result = {
            "error": True,
            "message": str(e),
            "request": {
                "method": method.upper(),
                "url": url,
                "headers": headers or {},
                "params": params or {},
            },
        }
        return json.dumps(error_result, indent=2)


@mcp.tool()
async def http_get(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, str]] = None,
    timeout: float = 30.0,
) -> str:
    """
    Make a GET request (convenience method).

    Args:
        url: The URL to GET
        headers: Custom headers
        params: Query parameters
        timeout: Request timeout in seconds

    Returns:
        JSON string with response data
    """
    return await http_request(
        url=url, method="GET", headers=headers, params=params, timeout=timeout
    )


@mcp.tool()
async def http_post(
    url: str,
    body: Optional[Union[str, Dict[str, Any]]] = None,
    headers: Optional[Dict[str, str]] = None,
    body_type: str = "json",
    timeout: float = 30.0,
) -> str:
    """
    Make a POST request (convenience method).

    Args:
        url: The URL to POST to
        body: Request body
        headers: Custom headers
        body_type: Body type ('json', 'form', 'text', 'raw')
        timeout: Request timeout in seconds

    Returns:
        JSON string with response data
    """
    return await http_request(
        url=url,
        method="POST",
        body=body,
        headers=headers,
        body_type=body_type,
        timeout=timeout,
    )


@mcp.tool()
async def http_put(
    url: str,
    body: Optional[Union[str, Dict[str, Any]]] = None,
    headers: Optional[Dict[str, str]] = None,
    body_type: str = "json",
    timeout: float = 30.0,
) -> str:
    """
    Make a PUT request (convenience method).

    Args:
        url: The URL to PUT to
        body: Request body
        headers: Custom headers
        body_type: Body type ('json', 'form', 'text', 'raw')
        timeout: Request timeout in seconds

    Returns:
        JSON string with response data
    """
    return await http_request(
        url=url,
        method="PUT",
        body=body,
        headers=headers,
        body_type=body_type,
        timeout=timeout,
    )


@mcp.tool()
async def http_delete(
    url: str, headers: Optional[Dict[str, str]] = None, timeout: float = 30.0
) -> str:
    """
    Make a DELETE request (convenience method).

    Args:
        url: The URL to DELETE
        headers: Custom headers
        timeout: Request timeout in seconds

    Returns:
        JSON string with response data
    """
    return await http_request(url=url, method="DELETE", headers=headers, timeout=timeout)


@mcp.tool()
async def http_patch(
    url: str,
    body: Optional[Union[str, Dict[str, Any]]] = None,
    headers: Optional[Dict[str, str]] = None,
    body_type: str = "json",
    timeout: float = 30.0,
) -> str:
    """
    Make a PATCH request (convenience method).

    Args:
        url: The URL to PATCH
        body: Request body
        headers: Custom headers
        body_type: Body type ('json', 'form', 'text', 'raw')
        timeout: Request timeout in seconds

    Returns:
        JSON string with response data
    """
    return await http_request(
        url=url,
        method="PATCH",
        body=body,
        headers=headers,
        body_type=body_type,
        timeout=timeout,
    )


def _get_status_text(status_code: int) -> str:
    """Get human-readable status text for HTTP status codes."""
    status_texts = {
        100: "Continue",
        101: "Switching Protocols",
        200: "OK",
        201: "Created",
        202: "Accepted",
        204: "No Content",
        301: "Moved Permanently",
        302: "Found",
        304: "Not Modified",
        307: "Temporary Redirect",
        308: "Permanent Redirect",
        400: "Bad Request",
        401: "Unauthorized",
        403: "Forbidden",
        404: "Not Found",
        405: "Method Not Allowed",
        409: "Conflict",
        422: "Unprocessable Entity",
        429: "Too Many Requests",
        500: "Internal Server Error",
        502: "Bad Gateway",
        503: "Service Unavailable",
        504: "Gateway Timeout",
    }

    if status_code in status_texts:
        return f"{status_code} {status_texts[status_code]}"
    elif 200 <= status_code < 300:
        return f"{status_code} Success"
    elif 300 <= status_code < 400:
        return f"{status_code} Redirection"
    elif 400 <= status_code < 500:
        return f"{status_code} Client Error"
    elif 500 <= status_code < 600:
        return f"{status_code} Server Error"
    else:
        return f"{status_code} Unknown"


@mcp.resource("http://status-codes")
async def http_status_codes() -> str:
    """Common HTTP status codes reference."""
    return """# HTTP Status Codes Reference

## 1xx Informational
- 100 Continue
- 101 Switching Protocols
- 102 Processing
- 103 Early Hints

## 2xx Success
- 200 OK
- 201 Created
- 202 Accepted
- 203 Non-Authoritative Information
- 204 No Content
- 205 Reset Content
- 206 Partial Content
- 207 Multi-Status
- 208 Already Reported
- 226 IM Used

## 3xx Redirection
- 300 Multiple Choices
- 301 Moved Permanently
- 302 Found
- 303 See Other
- 304 Not Modified
- 305 Use Proxy (Deprecated)
- 307 Temporary Redirect
- 308 Permanent Redirect

## 4xx Client Error
- 400 Bad Request
- 401 Unauthorized
- 402 Payment Required
- 403 Forbidden
- 404 Not Found
- 405 Method Not Allowed
- 406 Not Acceptable
- 407 Proxy Authentication Required
- 408 Request Timeout
- 409 Conflict
- 410 Gone
- 411 Length Required
- 412 Precondition Failed
- 413 Payload Too Large
- 414 URI Too Long
- 415 Unsupported Media Type
- 416 Range Not Satisfiable
- 417 Expectation Failed
- 418 I'm a teapot
- 421 Misdirected Request
- 422 Unprocessable Entity
- 423 Locked
- 424 Failed Dependency
- 425 Too Early
- 426 Upgrade Required
- 428 Precondition Required
- 429 Too Many Requests
- 431 Request Header Fields Too Large
- 451 Unavailable For Legal Reasons

## 5xx Server Error
- 500 Internal Server Error
- 501 Not Implemented
- 502 Bad Gateway
- 503 Service Unavailable
- 504 Gateway Timeout
- 505 HTTP Version Not Supported
- 506 Variant Also Negotiates
- 507 Insufficient Storage
- 508 Loop Detected
- 510 Not Extended
- 511 Network Authentication Required
"""


if __name__ == "__main__":
    mcp.run()
