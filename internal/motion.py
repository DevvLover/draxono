import json, time
from typing import Any, List

def answer_gestures(request_type: str, tasklist: List[dict], answers: dict) -> List[Any]:
    gestures: List[Any] = []
    if request_type == "image_label_binary":
        n = len(tasklist)
        cols = 3 if n == 9 else (4 if n == 16 else int(n**0.5) or 1)
        rows = (n + cols - 1) // cols
        tw, th = 500 // max(cols, 1), 470 // max(rows, 1)
        for i, task in enumerate(tasklist):
            if answers.get(task.get("task_key", "")) == "true":
                gestures.append(((i % cols) * tw + tw // 2, (i // cols) * th + th // 2))
    elif request_type == "image_drag_drop":
        for task in tasklist:
            ent_list = answers.get(task.get("task_key", ""), [])
            if not isinstance(ent_list, list): continue
            orig = {e.get("entity_id") or e.get("entity_name"): e for e in task.get("entities", [])}
            for ent in ent_list:
                orig_ent = orig.get(ent.get("entity_name"))
                if not orig_ent: continue
                oc = list(orig_ent.get("coords") or [0, 0])
                ox, oy = (int(oc[0]) if len(oc) >= 1 else 0), (int(oc[1]) if len(oc) >= 2 else 0)
                ex, ey = ent.get("entity_coords", [ox, oy])
                if [ox, oy] != [ex, ey]:
                    gestures.append((ox, oy, ex, ey))
                    break
    else:
        for task in tasklist:
            ent_list = answers.get(task.get("task_key", ""), [])
            if isinstance(ent_list, list) and ent_list:
                f = ent_list[0]
                if isinstance(f, dict): gestures.append(tuple(f.get("entity_coords", [250, 200])))
                elif isinstance(f, (list, tuple)) and len(f) >= 2: gestures.append((int(f[0]), int(f[1])))
    return gestures

def build_motion_data(gestures: List[Any], host: str, sitekey: str) -> str:
    now = int(time.time() * 1000)
    ts, te, mm, md, mu = [], [], [], [], []
    t, bx, by = now + 120, 1018, 923
    clip = lambda x, y: [max(0, min(bx, int(x))), max(0, min(by, int(y)))]
    cx, cy = 150, 200

    for g in gestures:
        if len(g) == 2:
            tx, ty = clip(g[0], g[1])
            for s in range(1, 9):
                p = s / 8
                mm.append([int(cx + (tx - cx) * p * (2 - p)), int(cy + (ty - cy) * p * (2 - p)), t + s * 12])
            t += 116
            ts.append([[0, tx, ty], t]); te.append([[0, tx, ty], t + 60])
            md.append([tx, ty, t]); mu.append([tx, ty, t + 60])
            t += 150; cx, cy = tx, ty
        elif len(g) == 4:
            sx, sy = clip(g[0], g[1]); ex, ey = clip(g[2], g[3])
            for s in range(1, 6): mm.append([int(cx + (sx - cx) * (s / 5)), int(cy + (sy - cy) * (s / 5)), t + s * 15])
            t += 80; ts.append([[0, sx, sy], t]); md.append([sx, sy, t]); t += 40
            for s in range(1, 11): mm.append([int(sx + (ex - sx) * (s / 10)), int(sy + (ey - sy) * (s / 10)), t + s * 16])
            t += 200; te.append([[0, ex, ey], t]); mu.append([ex, ey, t]); t += 100
            cx, cy = ex, ey

    top = {
        "inv": False, "theme": 1796889847, "pel": f'<div id="hcaptcha-demo" class="h-captcha" data-sitekey="{sitekey}"></div>',
        "st": now - 500, "sc": {"availWidth": bx, "availHeight": by, "width": bx, "height": by, "colorDepth": 24, "pixelDepth": 24, "availLeft": 0, "availTop": 0, "onchange": None, "isExtended": False},
        "or": "landscape", "wi": [bx, by],
        "nv": {
            "vendorSub": "", "productSub": "20030107", "vendor": "Google Inc.", "maxTouchPoints": 1, "hardwareConcurrency": 8, "cookieEnabled": True,
            "appCodeName": "Mozilla", "appName": "Netscape", "appVersion": "5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
            "platform": "Win32", "product": "Gecko", "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
            "language": "en-US", "languages": ["en-US", "en"], "onLine": True, "webdriver": False, "pdfViewerEnabled": True, "deviceMemory": 8
        }
    }

    return json.dumps({
        "st": now - 500, "dct": now - 500, "ts": ts, "ts-mp": 0, "te": te, "te-mp": 0, "mm": mm, "mm-mp": 0.05 if mm else 0,
        "md": md, "md-mp": 0.02 if md else 0, "mu": mu, "mu-mp": 0.02 if mu else 0, "v": 1, "topLevel": top, "session": [],
        "widgetList": ["0crrk962gd14"], "widgetId": "0crrk962gd14", "href": f"https://{host}/demo" if "demo" in host else f"https://{host}/",
        "prev": {"escaped": False, "passed": False, "expiredChallenge": False, "expiredResponse": False}
    }, separators=(",", ":"))
