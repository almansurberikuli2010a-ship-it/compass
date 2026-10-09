import pytest

from app.checker import LineIn, check_lines


def run(*lines, **kw):
    return check_lines([LineIn(t) for t in lines], **kw)


def kinds(res):
    return [(s["status"], s["mistake"]["type"] if s["mistake"] else None) for s in res["steps"]]


def test_correct_solution_has_no_flags():
    r = run("Solve: 2x + 4 = 10", "2x = 6", "x = 3")
    assert kinds(r) == [("ok", None), ("ok", None)]
    assert r["answer_ok"] is True and not r["needs_task_photo"]


def test_ui_example_sign_slip_with_practice():
    r = run("Solve: 3(x - 2) = 15", "3x - 6 = 15", "3x = 15 - 6", "3x = 9", "x = 9 - 3")
    assert kinds(r)[0] == ("ok", None)
    m = r["steps"][1]["mistake"]
    assert m["type"] == "sign_slip" and m["certainty"] == "certain"
    assert "adding 6" in m["hint"] and m["practice"] == "3x - 6 + 6 = 15 + __"
    assert kinds(r)[2] == ("ok", None)          # follows the student's own previous line
    assert kinds(r)[3] == ("check", "wrong_operation")


def test_arithmetic_slip_in_final_answer():
    assert kinds(run("7x + 5 = 26", "7x = 21", "x = 2"))[-1] == ("check", "arithmetic_slip")


def test_operation_on_one_part_only_in_a_chain():
    assert kinds(run("3 <= 5x <= 10", "3 <= x <= 2"))[-1] == ("check", "both_sides")


def test_one_side_only():
    assert kinds(run("3x - 6 = 15", "3x = 15"))[-1] == ("check", "both_sides")


def test_inequality_sign_not_flipped():
    assert kinds(run("-5x < 10", "x < -2"))[-1] == ("check", "inequality_flip")
    assert kinds(run("-5x < 10", "x > -2"))[-1] == ("ok", None)


def test_distribution_unlike_terms_dropped_copy():
    assert kinds(run("2(x + 3)", "2x + 3"))[-1] == ("check", "distribution")
    assert kinds(run("3x + 2", "5x"))[-1] == ("check", "unlike_terms")
    assert kinds(run("x^2 + 5x + 6 = 0", "x^2 + 6 = 0"))[-1] == ("check", "dropped_term")
    assert kinds(run("3x - 5 = 10", "3x - 5 = 1"))[-1] == ("check", "copy_error")


def test_numeric_lines():
    assert kinds(run("7 x 8 = 54")) == [("check", "arithmetic_slip")]
    assert kinds(run("-3 + 5 = -8")) == [("check", "sign_slip")]
    assert kinds(run("2 + 3 * 4 = 20")) == [("check", "order_of_ops")]
    assert kinds(run("3 + 4 = 7 + 2 = 9")) == [("check", "equals_sign")]
    assert kinds(run("7 * 8 = 56")) == [("ok", None)]


def test_skipped_step_is_a_second_label():
    r = run("5(x + 1) + 3 = 5", "5x + 7 = 5")
    m = r["steps"][1]["mistake"]
    assert m["type"] == "arithmetic_slip" and [a["type"] for a in m["also"]] == ["skipped_step"]


def test_units():
    assert kinds(run("5cm + m + 7 = 0", "6cm + 7 = 0")) == [("ok", None), ("check", "unit_mistake")]


def test_correct_jump_is_accepted():
    assert kinds(run("3x - 6 = 15", "x = 7")) == [("ok", None), ("ok", None)]


def test_unclear_character_waits_for_confirmation():
    items = [LineIn("3x = 9"), LineIn("x = 7", unclear=[{"pos": 4, "alternatives": ["1", "7"]}])]
    assert kinds(check_lines(items)) == [("ok", None), ("unreadable", None)]


def test_messy_layout_from_boxes():
    items = [LineIn("3x = 9", box=[0.1, 0.1, 0.3, 0.05]), LineIn("x = 3", box=[0.7, 0.2, 0.3, 0.05])]
    assert kinds(check_lines(items))[-1] == ("check", "messy_layout")


def test_wrong_final_answer_without_flagged_step_asks_for_task_photo():
    r = run("Solve: 2x + 4 = 10", "x = 5")
    assert r["answer_ok"] is False


@pytest.mark.parametrize("bad", ["???", "hello world", "3x ="])
def test_unparseable_lines_do_not_crash(bad):
    assert run("3x = 9", bad)["steps"][-1]["status"] == "unchecked"
