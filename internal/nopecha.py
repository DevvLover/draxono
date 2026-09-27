import base64
import copy
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Tuple
import requests

NOPECHA_API = "https://api.nopecha.com/v1"
DEFAULT_TIMEOUT = 60

class NopechaError(Exception): pass
class NopechaCreditError(NopechaError): pass
class NopechaNetworkError(NopechaError): pass

def fetch_as_data_uri(session: requests.Session, uri: str) -> str:
    if uri.startswith("data:"):
        return uri
    candidates = [uri, uri + ".png", uri + ".jpg", uri + ".jpeg", uri + ".webp", uri + ".webm"]
    last_exc = None
    for cand in candidates:
        try:
            r = session.get(cand, timeout=15)
            if r.status_code == 200 and len(r.content) > 100:
                clean_cand = cand.split("?")[0].lower()
                ct = (r.headers.get("content-type") or "").split(";")[0].strip().lower()

                if clean_cand.endswith(".png") or "png" in ct: mime = "image/png"
                elif clean_cand.endswith(".jpeg") or clean_cand.endswith(".jpg") or "jpeg" in ct or "jpg" in ct: mime = "image/jpeg"
                elif clean_cand.endswith(".webp") or "webp" in ct: mime = "image/webp"
                elif clean_cand.endswith(".webm") or "webm" in ct: mime = "video/webm"
                else: mime = ct if ct.startswith("image/") or ct.startswith("video/") else "image/png"

                b64 = base64.b64encode(r.content).decode("ascii")
                return f"data:{mime};base64,{b64}"
        except Exception as e:
            last_exc = e
    r = session.get(uri, timeout=15)
    r.raise_for_status()
    raise last_exc or RuntimeError(f"Failed to fetch {uri}")

def inline_challenge_images(cap: Dict[str, Any], sess: Optional[requests.Session] = None) -> Dict[str, Any]:
    cap = copy.deepcopy(cap)
    session = sess or requests.Session()
    jobs: List[tuple] = []
    for ti, task in enumerate(cap.get("tasklist") or []):
        if task.get("datapoint_uri") and not str(task["datapoint_uri"]).startswith("data:"):
            jobs.append(("dp", ti, None, task["datapoint_uri"]))
        for ei, ent in enumerate(task.get("entities") or []):
            if ent.get("entity_uri") and not str(ent["entity_uri"]).startswith("data:"):
                jobs.append(("ent", ti, ei, ent["entity_uri"]))

    results: Dict[tuple, str] = {}
    if jobs:
        with ThreadPoolExecutor(max_workers=min(8, len(jobs))) as pool:
            futs = {pool.submit(fetch_as_data_uri, session, uri): key for key, uri in [(j[:3], j[3]) for j in jobs]}
            for fut in as_completed(futs):
                key = futs[fut]
                try: results[key] = fut.result()
                except Exception as e: raise NopechaNetworkError(f"failed to inline image {key}: {e}")

    for kind, ti, ei, _ in jobs:
        if kind == "dp": cap["tasklist"][ti]["datapoint_uri"] = results[(kind, ti, ei)]
        else: cap["tasklist"][ti]["entities"][ei]["entity_uri"] = results[(kind, ti, ei)]

    examples = cap.get("requester_question_example")
    if examples:
        if isinstance(examples, str):
            if examples.strip().startswith("http") and not examples.startswith("data:"):
                try: cap["requester_question_example"] = fetch_as_data_uri(session, examples)
                except Exception as e: raise NopechaNetworkError(f"failed to inline example image: {e}")
        elif isinstance(examples, list):
            ex_jobs = [(i, ex) for i, ex in enumerate(examples) if isinstance(ex, str) and ex.strip().startswith("http") and not ex.startswith("data:")]
            ex_results = {}
            if ex_jobs:
                with ThreadPoolExecutor(max_workers=min(4, len(ex_jobs))) as pool:
                    futs = {pool.submit(fetch_as_data_uri, session, uri): i for i, uri in ex_jobs}
                    for fut in as_completed(futs):
                        i = futs[fut]
                        try: ex_results[i] = fut.result()
                        except Exception as e: raise NopechaNetworkError(f"failed to inline example {i}: {e}")
            cap["requester_question_example"] = [ex_results.get(i, ex) if isinstance(ex, str) else ex for i, ex in enumerate(examples)]

    return cap

def is_credit_error(data: Dict[str, Any]) -> bool:
    if not isinstance(data, dict): return False
    if data.get("error") == 16 or data.get("code") == 16: return True
    msg = str(data.get("message", "")).lower()
    return "out of credit" in msg or "insufficient credit" in msg

def solve_challenge(api_key: str, cap_data: Dict[str, Any], timeout: int = DEFAULT_TIMEOUT, headers: Optional[dict] = None, skip_inline: bool = False) -> Any:
    if not api_key: raise NopechaError("NopeCHA API key is required")
    session = requests.Session()
    session.headers.update(headers or {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36 Edg/152.0.0.0",
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        "Referer": "https://newassets.hcaptcha.com/",
    })

    cap = cap_data if skip_inline else inline_challenge_images(cap_data, sess=session)
    payload = {
        "data": {
            "request_type": cap["request_type"],
            "requester_question": cap.get("requester_question", {}),
            "tasklist": cap.get("tasklist", []),
        }
    }
    if cap.get("requester_question_example"): payload["data"]["requester_question_example"] = cap["requester_question_example"]
    if "requester_restricted_answer_set" in cap: payload["data"]["requester_restricted_answer_set"] = cap["requester_restricted_answer_set"]

    req_headers = {"Content-Type": "application/json", "Authorization": f"Basic {api_key}"}
    post_timeout = 90 if len(cap.get("tasklist") or []) >= 6 else 45
    r = session.post(f"{NOPECHA_API}/recognition/hcaptcha", headers=req_headers, json=payload, timeout=post_timeout)
    try: data = r.json()
    except Exception as e: raise NopechaNetworkError(f"non-JSON response HTTP {r.status_code}: {r.text[:200]}") from e

    if is_credit_error(data): raise NopechaCreditError(data)
    err = data.get("code") if data.get("code") is not None else data.get("error")
    if err and not isinstance(data.get("data"), str): raise NopechaError(f"NopeCHA submit error: {data}")

    job_id = data.get("data")
    if not isinstance(job_id, str): raise NopechaError(f"no job_id returned: {data}")

    deadline = time.time() + timeout
    time.sleep(0.3)
    while time.time() < deadline:
        r = session.get(f"{NOPECHA_API}/recognition/hcaptcha", params={"id": job_id}, headers=req_headers, timeout=30)
        try: result = r.json()
        except Exception:
            time.sleep(0.5)
            continue

        if result.get("code") == 14 or (r.status_code == 409 and result.get("data") is None):
            time.sleep(0.4)
            continue
        if is_credit_error(result): raise NopechaCreditError(result)
        if result.get("code") or (result.get("error") and result.get("data") is None): raise NopechaError(f"NopeCHA poll error: {result}")
        if result.get("data") is not None: return result["data"]
        time.sleep(0.5)

    raise NopechaNetworkError("poll timeout")

def format_answers(request_type: str, tasklist: List[dict], solution: Any, dims: Dict[str, Tuple[int, int]]) -> Dict[str, Any]:
    answers: Dict[str, Any] = {}
    if request_type == "image_label_binary":
        idx = 0
        for batch in solution:
            for val in batch:
                if idx < len(tasklist):
                    answers[tasklist[idx].get("task_key", "")] = "true" if val else "false"
                idx += 1
    elif request_type == "image_label_area_select":
        for i, task in enumerate(tasklist):
            task_key = task.get("task_key", "")
            img_w, img_h = dims.get(task_key, (500, 400))
            ents = []
            if i < len(solution) and solution[i]:
                for j, box in enumerate(solution[i]):
                    if isinstance(box, dict):
                        bx, by = float(box.get("x", 50)), float(box.get("y", 50))
                        cx = int(bx / 100.0 * img_w) if bx <= 100 else int(bx)
                        cy = int(by / 100.0 * img_h) if by <= 100 else int(by)
                    elif isinstance(box, (list, tuple)) and len(box) >= 2:
                        cx = int(box[0] / 100.0 * img_w) if box[0] <= 100 else int(box[0])
                        cy = int(box[1] / 100.0 * img_h) if box[1] <= 100 else int(box[1])
                    else: cx, cy = int(img_w / 2), int(img_h / 2)
                    ents.append({"entity_name": j, "entity_type": "default", "entity_coords": [cx, cy]})
            if ents: answers[task_key] = ents
    elif request_type == "image_drag_drop":
        for i, task in enumerate(tasklist):
            task_key = task.get("task_key", "")
            img_w, img_h = dims.get(task_key, (500, 400))
            drops = {}
            if i < len(solution) and solution[i]:
                for box in solution[i]:
                    if isinstance(box, dict):
                        eid = box.get("entity_id") or box.get("entity_name")
                        if eid: drops[eid] = box
            ents = []
            for ent in task.get("entities", []):
                eid = ent.get("entity_id") or ent.get("entity_name") or "0"
                size = list(ent.get("size") or [0, 0])
                ew = int(size[0]) if len(size) >= 1 else 0
                eh = int(size[1]) if len(size) >= 2 else 0
                if eid in drops:
                    box = drops[eid]
                    x = int(box.get("x", 0) / 100 * img_w)
                    y = int(box.get("y", 0) / 100 * img_h)
                    if ew: x = max(0, min(x, img_w - ew))
                    if eh: y = max(0, min(y, img_h - eh))
                else:
                    coords = list(ent.get("coords") or [0, 0])
                    x = int(coords[0]) if len(coords) >= 1 else 0
                    y = int(coords[1]) if len(coords) >= 2 else 0
                ents.append({"entity_name": eid, "entity_type": "default", "entity_coords": [x, y]})
            if ents: answers[task_key] = ents
    return answers
