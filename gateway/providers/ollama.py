import requests


def chat(model: str, prompt: str, format: dict | None = None) -> str:
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }
    if format is not None:
        body["format"] = format
    resp = requests.post("http://localhost:11434/api/chat", json=body, timeout = 4000)
    if resp.status_code != 200:
        raise RuntimeError(f"Ollama {resp.status_code}: {resp.text[:500]}")
    data = resp.json()
    return data["message"]["content"]

    