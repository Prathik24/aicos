import pathlib
from core.schemas.commitment import Commitment

def test_valid_fixture_parses():
    raw = pathlib.Path("tests/fixtures/commitment_good.json").read_text()
    c = Commitment.model_validate_json(raw)
    assert c.status == "proposed"
    assert c.owner.kind == "unresolved"