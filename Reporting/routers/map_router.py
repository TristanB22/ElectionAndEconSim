#!/usr/bin/env python3
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
import httpx
import os
import random
import time
from typing import List, Optional
from urllib.parse import urlparse

from ..config import settings

router = APIRouter(prefix="/api/map", tags=["map"])


@router.get("/config")
def get_map_config():
    """Expose which geo features are enabled to the frontend."""
    return {"tiles": True, "vector": False, "pois": True}


def _select_proxy(proxies: List[str]) -> tuple[Optional[httpx.Proxy], Optional[str]]:
    """Select a random proxy and return (Proxy object, original URL) for logging.
    Returns (None, None) if proxies disabled or pool empty.
    """
    if not proxies or not settings.USE_TILE_PROXY:
        return None, None
    proxy_url = random.choice(proxies)
    return httpx.Proxy(proxy_url), proxy_url


def _build_upstream_url(z: int, x: int, y: int) -> str:
    return settings.TILE_UPSTREAM_URL.format(z=z, x=x, y=y)


def _redact_proxy_url(proxy_url: Optional[str]) -> str:
    if not proxy_url:
        return ""
    try:
        parsed = urlparse(proxy_url)
        host = parsed.hostname or "unknown-host"
        port = f":{parsed.port}" if parsed.port else ""
        return f"{parsed.scheme}://{host}{port}/"
    except Exception:
        return "unknown-proxy"


def _browser_like_headers() -> dict:
    """Return headers that mimic a typical desktop Chrome request for PNG tiles.
    This helps certain upstreams treat us like a normal browser client.
    """
    return {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-language": "en-US,en;q=0.9",
        "cache-control": "no-cache",
        "pragma": "no-cache",
        "priority": "u=0, i",
        "sec-ch-ua": '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"',
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "none",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
    }


@router.get("/tiles/{z}/{x}/{y}.png")
def get_map_tile(z: int, x: int, y: int):
    """Serve tiles from NAS. If missing, fetch from upstream via proxies with retry/backoff and cache locally."""
    log_level = settings.TILE_LOG_LEVEL
    
    try:
        tiles_dir = settings.NAS_MAPS_DATA_DIRECTORY
        tile_path = Path(tiles_dir) / "tiles" / str(z) / str(x) / f"{y}.png"

        if tile_path.exists():
            return FileResponse(str(tile_path), media_type="image/png")

        # Attempt to fetch via upstream with proxy + retries
        upstream_url = _build_upstream_url(z, x, y)
        # Config snapshot for this request (log_level >= 1)
        if log_level >= 1:
            try:
                print(
                    f"[tiles] config: USE_TILE_PROXY={settings.USE_TILE_PROXY} (env={os.getenv('USE_TILE_PROXY')}), "
                    f"pool_size={len(settings.TILE_HTTP_PROXIES)}, upstream={upstream_url}, cache_path={tile_path}"
                )
            except Exception:
                pass
        backoff_base = max(0, settings.TILE_BACKOFF_BASE_MS) / 1000.0
        max_retries = max(0, settings.TILE_MAX_RETRIES)
        timeout = settings.TILE_TIMEOUT_S
        # Mimic a real browser to avoid upstream throttling/blocks
        headers = _browser_like_headers()
        last_error: Optional[Exception] = None

        for attempt in range(max_retries + 1):
            try:
                proxy, proxy_url = _select_proxy(settings.TILE_HTTP_PROXIES)
                # httpx 0.27+: configure proxy via HTTPTransport
                if proxy:
                    transport = httpx.HTTPTransport(proxy=proxy)
                    client_kwargs = {"transport": transport, "timeout": timeout}
                else:
                    client_kwargs = {"timeout": timeout}

                # Debug trace for diagnostics (log_level >= 2)
                if log_level >= 2:
                    try:
                        print(
                            f"[tiles] attempt={attempt+1}/{max_retries+1} proxy={'on' if proxy else 'off'} "
                            f"proxy_url={_redact_proxy_url(proxy_url)} url={upstream_url}"
                        )
                    except Exception:
                        pass

                t0 = time.time()
                with httpx.Client(**client_kwargs) as client:
                    r = client.get(upstream_url, headers=headers, follow_redirects=True)
                    dt_ms = int((time.time() - t0) * 1000)
                    if r.status_code == 200 and r.content:
                        tile_path.parent.mkdir(parents=True, exist_ok=True)
                        tile_path.write_bytes(r.content)
                        if log_level >= 1:
                            try:
                                print(f"[tiles] success status=200 bytes={len(r.content)} ms={dt_ms} saved={tile_path}")
                            except Exception:
                                pass
                        return FileResponse(str(tile_path), media_type="image/png")
                    # Treat non-200 as retryable up to max_retries
                    if log_level >= 2:
                        try:
                            body_preview = r.text[:200] if r.text else ""
                            print(
                                f"[tiles] upstream non-200 status={r.status_code} ms={dt_ms} "
                                f"ct={r.headers.get('content-type')} preview={body_preview!r}"
                            )
                        except Exception:
                            pass
                    last_error = HTTPException(status_code=r.status_code, detail=f"Upstream returned {r.status_code}")
            except Exception as e:
                last_error = e
                if log_level >= 2:
                    try:
                        print(f"[tiles] exception type={type(e).__name__} msg={e}")
                    except Exception:
                        pass

            # Exponential backoff with jitter: base * 2^attempt + small random
            if attempt < max_retries:
                sleep_s = (backoff_base * (2 ** attempt)) + random.uniform(0, backoff_base)
                time.sleep(sleep_s)

        # If we reach here, fetching failed
        if log_level >= 1:
            try:
                print(f"[tiles] failed after {max_retries+1} attempts; last_error={last_error}")
            except Exception:
                pass
        raise HTTPException(status_code=404, detail=f"Tile not found (upstream failed): {last_error}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to serve tile: {str(e)}")

