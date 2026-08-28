from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from core.schemas.validation import ValidationReport
from core.identity import commitment_key, decision_key, key_fact_key
from pipeline.validate import _owner_str



_FLAG_COLORS = {"anchor_failed": "red",
                "date_in_action_without_due": "amber",
                "due_unparseable": "amber",
                "duplicate_merged": "info"}


def render_package(report: ValidationReport, meeting_label: str,
                   out_path: str = "data/out/approval_package.html") -> str :
    by_key: dict[str, list] = {}
    for f in report.flags:
        by_key.setdefault(f.record_key, []).append(f)

    items = []

    for c in report.commitments:
        k = commitment_key(owner=_owner_str(c.owner), action=c.action)
        items.append({"kind": "commitment", "key": k, "title": c.action,
                      "owner": c.owner.raw_mention, "record": c,
                      "flags": by_key.get(k, [])})
    for d in report.decisions:
        k = decision_key(owner=_owner_str(d.owner), statement=d.statement)
        items.append({"kind": "decision", "key": k, "title": d.statement,
                        "owner": d.owner.raw_mention, "record": d,
                        "flags": by_key.get(k, [])})
    for kf in report.key_facts:
        k = key_fact_key(statement=kf.statement)
        items.append({"kind": "key fact", "key": k, "title": kf.statement,
                      "owner": None, "record": kf,
                      "flags": by_key.get(k, [])})

    env = Environment(loader=FileSystemLoader("pipeline/templates"))
    env.filters["flag_color"] = lambda rule: _FLAG_COLORS.get(rule, "info")
    html = env.get_template("package.html.j2").render(
        meeting_label=meeting_label, items=items)

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html)
    return str(out)
    


