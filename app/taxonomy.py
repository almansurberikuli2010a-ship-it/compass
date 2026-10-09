"""Every mistake type in one place.

name   -> what the student sees
row    -> label of the row in the teacher heatmap
plural -> used in the teacher insight sentence
blurb  -> one line for the student legend
"""

TYPES = {
    "sign_slip": ("Sign slip", "Sign slips", "sign slips", "A plus or minus changed on the way."),
    "arithmetic_slip": ("Arithmetic slip", "Arithmetic", "arithmetic slips", "A calculation is slightly off."),
    "both_sides": ("One side only", "Operation", "one-sided moves", "A move was made on one side but not the other."),
    "wrong_operation": ("Different moves", "Operation", "mismatched moves", "The two sides got different operations."),
    "distribution": ("Distribution", "Distribution", "distribution slips", "The number outside brackets must reach every term."),
    "unlike_terms": ("Unlike terms", "Like terms", "unlike-term merges", "Terms that don't match were added together."),
    "dropped_term": ("Dropped term", "Dropped terms", "dropped terms", "A term disappeared between two lines."),
    "copy_error": ("Copy slip", "Copy slips", "copy slips", "A number changed while copying a line."),
    "inequality_flip": ("Inequality sign", "Inequality sign", "inequality-sign slips", "Multiplying or dividing by a negative flips the sign."),
    "order_of_ops": ("Order of operations", "Order of operations", "order-of-operations slips", "Multiplication and division come first."),
    "equals_sign": ("Equals sign", "Equals sign", "equals-sign slips", "'=' means 'is the same as', not 'now do'."),
    "unit_mistake": ("Units", "Units", "unit slips", "Different units were combined."),
    "messy_layout": ("Layout", "Layout", "layout issues", "Lines wander, so the steps are hard to follow."),
    "unclear_char": ("Unreadable", "Unreadable", "unreadable characters", "A character could be read two ways."),
    "check": ("Check this step", "Other", "unexplained steps", "This step doesn't follow from the line above."),
}


def name(t):
    return TYPES.get(t, TYPES["check"])[0]


def row(t):
    return TYPES.get(t, TYPES["check"])[1]


def plural(t):
    return TYPES.get(t, TYPES["check"])[2]


def legend():
    return [{"type": t, "name": v[0], "blurb": v[3]} for t, v in TYPES.items() if t != "check"]


_BALANCE = ("Keep both sides balanced", [
    (1, "Show an equation as a balance scale."),
    (2, "Do one move on both sides, together, out loud."),
    (2, "Try a new equation alone, then send a pulse."),
])

PLANS = {
    "sign_slip": _BALANCE,
    "both_sides": _BALANCE,
    "wrong_operation": ("Undo with the opposite move", [
        (1, "Ask: what is happening to x? Name the move."),
        (2, "Undo it with the opposite move, on both sides."),
        (2, "Try one more equation, then send a pulse."),
    ]),
    "arithmetic_slip": ("Slow down the calculation", [
        (1, "Show how to estimate an answer before calculating."),
        (2, "Pairs check each other's last line."),
        (2, "One more problem, then send a pulse."),
    ]),
    "distribution": ("Reach every term in the brackets", [
        (1, "Draw arrows from the outside number to each term."),
        (2, "Expand three examples together."),
        (2, "Try one alone, then send a pulse."),
    ]),
    "unlike_terms": ("Only like terms combine", [
        (1, "Sort terms into groups: x-terms and plain numbers."),
        (2, "Combine inside each group only."),
        (2, "Try one alone, then send a pulse."),
    ]),
}
DEFAULT_PLAN = ("Revisit the last step together", [
    (1, "Put the last worked example on the board."),
    (2, "Ask students to explain the step to a partner."),
    (2, "Try a similar problem, then send a pulse."),
])


def plan(t):
    title, steps = PLANS.get(t, DEFAULT_PLAN)
    return {"title": title, "steps": [{"min": m, "text": s} for m, s in steps]}
