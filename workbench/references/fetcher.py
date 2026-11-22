from __future__ import annotations

import ipaddress
import re
import socket
from collections.abc import Callable
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import httpx


class ReferenceFetchError(ValueError):
    pass


class _ReadableHTMLParser(HTMLParser):
    _ignored_tags = {"script", "style", "noscript", "svg", "nav", "footer", "form"}
    _break_tags = {"article", "main", "section", "div", "p", "h1", "h2", "h3", "li", "blockquote", "br"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._ignored_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, _attrs) -> None:
        if tag in self._ignored_tags:
            self._ignored_depth += 1
        elif not self._ignored_depth and tag in self._break_tags:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self._ignored_tags and self._ignored_depth:
            self._ignored_depth -= 1
        elif not self._ignored_depth and tag in self._break_tags:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth and data.strip():
            self.parts.append(data)

    def readable_text(self) -> str:
        lines = [re.sub(r"\s+", " ", line).strip() for line in "".join(self.parts).splitlines()]
        return "\n".join(dict.fromkeys(line for line in lines if line))


def extract_readable_text(html: str) -> str:
    parser = _ReadableHTMLParser()
    parser.feed(html)
    parser.close()
    text = parser.readable_text()
    if not text:
        raise ReferenceFetchError("链接页面没有可读取的正文")
    return text


def _system_resolver(host: str) -> list[str]:
    return sorted({item[4][0] for item in socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)})


class SafeReferenceFetcher:
    def __init__(
        self,
        *,
        resolver: Callable[[str], list[str]] = _system_resolver,
        transport: httpx.BaseTransport | None = None,
        max_redirects: int = 3,
        max_bytes: int = 1_000_000,
        timeout_seconds: float = 10,
    ) -> None:
        self.resolver = resolver
        self.max_redirects = max_redirects
        self.max_bytes = max_bytes
        self.client = httpx.Client(
            transport=transport,
            follow_redirects=False,
            timeout=timeout_seconds,
            headers={"User-Agent": "PublicityWorkbench/0.1"},
        )

    def _validate_url(self, url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            raise ReferenceFetchError("只允许公开 HTTP 或 HTTPS 地址")
        try:
            ipaddress.ip_address(parsed.hostname)
            addresses = [parsed.hostname]
        except ValueError:
            try:
                addresses = self.resolver(parsed.hostname)
            except OSError as exc:
                raise ReferenceFetchError("链接域名无法解析") from exc
        if not addresses:
            raise ReferenceFetchError("链接域名没有公开地址")
        if any(not ipaddress.ip_address(value).is_global for value in addresses):
            raise ReferenceFetchError("拒绝访问本机、内网或保留地址")

    def fetch(self, url: str) -> str:
        current = url
        for redirect_count in range(self.max_redirects + 1):
            self._validate_url(current)
            try:
                response = self.client.get(current)
            except httpx.HTTPError as exc:
                raise ReferenceFetchError("读取公开链接失败") from exc
            if response.is_redirect:
                if redirect_count >= self.max_redirects or "location" not in response.headers:
                    raise ReferenceFetchError("链接重定向次数过多")
                current = urljoin(current, response.headers["location"])
                continue
            if response.status_code >= 400:
                raise ReferenceFetchError(f"链接返回状态 {response.status_code}")
            if "text/html" not in response.headers.get("content-type", "").lower():
                raise ReferenceFetchError("链接不是 HTML 页面")
            if len(response.content) > self.max_bytes:
                raise ReferenceFetchError("链接内容超过大小限制")
            return extract_readable_text(response.text)
        raise ReferenceFetchError("链接重定向次数过多")
