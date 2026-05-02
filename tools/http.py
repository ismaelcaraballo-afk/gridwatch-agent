import time
import requests

TRANSIENT_ERRORS = (429, 502, 503, 504)


def get_with_backoff(
    url: str,
    *,
    params: dict = None,
    headers: dict = None,
    timeout: int = 30,
    max_retries: int = 3,
) -> requests.Response:
    """GET with exponential backoff on transient HTTP errors and timeouts.

    Delays: 1s → 2s → 4s between attempts (doubles each retry).
    Raises on final failure so the calling tool can return an error string.
    """
    delay = 1
    last_exc = None

    for attempt in range(max_retries + 1):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=timeout)
            if resp.status_code in TRANSIENT_ERRORS and attempt < max_retries:
                time.sleep(delay)
                delay *= 2
                continue
            resp.raise_for_status()
            return resp
        except requests.Timeout as e:
            last_exc = e
            if attempt < max_retries:
                time.sleep(delay)
                delay *= 2
        except requests.RequestException as e:
            last_exc = e
            if attempt < max_retries:
                time.sleep(delay)
                delay *= 2

    raise requests.RequestException(
        f"All {max_retries + 1} attempts failed for {url}"
    ) from last_exc
