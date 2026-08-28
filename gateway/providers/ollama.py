import requests


def chat(model: str, prompt: str, format: dict | None = None) -> str:
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options" : {"num_ctx" : 32768}
    }
    if format is not None:
        body["format"] = format
    resp = requests.post("http://localhost:11434/api/chat", json=body, timeout = 4000)
    if resp.status_code != 200:
        raise RuntimeError(f"Ollama {resp.status_code}: {resp.text[:500]}")
    data = resp.json()
    return {
        "content": data["message"]["content"],
        "tokens_in": data.get("prompt_eval_count"),
        "tokens_out": data.get("eval_count"),
        "duration_ms": (data.get("total_duration") or 0) // 1_000_000 or None,
        "load_ms": (data.get("load_duration") or 0) // 1_000_000 or None,
        "eval_ms": (data.get("eval_duration") or 0) // 1_000_000 or None,
        "done_reason": data.get("done_reason"),
    }

    