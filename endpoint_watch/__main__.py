"""Run with python -m endpoint_watch or the endpoint-watch command."""

import argparse
import json
import math
import time
from dataclasses import asdict, dataclass
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from . import __version__


@dataclass
class Result:
    url: str
    final_url: str | None
    ok: bool
    status_code: int | None
    elapsed_ms: float
    error: str | None


def http_url(value: str) -> str:
    """Validate every target before the CLI makes any network requests."""
    try:
        value.encode("ascii")
        if any(character.isspace() or ord(character) < 32 or ord(character) == 127
               for character in value):
            raise ValueError("whitespace and control characters are not allowed")
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("an http:// or https:// URL with a hostname is required")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("credentials in URLs are not supported")
        if parsed.port == 0:
            raise ValueError("port must be between 1 and 65535")
    except (ValueError, UnicodeError) as exc:
        raise argparse.ArgumentTypeError(
            f"invalid HTTP URL: {exc}; use an ASCII hostname and percent-encoded path"
        ) from exc
    return value


def positive_timeout(value: str) -> float:
    try:
        timeout = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("timeout must be a positive number") from exc
    if not math.isfinite(timeout) or not 0 < timeout <= 86400:
        raise argparse.ArgumentTypeError("timeout must be greater than 0 and at most 86400 seconds")
    return timeout


def check_url(url: str, timeout: float = 5.0) -> Result:
    http_url(url)
    positive_timeout(str(timeout))
    started = time.perf_counter()
    status_code = None
    final_url = None
    error = None
    request = Request(url, headers={"User-Agent": f"endpoint-watch/{__version__}"})
    try:
        # Only response headers are needed; do not download the response body.
        with urlopen(request, timeout=timeout) as response:
            status_code = response.status
            final_url = response.geturl()
            if not 200 <= status_code < 300:
                error = f"HTTP {status_code}"
    except HTTPError as exc:
        status_code = exc.code
        final_url = exc.geturl()
        error = f"HTTP {exc.code}: {exc.reason}"
        exc.close()
    except (URLError, OSError, HTTPException, ValueError) as exc:
        error = str(exc.reason) if isinstance(exc, URLError) else str(exc)
        error = error or type(exc).__name__
    return Result(
        url=url,
        final_url=final_url,
        ok=error is None,
        status_code=status_code,
        elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
        error=error,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check HTTP endpoints. A final 2xx response is healthy."
    )
    parser.add_argument("urls", nargs="+", type=http_url, metavar="URL")
    parser.add_argument(
        "--timeout", type=positive_timeout, default=5.0, metavar="SECONDS",
        help="connection/socket timeout, 0 < seconds <= 86400 (default: 5)",
    )
    parser.add_argument("--json", action="store_true", help="print a JSON report")
    parser.add_argument("--version", action="version", version=f"endpoint-watch {__version__}")
    args = parser.parse_args(argv)
    results = [check_url(url, args.timeout) for url in args.urls]
    healthy = sum(result.ok for result in results)
    summary = {"total": len(results), "healthy": healthy, "unhealthy": len(results) - healthy}
    if args.json:
        print(json.dumps(
            {"results": [asdict(result) for result in results], "summary": summary},
            ensure_ascii=False, indent=2,
        ))
    else:
        for result in results:
            label = "OK" if result.ok else "FAIL"
            status = result.status_code if result.status_code is not None else "no response"
            detail = f" — {result.error}" if result.error else ""
            print(f"{label} {result.url} [{status}, {result.elapsed_ms:.2f} ms]{detail}")
        print(f"{healthy}/{len(results)} healthy")
    return 0 if healthy == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
