#!/usr/bin/env python3
"""
Runnable (and self-contained) Python version of the clause-learning pseudocode.

Notes / assumptions (because the original is pseudocode):
- Literals are represented as strings:
  - objective literal: "p" or "~p" (explicit negation)
  - default negation isn't stored in the rule; instead, rule.neg is a list of objective literals
    that appear as "not <lit>" in the body.
- I is represented as a history of interpretations across iterations:
  I_hist[i] is a set of objective literals true at iteration i (0-based).
  The pseudocode uses I(i) and I(i-1); here we map that directly.
- `pi` is a list of Rule objects (a choice-resolved program).
- `choice_info` is a mapping Rule -> Optional[bool] to mimic the paper’s `pi[r] is None` test:
    * None  => rule counted as “choice rule for l”
    * True  => rule counted as “choice rule for ¬l”
  This is only used to reproduce the structure of `extract_choice` in the pseudocode.

This script focuses on “being runnable” and structurally faithful; you’ll likely want to adapt
the literal syntax, rule representation, and choice bookkeeping to match your implementation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple


# -----------------------------
# Basic rule / literal helpers
# -----------------------------

@dataclass(frozen=True)
class Rule:
    """A (choice-resolved) rule: head <- pos..., not neg..."""
    head: str
    pos: Tuple[str, ...] = ()
    neg: Tuple[str, ...] = ()  # objective literals that occur default-negated in the body


def is_objective_literal(lit: str) -> bool:
    # Treat anything not starting with "not " as objective here.
    # (We also assume explicit negation is encoded as "~p".)
    return not lit.strip().startswith("not ")


def lnot(lit: str) -> str:
    """String form used by the pseudocode for negation in the learned clause."""
    return f"lnot({lit})"


def I_at(I_hist: Sequence[Set[str]], idx: int) -> Set[str]:
    """Safe access to interpretation history; negative indices yield empty set."""
    if idx < 0:
        return set()
    if idx >= len(I_hist):
        # If caller asks for a future iteration, treat as last known.
        return set(I_hist[-1]) if I_hist else set()
    return I_hist[idx]


def head(r: Rule) -> str:
    return r.head


def pos(r: Rule) -> Tuple[str, ...]:
    return r.pos


def neg(r: Rule) -> Tuple[str, ...]:
    return r.neg


# -----------------------------
# Pseudocode -> runnable code
# -----------------------------

def selection_rule(r: Rule, I_hist: Sequence[Set[str]], i: int) -> Tuple[Optional[Rule], Optional[Rule]]:
    """
    If all positive body literals are in I(i) and all negative-body objective literals are NOT in I(i-1),
    then r "fires".
    """
    firing_rule: Optional[Rule] = None
    not_firing_rule: Optional[Rule] = None

    cond_pos = all(b in I_at(I_hist, i) for b in pos(r))
    cond_neg = all(b not in I_at(I_hist, i - 1) for b in neg(r))

    if cond_pos and cond_neg:
        firing_rule = r
    else:
        not_firing_rule = r

    return firing_rule, not_firing_rule


def selection_rules(lit: str, pi: Iterable[Rule], I_hist: Sequence[Set[str]], i: int) -> Tuple[List[Rule], List[Rule]]:
    firing_rules: List[Rule] = []
    neg_firing_rules: List[Rule] = []

    for r in pi:
        if head(r) != lit:
            continue
        f_r, n_f_r = selection_rule(r, I_hist, i)
        if f_r is not None:
            firing_rules.append(f_r)
        else:
            neg_firing_rules.append(n_f_r)  # type: ignore[arg-type]

    return firing_rules, neg_firing_rules


def extract_choice(
    lit: str,
    I_hist: Sequence[Set[str]],
    i: int,
    choice_info: Dict[Rule, Optional[bool]],
) -> Tuple[List[Rule], List[Rule]]:
    """
    Mirrors the paper’s structure:
      - if choice_info[r] is None => rule is counted in c_r_rules_for_l
      - else                      => rule is counted in c_r_rules_for_neg_l
    """
    c_r_rules_for_l: List[Rule] = []
    c_r_rules_for_neg_l: List[Rule] = []

    for r, tag in choice_info.items():
        if tag is None:
            c_r_rules_for_l.append(r)
        else:
            c_r_rules_for_neg_l.append(r)

    return c_r_rules_for_l, c_r_rules_for_neg_l


def _join_bool_expr(op: str, parts: List[str]) -> str:
    """Join non-empty parts with op; if empty, return empty string."""
    parts = [p for p in parts if p]
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    return f" {op} ".join(parts)


def not_prevent(
    lit: str,
    pi: Iterable[Rule],
    I_hist: Sequence[Set[str]],
    i: int,
    choice_info: Dict[Rule, Optional[bool]],
    _memo: Optional[Dict[Tuple[str, int, str], object]] = None,
) -> object:
    """
    Returns either False or a boolean expression string, following the paper’s shape.
    """
    if _memo is None:
        _memo = {}
    key = ("not_prevent", i, lit)
    if key in _memo:
        return _memo[key]

    if not is_objective_literal(lit):
        _memo[key] = False
        return False

    f_rules, _n_f_rules = selection_rules(lit, pi, I_hist, i)
    _c_r_for_l, c_r_for_neg_l = extract_choice(lit, I_hist, i, choice_info)

    if len(f_rules) == 0:
        _memo[key] = False
        return False

    disjuncts: List[str] = []
    for r in f_rules:
        to_prevent_parts: List[str] = []
        for b in pos(r):
            v = not_prevent(b, pi, I_hist, i, choice_info, _memo)
            if v is not False:
                to_prevent_parts.append(str(v))

        not_to_prevent_parts: List[str] = []
        for b in neg(r):
            v = prevent(b, pi, I_hist, i - 1, choice_info, _memo)
            if v is not False:
                not_to_prevent_parts.append(str(v))

        big_conjunct_parts: List[str] = []
        tp = _join_bool_expr("AND", to_prevent_parts)
        ntp = _join_bool_expr("AND", not_to_prevent_parts)
        if tp:
            big_conjunct_parts.append(tp)
        if ntp:
            big_conjunct_parts.append(ntp)

        # If r is among choice rules for ¬l, add "l" (as in the pseudocode).
        if r in c_r_for_neg_l:
            big_conjunct_parts.append(lit)

        disjuncts.append(_join_bool_expr("AND", big_conjunct_parts))

    result = _join_bool_expr("OR", disjuncts)
    _memo[key] = result
    return result


def prevent(
    lit: str,
    pi: Iterable[Rule],
    I_hist: Sequence[Set[str]],
    i: int,
    choice_info: Dict[Rule, Optional[bool]],
    _memo: Optional[Dict[Tuple[str, int, str], object]] = None,
) -> object:
    """
    Returns either False or a boolean expression string, following the paper’s shape.
    """
    if _memo is None:
        _memo = {}
    key = ("prevent", i, lit)
    if key in _memo:
        return _memo[key]

    if not is_objective_literal(lit):
        _memo[key] = False
        return False

    f_rules, _n_f_rules = selection_rules(lit, pi, I_hist, i)
    c_r_for_l, _c_r_for_neg_l = extract_choice(lit, I_hist, i, choice_info)

    if len(f_rules) == 0:
        _memo[key] = False
        return False

    conjuncts: List[str] = []
    for r in f_rules:
        to_prevent_parts: List[str] = []
        for b in pos(r):
            v = prevent(b, pi, I_hist, i, choice_info, _memo)
            if v is not False:
                to_prevent_parts.append(str(v))

        not_to_prevent_parts: List[str] = []
        for b in neg(r):
            v = not_prevent(b, pi, I_hist, i - 1, choice_info, _memo)
            if v is not False:
                not_to_prevent_parts.append(str(v))

        big_disjunct_parts: List[str] = []
        tp = _join_bool_expr("OR", to_prevent_parts)
        ntp = _join_bool_expr("OR", not_to_prevent_parts)
        if tp:
            big_disjunct_parts.append(tp)
        if ntp:
            big_disjunct_parts.append(ntp)

        # If r is among choice rules for l, add lnot(l).
        if r in c_r_for_l:
            big_disjunct_parts.append(lnot(lit))

        conjuncts.append(_join_bool_expr("OR", big_disjunct_parts))

    result = _join_bool_expr("AND", conjuncts)
    _memo[key] = result
    return result


def extract_clause(
    conflicting_pairs: Iterable[Tuple[str, str]],
    pi: Iterable[Rule],
    I_hist: Sequence[Set[str]],
    i: int,
    choice_info: Dict[Rule, Optional[bool]],
) -> str:
    """
    conflicting_pairs: iterable of (p, ~p)-style contradictory objective literals.
    Returns a learned clause string.
    """
    clause_parts: List[str] = []
    for p, np in conflicting_pairs:
        left = prevent(p, pi, I_hist, i, choice_info)
        right = prevent(np, pi, I_hist, i, choice_info)
        left_s = "False" if left is False else str(left)
        right_s = "False" if right is False else str(right)
        clause_parts.append(f"{left_s} OR {right_s}")
    return _join_bool_expr("AND", clause_parts)


# -----------------------------
# Small demo (so it "runs")
# -----------------------------

def main() -> None:
    # Example tiny program:
    #   p <- q, not r
    #   ~p <- s
    pi = [
        Rule("p", pos=("q",), neg=("r",)),
        Rule("~p", pos=("s",), neg=()),
    ]

    # Choice bookkeeping (optional; just to exercise the extract_choice path)
    # Mark first rule as "None" => counted in c_r_for_l; second as True => c_r_for_neg_l
    choice_info: Dict[Rule, Optional[bool]] = {
        pi[0]: None,
        pi[1]: True,
    }

    # Interpretation history across iterations i=0..2 (objective literals true at each step)
    I_hist = [
        {"q"},          # i=0
        {"q", "s"},     # i=1
        {"q", "s"},     # i=2
    ]

    # Suppose conflict is p vs ~p at iteration i=2
    learned = extract_clause([("p", "~p")], pi, I_hist, i=2, choice_info=choice_info)
    print("Learned clause:")
    print(learned)


if __name__ == "__main__":
    main()
