from pathlib import Path


def append(event) -> None:
    Path("data").mkdir(exist_ok=True)
    with open("data/audit.jsonl", "a") as f:
        f.write(event.model_dump_json() + "\n")