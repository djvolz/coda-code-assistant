"""
Web search and fetch tools for accessing online content.

These tools provide web content fetching capabilities with content
processing and markdown conversion.
"""

import re
import time
from typing import Any
from urllib.parse import urlparse

import aiohttp

from .base import BaseTool, ToolParameter, ToolParameterType, ToolResult, ToolSchema, tool_registry


class FetchUrlTool(BaseTool):
    """Tool for fetching content from URLs."""

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name="fetch_url",
            description="Fetch content from a URL and optionally convert to markdown",
            category="web",
            parameters={
                "url": ToolParameter(
                    type=ToolParameterType.STRING, description="URL to fetch content from"
                ),
                "max_length": ToolParameter(
                    type=ToolParameterType.INTEGER,
                    description="Maximum content length to return",
                    default=10000,
                    required=False,
                    min_value=100,
                    max_value=100000,
                ),
                "timeout": ToolParameter(
                    type=ToolParameterType.INTEGER,
                    description="Request timeout in seconds",
                    default=30,
                    required=False,
                    min_value=5,
                    max_value=120,
                ),
                "format": ToolParameter(
                    type=ToolParameterType.STRING,
                    description="Output format: 'raw', 'text', or 'markdown'",
                    default="markdown",
                    required=False,
                    enum=["raw", "text", "markdown"],
                ),
                "follow_redirects": ToolParameter(
                    type=ToolParameterType.BOOLEAN,
                    description="Whether to follow HTTP redirects",
                    default=True,
                    required=False,
                ),
                "user_agent": ToolParameter(
                    type=ToolParameterType.STRING,
                    description="Custom User-Agent string",
                    default="Coda-AI-Assistant/1.0",
                    required=False,
                ),
            },
        )

    async def execute(self, arguments: dict[str, Any]) -> ToolResult:
        url = arguments["url"].strip()
        max_length = arguments.get("max_length", 10000)
        timeout = arguments.get("timeout", 30)
        output_format = arguments.get("format", "markdown")
        follow_redirects = arguments.get("follow_redirects", True)
        user_agent = arguments.get("user_agent", "Coda-AI-Assistant/1.0")

        # Validate URL
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return ToolResult(
                    success=False,
                    error="Invalid URL format",
                    tool="fetch_url",
                    metadata={"url": url},
                )

            if parsed.scheme not in ["http", "https"]:
                return ToolResult(
                    success=False,
                    error="Only HTTP and HTTPS URLs are supported",
                    tool="fetch_url",
                    metadata={"url": url},
                )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"URL parsing failed: {str(e)}",
                tool="fetch_url",
                metadata={"url": url},
            )

        start_time = time.time()

        try:
            connector = aiohttp.TCPConnector(limit=10)
            timeout_config = aiohttp.ClientTimeout(total=timeout)

            async with aiohttp.ClientSession(
                connector=connector, timeout=timeout_config, headers={"User-Agent": user_agent}
            ) as session:
                async with session.get(
                    url,
                    allow_redirects=follow_redirects,
                    ssl=False,  # Allow self-signed certificates
                ) as response:
                    # Check response status
                    if response.status >= 400:
                        return ToolResult(
                            success=False,
                            error=f"HTTP {response.status}: {response.reason}",
                            tool="fetch_url",
                            metadata={
                                "url": url,
                                "status_code": response.status,
                                "final_url": str(response.url),
                            },
                        )

                    # Get content type
                    content_type = response.headers.get("content-type", "").lower()

                    # Read content
                    content = await response.read()

                    # Decode content
                    if "charset=" in content_type:
                        encoding = content_type.split("charset=")[1].split(";")[0]
                    else:
                        encoding = "utf-8"

                    try:
                        text_content = content.decode(encoding)
                    except UnicodeDecodeError:
                        text_content = content.decode("utf-8", errors="ignore")

                    # Process content based on format
                    if output_format == "raw":
                        processed_content = text_content
                    elif output_format == "text":
                        processed_content = self._html_to_text(text_content)
                    else:  # markdown
                        processed_content = self._html_to_markdown(text_content)

                    # Apply length limit
                    if len(processed_content) > max_length:
                        processed_content = (
                            processed_content[:max_length] + "\n\n... (content truncated)"
                        )

                    fetch_time = time.time() - start_time

                    return ToolResult(
                        success=True,
                        result=processed_content,
                        tool="fetch_url",
                        metadata={
                            "url": url,
                            "final_url": str(response.url),
                            "status_code": response.status,
                            "content_type": content_type,
                            "content_length": len(content),
                            "processed_length": len(processed_content),
                            "fetch_time": fetch_time,
                            "format": output_format,
                        },
                    )

        except TimeoutError:
            return ToolResult(
                success=False,
                error=f"Request timed out after {timeout} seconds",
                tool="fetch_url",
                metadata={"url": url, "timeout": timeout},
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Failed to fetch URL: {str(e)}",
                tool="fetch_url",
                metadata={"url": url},
            )

    def _html_to_text(self, html: str) -> str:
        """Convert HTML to plain text."""
        # Remove script and style elements
        html = re.sub(r"<script[^>]*>.*?</script[^>]*>", "", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<style[^>]*>.*?</style[^>]*>", "", html, flags=re.DOTALL | re.IGNORECASE)

        # Remove HTML tags
        text = re.sub(r"<[^>]+>", "", html)

        # Clean up whitespace
        text = re.sub(r"\n\s*\n", "\n\n", text)
        text = re.sub(r" +", " ", text)

        return text.strip()

    def _html_to_markdown(self, html: str) -> str:
        """Convert HTML to markdown format."""
        # Remove script and style elements
        html = re.sub(r"<script[^>]*>.*?</script[^>]*>", "", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<style[^>]*>.*?</style[^>]*>", "", html, flags=re.DOTALL | re.IGNORECASE)

        # Convert common HTML elements to markdown
        conversions = [
            # Headers
            (r"<h1[^>]*>(.*?)</h1>", r"# \1\n"),
            (r"<h2[^>]*>(.*?)</h2>", r"## \1\n"),
            (r"<h3[^>]*>(.*?)</h3>", r"### \1\n"),
            (r"<h4[^>]*>(.*?)</h4>", r"#### \1\n"),
            (r"<h5[^>]*>(.*?)</h5>", r"##### \1\n"),
            (r"<h6[^>]*>(.*?)</h6>", r"###### \1\n"),
            # Text formatting
            (r"<strong[^>]*>(.*?)</strong>", r"**\1**"),
            (r"<b[^>]*>(.*?)</b>", r"**\1**"),
            (r"<em[^>]*>(.*?)</em>", r"*\1*"),
            (r"<i[^>]*>(.*?)</i>", r"*\1*"),
            (r"<code[^>]*>(.*?)</code>", r"`\1`"),
            # Links
            (r'<a[^>]*href=["\']([^"\']*)["\'][^>]*>(.*?)</a>', r"[\2](\1)"),
            # Lists
            (r"<li[^>]*>(.*?)</li>", r"- \1\n"),
            (r"<ul[^>]*>", ""),
            (r"</ul>", "\n"),
            (r"<ol[^>]*>", ""),
            (r"</ol>", "\n"),
            # Paragraphs and breaks
            (r"<p[^>]*>(.*?)</p>", r"\1\n\n"),
            (r"<br[^>]*/?>", "\n"),
            (r"<hr[^>]*/?>", "\n---\n"),
            # Code blocks
            (r"<pre[^>]*>(.*?)</pre>", r"```\n\1\n```\n"),
            # Images
            (r'<img[^>]*src=["\']([^"\']*)["\'][^>]*alt=["\']([^"\']*)["\'][^>]*/?>', r"![\2](\1)"),
            (r'<img[^>]*alt=["\']([^"\']*)["\'][^>]*src=["\']([^"\']*)["\'][^>]*/?>', r"![\1](\2)"),
            (r'<img[^>]*src=["\']([^"\']*)["\'][^>]*/?>', r"![](\1)"),
        ]

        text = html
        for pattern, replacement in conversions:
            text = re.sub(pattern, replacement, text, flags=re.DOTALL | re.IGNORECASE)

        # Remove remaining HTML tags
        text = re.sub(r"<[^>]+>", "", text)

        # Clean up whitespace
        text = re.sub(r"\n\s*\n\s*\n", "\n\n", text)
        text = re.sub(r" +", " ", text)

        return text.strip()


class SearchWebTool(BaseTool):
    """Tool for searching the web using DuckDuckGo."""

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name="search_web",
            description="Search the web using DuckDuckGo search engine",
            category="web",
            parameters={
                "query": ToolParameter(type=ToolParameterType.STRING, description="Search query"),
                "max_results": ToolParameter(
                    type=ToolParameterType.INTEGER,
                    description="Maximum number of results to return",
                    default=5,
                    required=False,
                    min_value=1,
                    max_value=20,
                ),
                "region": ToolParameter(
                    type=ToolParameterType.STRING,
                    description="Search region (e.g., 'us-en', 'uk-en', 'de-de')",
                    default="us-en",
                    required=False,
                ),
                "safe_search": ToolParameter(
                    type=ToolParameterType.STRING,
                    description="Safe search setting",
                    default="moderate",
                    required=False,
                    enum=["strict", "moderate", "off"],
                ),
                "time_range": ToolParameter(
                    type=ToolParameterType.STRING,
                    description="Time range for results",
                    required=False,
                    enum=["day", "week", "month", "year"],
                ),
            },
        )

    async def execute(self, arguments: dict[str, Any]) -> ToolResult:
        query = arguments["query"].strip()
        max_results = arguments.get("max_results", 5)
        # These parameters are reserved for future use
        # region = arguments.get("region", "us-en")
        # safe_search = arguments.get("safe_search", "moderate")
        # time_range = arguments.get("time_range")

        if not query:
            return ToolResult(
                success=False, error="Search query cannot be empty", tool="search_web"
            )

        try:
            # Use DuckDuckGo Instant Answer API
            search_url = "https://api.duckduckgo.com/"
            params = {"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"}

            start_time = time.time()

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.9",
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(search_url, params=params, headers=headers) as response:
                    if response.status != 200:
                        return ToolResult(
                            success=False,
                            error=f"Search API returned status {response.status}",
                            tool="search_web",
                            metadata={"query": query},
                        )

                    # Check content type
                    content_type = response.headers.get("content-type", "").lower()
                    if "javascript" in content_type or "html" in content_type:
                        # DuckDuckGo is returning HTML/JS instead of JSON
                        # Fall back to scraping
                        results = await self._scrape_search_results(query, max_results)
                        if results:
                            # Format results
                            output = f"Search results for: {query}\n\n"
                            for i, result in enumerate(results[:max_results], 1):
                                output += f"{i}. **{result['title']}**\n"
                                output += f"   {result['snippet'][:200]}{'...' if len(result['snippet']) > 200 else ''}\n"
                                if result["url"]:
                                    output += f"   URL: {result['url']}\n"
                                output += f"   Source: {result['source']}\n\n"

                            return ToolResult(
                                success=True,
                                result=output,
                                tool="search_web",
                                metadata={
                                    "query": query,
                                    "results_count": len(results),
                                    "search_time": time.time() - start_time,
                                    "results": results[:max_results],
                                },
                            )
                        else:
                            return ToolResult(
                                success=False,
                                error="Search service is currently unavailable. Please try again later.",
                                tool="search_web",
                                metadata={"query": query},
                            )

                    try:
                        data = await response.json()
                    except Exception as e:
                        # Try fallback scraping
                        results = await self._scrape_search_results(query, max_results)
                        if results:
                            # Format results
                            output = f"Search results for: {query}\n\n"
                            for i, result in enumerate(results[:max_results], 1):
                                output += f"{i}. **{result['title']}**\n"
                                output += f"   {result['snippet'][:200]}{'...' if len(result['snippet']) > 200 else ''}\n"
                                if result["url"]:
                                    output += f"   URL: {result['url']}\n"
                                output += f"   Source: {result['source']}\n\n"

                            return ToolResult(
                                success=True,
                                result=output,
                                tool="search_web",
                                metadata={
                                    "query": query,
                                    "results_count": len(results),
                                    "search_time": time.time() - start_time,
                                    "results": results[:max_results],
                                },
                            )
                        else:
                            return ToolResult(
                                success=False,
                                error=f"Failed to parse search results: {str(e)}",
                                tool="search_web",
                                metadata={"query": query},
                            )

                    # Extract results
                    results = []

                    # Add instant answer if available
                    if data.get("Answer"):
                        results.append(
                            {
                                "type": "instant_answer",
                                "title": "Instant Answer",
                                "snippet": data["Answer"],
                                "url": data.get("AnswerSource", ""),
                                "source": "DuckDuckGo",
                            }
                        )

                    # Add abstract if available
                    if data.get("Abstract"):
                        results.append(
                            {
                                "type": "abstract",
                                "title": data.get("Heading", "Abstract"),
                                "snippet": data["Abstract"],
                                "url": data.get("AbstractURL", ""),
                                "source": data.get("AbstractSource", "Wikipedia"),
                            }
                        )

                    # Add related topics
                    for topic in data.get("RelatedTopics", [])[:max_results]:
                        if isinstance(topic, dict) and "Text" in topic:
                            results.append(
                                {
                                    "type": "related_topic",
                                    "title": topic.get("FirstURL", "")
                                    .split("/")[-1]
                                    .replace("_", " "),
                                    "snippet": topic["Text"],
                                    "url": topic.get("FirstURL", ""),
                                    "source": "DuckDuckGo",
                                }
                            )

            # If no results from instant API, fall back to web scraping search
            if not results:
                results = await self._scrape_search_results(query, max_results)

            # Format results
            if not results:
                return ToolResult(
                    success=True,
                    result=f"No results found for query: {query}",
                    tool="search_web",
                    metadata={
                        "query": query,
                        "results_count": 0,
                        "search_time": time.time() - start_time,
                    },
                )

            output = f"Search results for: {query}\n\n"
            for i, result in enumerate(results[:max_results], 1):
                output += f"{i}. **{result['title']}**\n"
                output += (
                    f"   {result['snippet'][:200]}{'...' if len(result['snippet']) > 200 else ''}\n"
                )
                if result["url"]:
                    output += f"   URL: {result['url']}\n"
                output += f"   Source: {result['source']}\n\n"

            return ToolResult(
                success=True,
                result=output,
                tool="search_web",
                metadata={
                    "query": query,
                    "results_count": len(results),
                    "search_time": time.time() - start_time,
                    "results": results[:max_results],
                },
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Search failed: {str(e)}",
                tool="search_web",
                metadata={"query": query},
            )

    async def _scrape_search_results(self, query: str, max_results: int) -> list:
        """Fallback method to scrape search results from DuckDuckGo."""
        try:
            search_url = "https://html.duckduckgo.com/html/"
            params = {"q": query}
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(search_url, params=params, headers=headers) as response:
                    if response.status != 200:
                        return []

                    html = await response.text()

                    # Simple regex-based extraction
                    results = []

                    # Look for result blocks
                    result_blocks = re.findall(
                        r'<div[^>]*class="result[^"]*"[^>]*>(.*?)</div>\s*</div>', html, re.DOTALL
                    )

                    for block in result_blocks[:max_results]:
                        # Extract URL and title
                        url_match = re.search(
                            r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
                            block,
                            re.DOTALL,
                        )
                        if not url_match:
                            continue

                        url, title = url_match.groups()

                        # Extract snippet
                        snippet_match = re.search(
                            r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>', block, re.DOTALL
                        )
                        snippet = snippet_match.group(1) if snippet_match else ""

                        # Clean up HTML
                        title = re.sub(r"<[^>]+>", "", title).strip()
                        title = re.sub(r"\s+", " ", title)
                        snippet = re.sub(r"<[^>]+>", "", snippet).strip()
                        snippet = re.sub(r"\s+", " ", snippet)

                        if title and url:
                            results.append(
                                {
                                    "type": "web_result",
                                    "title": title,
                                    "snippet": snippet,
                                    "url": url,
                                    "source": "DuckDuckGo",
                                }
                            )

                    # If no results found with the new pattern, try the old pattern
                    if not results:
                        link_pattern = r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>'
                        snippet_pattern = r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>'

                        links = re.findall(link_pattern, html, re.DOTALL)
                        snippets = re.findall(snippet_pattern, html, re.DOTALL)

                        for i, (url, title) in enumerate(links[:max_results]):
                            snippet = snippets[i] if i < len(snippets) else ""

                            # Clean up HTML
                            title = re.sub(r"<[^>]+>", "", title).strip()
                            snippet = re.sub(r"<[^>]+>", "", snippet).strip()

                            if title:
                                results.append(
                                    {
                                        "type": "web_result",
                                        "title": title,
                                        "snippet": snippet,
                                        "url": url,
                                        "source": "DuckDuckGo",
                                    }
                                )

                    return results

        except Exception:
            return []


# Register tools
tool_registry.register(FetchUrlTool())
tool_registry.register(SearchWebTool())
