import argparse
import json
import os
import sys
import time
import urllib.parse
from typing import Any, Dict, Optional
import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from internal.hsl import solve_hsl_local
from internal.motion import answer_gestures, build_motion_data
from internal.nopecha import format_answers, solve_challenge as nopecha_solve
from internal.telemetry import HEADERS, fetch_asset_version, fetch_site_config, get_client_options, get_pdc_pem

DEFAULT_NOPECHA_KEY = os.environ.get("NOPECHA_API_KEY", "")
DEFAULT_SITEKEY = "a5f74b19-9e45-40e0-b45d-47ff91b7a6c2"
DEFAULT_HOST = "accounts.hcaptcha.com"

def parse_proxy(proxy_str: Optional[str]) -> Optional[Dict[str, str]]:
    if not proxy_str or not proxy_str.strip():
        return None
    p = proxy_str.strip()
    if not (p.startswith("http://") or p.startswith("https://")):
        p = f"http://{p}"
    return {"http": p, "https": p}

def solve(
    nopecha_key: str,
    sitekey: str = DEFAULT_SITEKEY,
    host: str = DEFAULT_HOST,
    proxy: Optional[str] = None,
    timeout: float = 30.0
) -> Dict[str, Any]:
    session = requests.Session()
    session.headers.update(HEADERS)
    proxies = parse_proxy(proxy)
    if proxies:
        session.proxies.update(proxies)

    t0 = time.time()
    asset_version = fetch_asset_version(session, host=host, sitekey=sitekey, timeout=timeout)
    site_config = fetch_site_config(session, asset_version, host, sitekey, timeout=timeout)

    t_obj = get_pdc_pem()
    pdc, pem = t_obj["pdc"], t_obj["pem"]
    client_options = get_client_options(host)
    motion_data = build_motion_data([], host, sitekey)

    getcap_payload1 = {
        "v": asset_version, "sitekey": sitekey, "host": host, "hl": "en",
        "motionData": motion_data, "pdc": json.dumps(pdc), "pem": json.dumps(pem),
        "n": "fail", "e": "asset-error", "c": json.dumps(site_config),
        "clientOptions": json.dumps(client_options),
    }

    hcap_url1 = f"https://api.hcaptcha.com/getcaptcha/{sitekey}"
    resp1 = session.post(hcap_url1, data=urllib.parse.urlencode(getcap_payload1), timeout=timeout)
    resp1.raise_for_status()
    data1 = resp1.json()

    c_obj = data1.get("c", {})
    hsj_req = c_obj.get("req")
    if not hsj_req:
        raise RuntimeError(f"Failed to receive HSL/HSJ JWT from asset-error request: {data1}")

    c_hsl_req = hsj_req
    c_type = c_obj.get("type", "hsl")
    if c_type == "hsj":
        pdc["s"] = int(time.time() * 1000)
        getcap_payload2 = {
            "v": asset_version, "sitekey": sitekey, "host": host, "hl": "en",
            "motionData": motion_data, "pdc": json.dumps(pdc), "pem": json.dumps(pem),
            "n": "fail", "e": "asset-error", "c": json.dumps({"type": "hsj", "req": hsj_req}),
            "clientOptions": json.dumps(client_options),
        }
        resp2 = session.post(hcap_url1, data=urllib.parse.urlencode(getcap_payload2), timeout=timeout)
        resp2.raise_for_status()
        data2 = resp2.json()
        c_obj = data2.get("c", {})
        c_hsl_req = c_obj.get("req", hsj_req)

    proof = solve_hsl_local(c_hsl_req)
    pem2 = {"csc": 62.0, "csch": "api2.hcaptcha.com", "cscrt": 0, "cscft": 62.0}
    client_options["endpoint"] = "https://api2.hcaptcha.com"
    client_options["reportapi"] = f"https://{host}"
    pdc["s"] = int(time.time() * 1000)

    getcap_payload3 = {
        "v": asset_version, "sitekey": sitekey, "host": host, "hl": "en",
        "motionData": motion_data, "pdc": json.dumps(pdc), "pem": json.dumps(pem2),
        "n": proof, "c": json.dumps(c_obj), "clientOptions": json.dumps(client_options),
    }

    hcap_url2 = f"https://api2.hcaptcha.com/getcaptcha/{sitekey}"
    resp3 = session.post(hcap_url2, data=urllib.parse.urlencode(getcap_payload3), headers={"Accept": "application/json"}, timeout=timeout)
    resp3.raise_for_status()
    captcha_data = resp3.json()

    if captcha_data.get("pass") is True or captcha_data.get("generated_pass_UUID"):
        return {
            "pass": True, "token": captcha_data.get("generated_pass_UUID"),
            "challenge_type": "passive_pass", "elapsed_seconds": round(time.time() - t0, 2),
            "raw_response": captcha_data,
        }

    request_type = captcha_data.get("request_type")
    tasklist = captcha_data.get("tasklist", [])
    captcha_key = captcha_data.get("key")
    if not tasklist or not captcha_key:
        raise RuntimeError(f"Failed to get challenge tasks: {captcha_data}")

    raw_sol = nopecha_solve(nopecha_key, captcha_data)
    dims = {t.get("task_key", ""): (480, 320) for t in tasklist}
    answers = format_answers(request_type, tasklist, raw_sol, dims)
    gestures = answer_gestures(request_type, tasklist, answers)

    motion_data_final = build_motion_data(gestures, host, sitekey)
    n_check = proof
    if captcha_data.get("c") and isinstance(captcha_data["c"], dict) and captcha_data["c"].get("req"):
        try: n_check = solve_hsl_local(captcha_data["c"]["req"])
        except Exception: n_check = proof

    c_check_json = json.dumps(captcha_data.get("c", c_obj), separators=(",", ":"))
    check_url = f"https://api2.hcaptcha.com/checkcaptcha/{sitekey}/{captcha_key}"
    check_payload = {
        "v": asset_version, "job_mode": request_type, "answers": answers,
        "serverdomain": host, "sitekey": sitekey, "motionData": motion_data_final,
        "n": n_check, "c": c_check_json,
    }

    check_resp = session.post(check_url, json=check_payload, headers={"Content-Type": "application/json", "Accept": "application/json"}, timeout=timeout)
    if check_resp.status_code == 403:
        form_payload = {
            "v": asset_version, "sitekey": sitekey, "host": host, "hl": "en",
            "motionData": motion_data_final, "n": n_check, "c": c_check_json,
            "answers": json.dumps(answers),
        }
        check_resp = session.post(check_url, data=urllib.parse.urlencode(form_payload), headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"}, timeout=timeout)

    res_json = check_resp.json()
    is_pass = bool(res_json.get("pass") or res_json.get("generated_pass_UUID"))

    return {
        "pass": is_pass, "token": res_json.get("generated_pass_UUID") or None,
        "challenge_type": request_type, "elapsed_seconds": round(time.time() - t0, 2),
        "raw_response": res_json,
    }

COLOR_RESET, COLOR_CYAN, COLOR_GREEN, COLOR_RED = "\033[0m", "\033[36m", "\033[32m", "\033[31m"

def main():
    parser = argparse.ArgumentParser(description="HSL Solver Demo")
    parser.add_argument("--server", default="http://127.0.0.1:8000")
    parser.add_argument("--nopecha-key", default="")
    parser.add_argument("--sitekey", default=DEFAULT_SITEKEY)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--proxy", default=None)
    args = parser.parse_args()

    url = f"{args.server.rstrip('/')}/solve"
    payload = {"sitekey": args.sitekey, "host": args.host, "proxy": args.proxy}
    if args.nopecha_key: payload["nopecha_key"] = args.nopecha_key

    print(f"{COLOR_CYAN}[*] INFO{COLOR_RESET} Sending solve request to server at {url} (host={args.host}, sitekey={args.sitekey})...")
    try:
        r = requests.post(url, json=payload, timeout=65)
        res = r.json()
        if res.get("success"):
            print(f"{COLOR_GREEN}[+] INFO{COLOR_RESET} SUCCESS [{res.get('elapsed_seconds')}s] Token: {res.get('token')}")
        else:
            print(f"{COLOR_RED}[-] ERROR{COLOR_RESET} FAILED [{res.get('elapsed_seconds')}s] Error: {res.get('error') or res.get('raw_response')}")
            sys.exit(1)
    except Exception as e:
        print(f"{COLOR_RED}[-] ERROR{COLOR_RESET} Request error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
