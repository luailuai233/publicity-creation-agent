from pathlib import Path

from docx import Document

from workbench.materials.parsers import parse_path


def test_docx_preserves_paragraph_and_table_row_locations(tmp_path: Path) -> None:
    path = tmp_path / "source.docx"
    document = Document()
    document.add_paragraph("第一段")
    document.add_paragraph("   ")
    table = document.add_table(rows=2, cols=2)
    table.rows[0].cells[0].text = "姓名"
    table.rows[0].cells[1].text = "小林"
    table.rows[1].cells[0].text = "行动"
    table.rows[1].cells[1].text = "负责讲解"
    document.save(path)

    result = parse_path(path, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

    assert [chunk.content for chunk in result.chunks] == ["第一段", "姓名 | 小林", "行动 | 负责讲解"]
    assert result.chunks[0].paragraph == 1
    assert result.chunks[1].location == "table:1:row:1"


def test_text_parser_returns_one_located_chunk(tmp_path: Path) -> None:
    path = tmp_path / "note.txt"
    path.write_text("活动说明", encoding="utf-8")

    result = parse_path(path, "text/plain")

    assert result.chunks[0].paragraph == 1
    assert result.chunks[0].content == "活动说明"
