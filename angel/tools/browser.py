"""Web tools: open URLs and searches in the user's default browser."""

from __future__ import annotations

import urllib.parse
import webbrowser

from angel.tools.registry import ToolRegistry, ToolResult, ToolSpec


def open_url(url: str) -> ToolResult:
    url = url.strip()
    if not url:
        return ToolResult(False, "no URL given")
    if not url.lower().startswith(("http://", "https://")):
        url = "https://" + url
    parsed = urllib.parse.urlparse(url)
    if not parsed.netloc or "." not in parsed.netloc:
        return ToolResult(False, f"'{url}' does not look like a valid web address")
    if webbrowser.open(url):
        return ToolResult(True, f"opened {url} in the default browser")
    return ToolResult(False, "no browser could be opened")


def search_web(query: str) -> ToolResult:
    query = query.strip()
    if not query:
        return ToolResult(False, "no search query given")
    url = "https://www.google.com/search?q=" + urllib.parse.quote_plus(query)
    if webbrowser.open(url):
        return ToolResult(True, f"opened a web search for: {query}")
    return ToolResult(False, "no browser could be opened")


def register(registry: ToolRegistry, _settings) -> None:
    registry.register(ToolSpec(
        name="open_url",
        description="Open a URL in the user's default web browser.",
        parameters={"url": {"type": "string", "description": "The web address"}},
        required=["url"], func=open_url))
    registry.register(ToolSpec(
        name="search_web",
        description="Open a web search for a query in the user's default browser. "
                    "This shows results to the user; it does not return them to you.",
        parameters={"query": {"type": "string", "description": "Search terms"}},
        required=["query"], func=search_web))
