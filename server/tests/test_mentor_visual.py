import pytest

from learnmate.mentor.visual import VisualError, parse_visual

BASE = {"caption": "Growth", "alt_text": "Plant height over four weeks"}


def chart(**kw):
    return {
        **BASE,
        "kind": "chart",
        "chart_type": "bar",
        "labels": ["a", "b"],
        "values": [1, 2],
        **kw,
    }


def test_visual_none_stays_none() -> None:
    assert parse_visual(None) is None


@pytest.mark.parametrize("chart_type", ["bar", "line", "pie"])
def test_visual_chart_bar_line_pie_accepted(chart_type: str) -> None:
    out = parse_visual(chart(chart_type=chart_type))
    assert out["chart_type"] == chart_type
    assert out["values"] == [1.0, 2.0]


def test_visual_steps_and_table_accepted() -> None:
    steps = {**BASE, "kind": "steps", "steps": ["one", "two"]}
    table = {**BASE, "kind": "table", "columns": ["x"], "rows": [["1"]]}
    assert parse_visual(steps)["steps"] == ["one", "two"]
    assert parse_visual(table)["rows"] == [["1"]]


@pytest.mark.parametrize("value", ["missing", "", "   "])
def test_visual_without_caption_rejected(value: str) -> None:
    raw = chart()
    if value == "missing":
        del raw["caption"]
    else:
        raw["caption"] = value
    with pytest.raises(VisualError):
        parse_visual(raw)


@pytest.mark.parametrize("value", ["missing", "", "   "])
def test_visual_without_alt_text_rejected(value: str) -> None:
    raw = chart()
    if value == "missing":
        del raw["alt_text"]
    else:
        raw["alt_text"] = value
    with pytest.raises(VisualError):
        parse_visual(raw)


def test_visual_unknown_kind_and_chart_type_rejected() -> None:
    for raw in ({**BASE, "kind": "figure"}, chart(chart_type="scatter")):
        with pytest.raises(VisualError):
            parse_visual(raw)


def test_visual_limits() -> None:
    table = {**BASE, "kind": "table", "columns": ["x", "y"]}
    bad = [
        chart(labels=list("abcdefg"), values=[1] * 7),
        chart(values=[1]),
        chart(values=["NaN", 1]),
        chart(values=[float("inf"), 1]),
        chart(chart_type="pie", values=[1, -2]),
        {**BASE, "kind": "steps", "steps": list("abcdef")},
        {**BASE, "kind": "steps", "steps": ["only one"]},
        {**table, "rows": [["1"]]},
        {**table, "rows": [["1", "2"]] * 5},
        {**BASE, "kind": "table", "columns": list("abcd"), "rows": [list("abcd")]},
    ]
    for raw in bad:
        with pytest.raises(VisualError):
            parse_visual(raw)
