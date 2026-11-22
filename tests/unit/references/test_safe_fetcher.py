import httpx
import pytest

from workbench.references.fetcher import ReferenceFetchError, SafeReferenceFetcher


def public_resolver(_host: str) -> list[str]:
    return ["93.184.216.34"]


def test_fetcher_accepts_only_public_html_and_sends_no_cookie() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "cookie" not in request.headers
        return httpx.Response(200, headers={"content-type": "text/html; charset=utf-8"}, text="<h1>公开案例</h1>")

    fetcher = SafeReferenceFetcher(resolver=public_resolver, transport=httpx.MockTransport(handler))
    assert "公开案例" in fetcher.fetch("https://example.com/article")


def test_fetcher_returns_readable_text_without_script_style_or_markup() -> None:
    html = """
    <html><head><title>公益文章标题</title><style>.hidden{display:none}</style>
    <script>window.secret = '不要进入模型';</script></head>
    <body><nav>站点导航</nav><article><h1>公益文章标题</h1><p>第一段正文。</p><p>第二段&nbsp;正文。</p></article></body></html>
    """
    fetcher = SafeReferenceFetcher(
        resolver=public_resolver,
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(200, headers={"content-type": "text/html; charset=utf-8"}, text=html)
        ),
    )

    text = fetcher.fetch("https://example.com/article")

    assert "公益文章标题" in text
    assert "第一段正文。" in text
    assert "第二段 正文。" in text
    assert "window.secret" not in text
    assert ".hidden" not in text
    assert "<article>" not in text


def test_fetcher_rejects_html_without_readable_article_text() -> None:
    fetcher = SafeReferenceFetcher(
        resolver=public_resolver,
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(200, headers={"content-type": "text/html"}, text="<script>only()</script>")
        ),
    )

    with pytest.raises(ReferenceFetchError, match="正文"):
        fetcher.fetch("https://example.com/empty")


@pytest.mark.parametrize("url", ["file:///etc/passwd", "http://127.0.0.1/a", "http://[::1]/a"])
def test_fetcher_rejects_non_http_and_local_addresses(url: str) -> None:
    fetcher = SafeReferenceFetcher(resolver=lambda _host: ["127.0.0.1"])
    with pytest.raises(ReferenceFetchError):
        fetcher.fetch(url)


def test_fetcher_revalidates_redirect_and_limits_type_and_size() -> None:
    def redirect_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "http://127.0.0.1/private"})

    fetcher = SafeReferenceFetcher(resolver=public_resolver, transport=httpx.MockTransport(redirect_handler))
    with pytest.raises(ReferenceFetchError):
        fetcher.fetch("https://example.com")

    binary = SafeReferenceFetcher(
        resolver=public_resolver,
        transport=httpx.MockTransport(lambda _request: httpx.Response(200, headers={"content-type": "application/pdf"}, content=b"pdf")),
    )
    with pytest.raises(ReferenceFetchError):
        binary.fetch("https://example.com/file")

    large = SafeReferenceFetcher(
        resolver=public_resolver,
        max_bytes=4,
        transport=httpx.MockTransport(lambda _request: httpx.Response(200, headers={"content-type": "text/html"}, content=b"12345")),
    )
    with pytest.raises(ReferenceFetchError):
        large.fetch("https://example.com/large")
