from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from workbench.facts.schemas import ConflictFactOption, ConflictGroupDetail, ConflictSourceEvidence


def test_conflict_partial_renders_a_resolution_control_for_each_candidate() -> None:
    templates = Path(__file__).resolve().parents[3] / "workbench" / "templates"
    environment = Environment(loader=FileSystemLoader(templates), autoescape=select_autoescape())
    template = environment.get_template("facts/conflict_resolver.html")
    detail = ConflictGroupDetail(
        id="number-internal-id",
        fact_type="NUMBER",
        options=[
            ConflictFactOption(
                id="fact-36",
                content="36 人",
                sources=[ConflictSourceEvidence(label="流程.docx · 第 4 段", excerpt="共有 36 人")],
            ),
            ConflictFactOption(
                id="fact-12",
                content="12 人",
                sources=[ConflictSourceEvidence(label="采访.docx · 第 7 段", excerpt="共有 12 人")],
            ),
        ],
    )

    html = template.render(conflict_details=[detail])

    assert html.count('data-resolve-conflict="number-internal-id"') == 2
    assert 'data-fact-id="fact-36"' in html
    assert 'data-fact-id="fact-12"' in html
