import base64, hashlib, json, time

def decode_base64_url(d: str) -> bytes:
    return base64.urlsafe_b64decode((d + "=" * (-len(d) % 4)).replace("_", "/").replace("-", "+"))

def check_proof(diff: int, cand: str) -> bool:
    bits = [(b >> i) & 1 for b in hashlib.sha1(cand.encode("utf-8")).digest() for i in range(8)]
    return bits[0] == 0 and (diff <= 1 or all(b == 0 for b in bits[1:max(1, diff - 1)]))

def solve_hsl_local(token: str) -> str:
    p = json.loads(decode_base64_url(token.split(".")[1]))
    diff, chal = p.get("s", 2), p.get("d", "")
    if not chal: raise ValueError("HSL token missing 'd' field")

    charset = "0123456789/:abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    for length in range(25):
        def gen(prefix):
            if len(prefix) == length:
                cand = "".join(charset[i] for i in prefix)
                return cand if check_proof(diff, f"{chal}::{cand}") else None
            for i in range(len(charset)):
                res = gen(prefix + [i])
                if res is not None: return res
            return None

        sol = gen([])
        if sol is not None:
            return f"1:{diff}:{time.strftime('%Y%m%d%H%M%S', time.gmtime())}:{chal}::{sol}"
    raise RuntimeError("Failed to find HSL proof")
