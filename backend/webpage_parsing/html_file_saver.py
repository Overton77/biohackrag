import asyncio
import aiohttp
import async_timeout
import random
import time

# Modern browser-y headers
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/127.0.0.0 Safari/537.36"
    ),
    # keep br now that you installed brotli/brotlicffi
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

async def fetch_html(url: str, session: aiohttp.ClientSession) -> str:
    # jittered backoff for transient 4xx/5xx
    for attempt in range(5):
        try:
            # Timeout per request
            async with async_timeout.timeout(30):
                async with session.get(url, allow_redirects=True) as resp:
                    # Optional: raise for non-200 to catch early
                    resp.raise_for_status()
                    # Let aiohttp handle decoding (now that brotli is installed)
                    return await resp.text(encoding="utf-8", errors="ignore")
        except (aiohttp.ClientResponseError, aiohttp.ClientConnectionError, asyncio.TimeoutError) as e:
            # backoff on 403/429/5xx, with small jitter
            if attempt == 4:
                raise
            sleep = (2 ** attempt) + random.uniform(0, 0.5)
            await asyncio.sleep(sleep)

async def save_html_file(url: str, output_file: str):
    timeout = aiohttp.ClientTimeout(total=60, connect=15, sock_read=45)
    conn = aiohttp.TCPConnector(limit=8, ssl=False)  # disable cert validation if you hit odd TLS issues; else remove ssl=False
    async with aiohttp.ClientSession(headers=DEFAULT_HEADERS, timeout=timeout, connector=conn) as session:
        html = await fetch_html(url, session)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html)

if __name__ == "__main__":
    url = "https://daveasprey.com/1303-nayan-patel/"
    output = r"C:\Users\Pinda\Proyectos\BioHackAgent\backend\output\episode_1303.html"
    asyncio.run(save_html_file(url, output))