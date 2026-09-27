import argparse, os, sys, requests

DEFAULT_SERVER = "http://127.0.0.1:8000"
DEFAULT_NOPECHA_KEY = os.environ.get("NOPECHA_API_KEY", "sub_1U8nZoCRwBwvt6pt891WudkT")
DEFAULT_SITEKEY = "a9b5fb07-92ff-493f-86fe-352a2803b3df"
DEFAULT_HOST = "discord.com"

COLOR_RESET, COLOR_CYAN, COLOR_GREEN, COLOR_RED = "\033[0m", "\033[36m", "\033[32m", "\033[31m"

class SolverClient:
    def __init__(self, server_url: str = DEFAULT_SERVER):
        self.server_url = server_url.rstrip("/")

    def health(self) -> bool:
        try: return requests.get(f"{self.server_url}/health", timeout=5).status_code == 200
        except Exception: return False

    def solve(self, nopecha_key: str = DEFAULT_NOPECHA_KEY, sitekey: str = DEFAULT_SITEKEY, host: str = DEFAULT_HOST, proxy: str = None, timeout: float = 60.0) -> dict:
        try:
            r = requests.post(f"{self.server_url}/solve", json={"nopecha_key": nopecha_key, "sitekey": sitekey, "host": host, "proxy": proxy, "timeout": timeout}, timeout=timeout + 10)
            return r.json()
        except Exception as e:
            return {"success": False, "error": f"Invalid JSON response: {e}"}

def main():
    parser = argparse.ArgumentParser(description="HSL Solver Client")
    parser.add_argument("--server", default=DEFAULT_SERVER)
    parser.add_argument("--nopecha-key", default=DEFAULT_NOPECHA_KEY)
    parser.add_argument("--sitekey", default=DEFAULT_SITEKEY)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--proxy", default=None)
    args = parser.parse_args()

    client = SolverClient(server_url=args.server)
    print(f"{COLOR_CYAN}[*] INFO{COLOR_RESET} Checking API health at {args.server}...")
    if not client.health():
        print(f"{COLOR_RED}[-] ERROR{COLOR_RESET} API Server at {args.server} is offline or unhealthy.")
        sys.exit(1)

    print(f"{COLOR_CYAN}[*] INFO{COLOR_RESET} Requesting hCaptcha token for host={args.host} sitekey={args.sitekey} proxy={args.proxy}...")
    res = client.solve(nopecha_key=args.nopecha_key, sitekey=args.sitekey, host=args.host, proxy=args.proxy)

    if res.get("success"):
        print(f"{COLOR_GREEN}[+] INFO{COLOR_RESET} SUCCESS [{res.get('elapsed_seconds')}s] Token: {res.get('token')}")
    else:
        print(f"{COLOR_RED}[-] ERROR{COLOR_RESET} FAILED [{res.get('elapsed_seconds')}s] Error: {res.get('error') or res.get('raw_response')}")
        sys.exit(1)

if __name__ == "__main__":
    main()
