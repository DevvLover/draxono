import json, time
from typing import Any, Dict
import requests
from internal.hsl import decode_base64_url

HEADERS = {
    "Accept": "application/json, application/octet-stream",
    "Accept-Language": "en-US,en;q=0.9",
    "Content-Type": "application/x-www-form-urlencoded",
    "Sec-Ch-Ua": '"Chromium";v="132", "Not?A_Brand";v="24", "Google Chrome";v="132"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
}

def fetch_asset_version(session: requests.Session, host: str = "accounts.hcaptcha.com", sitekey: str = "a5f74b19-9e45-40e0-b45d-47ff91b7a6c2", timeout: float = 30.0) -> str:
    r = session.get("https://hcaptcha.com/checksiteconfig", params={"host": host, "sitekey": sitekey, "sc": "1", "swa": "1"}, timeout=timeout)
    r.raise_for_status()
    req_jwt = r.json()["c"]["req"]
    return json.loads(decode_base64_url(req_jwt.split(".")[1]).decode("utf-8"))["l"].rsplit("/", 1)[-1]

def fetch_site_config(session: requests.Session, asset_version: str, host: str, sitekey: str, timeout: float = 30.0) -> dict:
    r = session.post(f"https://api.hcaptcha.com/checksiteconfig?v={asset_version}&host={host}&sitekey={sitekey}&sc=1&swa=1&spst=1", headers={"Content-Type": "text/plain", "Referer": "https://newassets.hcaptcha.com/"}, timeout=timeout)
    r.raise_for_status()
    return r.json().get("c", {})

def fetch_hsw_js(session: requests.Session, asset_version: str, timeout: float = 15.0) -> str:
    r = session.get(f"https://newassets.hcaptcha.com/c/{asset_version}/hsw.js", timeout=timeout)
    r.raise_for_status()
    return r.text

def get_client_options(host: str, endpoint: str = "https://api.hcaptcha.com") -> dict:
    return {
        "sentry": True, "reportapi": f"https://{host}", "recaptchacompat": "true", "custom": False, "hl": "en",
        "tplinks": "on", "andint": "off", "pat": "on", "pstissuer": "https://pst-issuer.hcaptcha.com", "endpoint": endpoint,
        "theme": "light", "size": "normal", "confirm-nav": False,
    }

def get_pdc_pem() -> Dict[str, Any]:
    now = int(time.time() * 1000)
    return {
        "pdc": {"s": now, "n": 0, "bfp": 1, "bfc": 1, "big": 0, "p": 0, "gcs": 1},
        "pem": {"csc": 60.3, "csch": "api.hcaptcha.com", "cscrt": 0, "cscft": 60.3},
    }
