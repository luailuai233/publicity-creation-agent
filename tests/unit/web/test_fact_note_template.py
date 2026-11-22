from pathlib import Path
from types import SimpleNamespace

from jinja2 import Environment, FileSystemLoader, select_autoescape


def test_pending_fact_note_offers_explicit_accept_and_ignore_actions() -> None:
    templates = Path(__file__).resolve().parents[3] / "workbench" / "templates"
    environment = Environment(loader=FileSystemLoader(templates), autoescape=select_autoescape())
    template = environment.get_template("facts/fact_note.html")
    fact = SimpleNamespace(id="fact-1", type="QUOTE", content="尚未公布", status="PENDING")

    html = template.render(fact=fact)

    assert 'data-update-fact="fact-1"' in html
    assert 'data-fact-status="CONFIRMED"' in html
    assert 'data-fact-status="INVALID"' in html
    assert "采用" in html
    assert "忽略" in html
