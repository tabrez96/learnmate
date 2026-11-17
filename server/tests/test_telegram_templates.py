import datetime as dt

import pytest

from learnmate.telegram import templates as t


def test_session_started():
    assert (
        t.session_started("Maya", "Science", "16:05").text
        == "Maya started a Science session (16:05)."
    )


def test_session_pin_new_has_button():
    m = t.session_pin("Maya", "4821", 12, "new")
    assert (
        m.text
        == "Session PIN for Maya's session: 4821. It works for this session only."
    )
    assert m.buttons == (t.Button("New PIN", "new_pin:12"),)


def test_session_pin_replaced():
    m = t.session_pin("Maya", "1357", 12, "replaced")
    assert (
        m.text
        == "New session PIN for Maya's session: 1357. The old PIN no longer works."
    )
    assert m.buttons == (t.Button("New PIN", "new_pin:12"),)


def test_session_pin_resent():
    m = t.session_pin("Maya", "4821", 12, "resent")
    assert (
        m.text
        == "The session PIN again: 4821. It's the same PIN as when the session started."
    )
    assert m.buttons == (t.Button("New PIN", "new_pin:12"),)


def test_grade_daily():
    m = t.grade("Maya", "daily", "Photosynthesis", 80, "B", 4, 5, 25)
    assert m.text == (
        "Maya finished the daily test on Photosynthesis: 80% (B), 4 of 5. Studied 25 min."
    )
    assert m.buttons == ()


@pytest.mark.parametrize(
    ("kind", "label"),
    [("weekly", "the weekly test"), ("surprise", "the surprise test")],
)
def test_grade_other_kinds(kind, label):
    m = t.grade("Maya", kind, "Fractions", 60, "D", 3, 5, 10)
    assert m.text.startswith(f"Maya finished {label} on Fractions: 60% (D)")


def test_grade_test_only():
    m = t.grade("Maya", "test_only", "Fractions", 100, "A", 5, 5, 0)
    assert m.text == (
        "Maya finished a test-only session on Fractions: 100% (A), 5 of 5. Studied 0 min."
    )


def test_grade_rejects_ungraded_kind():
    with pytest.raises(ValueError):
        t.grade("Maya", "warmup", "Fractions", 100, "A", 5, 5, 0)


def test_left_app():
    assert (
        t.left_app("Maya", "16:10").text
        == "Maya left Learnmate during the session (16:10)."
    )


def test_back_in_app():
    assert t.back_in_app("Maya", "16:12").text == "Maya is back (16:12)."


def test_locked():
    assert t.locked("Maya", 5, "16:20").text == (
        "Maya's session locked after 5 minutes with no activity (16:20)."
    )


def test_unlocked():
    assert t.unlocked("Maya", "16:21").text == "Maya's session was unlocked (16:21)."


def test_pin_lockout():
    assert t.pin_lockout("Maya", 5, "16:45").text == (
        "5 wrong PINs on Maya's session. "
        "The PIN pad is locked until 16:45; the session keeps running."
    )


def test_fallback_lockout():
    assert t.fallback_lockout("Maya", 3, "17:30").text == (
        "3 wrong fallback passwords on Maya's session. "
        "The fallback password is locked until 17:30."
    )


def test_force_ended():
    assert t.force_ended("Maya", "16:50").text == (
        "Maya's session was force-ended with the fallback password (16:50)."
    )


def test_budget_warning():
    assert t.budget_warning(80, 8.0, 10.0).text == (
        "AI spending this month is at 80% (8.00 of 10.00 USD)."
    )


def test_budget_reached():
    assert t.budget_reached(10.004, 10.0).text == (
        "AI spending this month reached the budget (10.00 of 10.00 USD). "
        "New lessons and material reading are paused until next month "
        "or until the budget is raised."
    )


def _summary(**kw):
    base = {
        "child": "Maya",
        "subject": "Science",
        "studied_min": 30,
        "score_pct": 80,
        "band": "B",
        "missed": False,
        "points": 45,
        "left_count": 0,
        "lock_minutes": (),
        "force_ended": False,
    }
    return t.SessionSummary(**{**base, **kw})


def test_summary_full():
    m = t.summary(_summary(left_count=2, lock_minutes=(8, 5), force_ended=True))
    assert m.text.splitlines() == [
        "Session summary: Maya, Science",
        "Studied 30 min",
        "Test: 80% (B)",
        "Points: +45",
        "Left Learnmate: 2 times",
        "Locked 2 times for no activity, 13 min",
        "Force-ended with the fallback password",
    ]


def test_summary_missed_and_quiet():
    text = t.summary(_summary(score_pct=None, band=None, missed=True)).text
    assert "Test: Missed" in text
    assert "Left Learnmate: not once" in text
    assert "Locked" not in text
    assert "Force-ended" not in text


def test_summary_no_test_left_once():
    text = t.summary(
        _summary(score_pct=None, band=None, left_count=1, lock_minutes=(5,))
    ).text
    assert "Test: none" in text
    assert "Left Learnmate: once" in text
    assert "Locked once for no activity, 5 min" in text


def test_clock_time_converts_timezone():
    assert t.clock_time(dt.datetime(2026, 1, 5, 9, 0), "Asia/Kolkata") == "14:30"
