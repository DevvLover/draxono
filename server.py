import argparse, logging, os, sys
from flask import Flask, jsonify, request

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from tests.solve_demo import DEFAULT_HOST, DEFAULT_SITEKEY, solve

COLOR_RESET = "\033[0m"
COLOR_CYAN = "\033[36m"
COLOR_GREEN = "\033[32m"
COLOR_RED = "\033[31m"
COLOR_YELLOW = "\033[33m"

class ColoredFormatter(logging.Formatter):
    def format(self, record):
        timestamp = self.formatTime(record, "%H:%M:%S")
        if record.levelno >= logging.ERROR:
            prefix = f"{COLOR_RED}[-] ERROR{COLOR_RESET}"
        elif record.levelno >= logging.WARNING:
            prefix = f"{COLOR_YELLOW}[!] WARN {COLOR_RESET}"
        else:
            msg = record.getMessage()
            if "SUCCESS" in msg or "result -> pass=True" in msg:
                prefix = f"{COLOR_GREEN}[+] INFO {COLOR_RESET}"
            else:
                prefix = f"{COLOR_CYAN}[*] INFO {COLOR_RESET}"
        return f"{timestamp} {prefix} {record.getMessage()}"

handler = logging.StreamHandler()
handler.setFormatter(ColoredFormatter())
logger = logging.getLogger("hsl_api")
logger.setLevel(logging.INFO)
logger.addHandler(handler)
logger.propagate = False

app = Flask(__name__)
KEYS_FILE = os.path.join(os.path.dirname(__file__), "keys", "keys.txt")

def get_server_key() -> str:
    if os.path.exists(KEYS_FILE):
        with open(KEYS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                k = line.strip()
                if k and not k.startswith("#"): return k
    return os.environ.get("NOPECHA_API_KEY", "")

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "hsl-solver"})

@app.route("/solve", methods=["POST"])
def handle_solve():
    d = request.get_json(silent=True) or {}
    key = d.get("nopecha_key") or d.get("api_key") or d.get("client_key") or get_server_key()
    if not key:
        return jsonify({"success": False, "error": "No valid key found."}), 400

    sitekey, host = d.get("sitekey", DEFAULT_SITEKEY), d.get("host", DEFAULT_HOST)
    proxy, timeout = d.get("proxy"), float(d.get("timeout", 30.0))

    logger.info(f"Solve request -> host={host} sitekey={sitekey} proxy={proxy}")
    try:
        res = solve(nopecha_key=key, sitekey=sitekey, host=host, proxy=proxy, timeout=timeout)
        passed = res.get("pass", False)
        status = 200 if passed else 422
        log_fn = logger.info if passed else logger.warning
        tag = "result -> pass=True" if passed else "result -> pass=False"
        log_fn(f"Solve {tag} type={res.get('challenge_type')} time={res.get('elapsed_seconds')}s")
        return jsonify({
            "success": passed,
            "token": res.get("token"),
            "challenge_type": res.get("challenge_type"),
            "elapsed_seconds": res.get("elapsed_seconds"),
            "raw_response": res.get("raw_response"),
        }), status
    except Exception as e:
        logger.error(f"Solve exception -> {e}")
        return jsonify({"success": False, "error": str(e)}), 500

def main():
    parser = argparse.ArgumentParser(description="HSL API Server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    cli = sys.modules.get("flask.cli")
    if cli: cli.show_server_banner = lambda *a: None
    logging.getLogger("werkzeug").setLevel(logging.ERROR)

    logger.info(f"HSL API listening on http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port)

if __name__ == "__main__":
    main()
