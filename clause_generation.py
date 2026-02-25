#!/usr/bin/env python3
import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple


@dataclass(frozen=True)
class Rule:
    rule_id: str
    head: str
    pos: Tuple[str, ...]
    neg: Tuple[str, ...]
    choice_tag: str = "none"


def is_objective_literal(lit: str) -> bool:
    return not lit.startswith("naf(")


def I_at(I_hist: Dict[int, Set[str]], idx: int) -> Set[str]:
    if idx < 0:
        return set()
    return I_hist.get(idx, set())


def selection_rule(r: Rule, I_hist: Dict[int, Set[str]], i: int) -> Tuple[Optional[Rule], Optional[Rule]]:
    cond_pos = all(b in I_at(I_hist, i) for b in r.pos)
    cond_neg = all(b not in I_at(I_hist, i - 1) for b in r.neg)
    if cond_pos and cond_neg:
        return r, None
    return None, r


def selection_rules(lit: str, rules: Iterable[Rule], I_hist: Dict[int, Set[str]], i: int) -> Tuple[List[Rule], List[Rule]]:
    firing_rules: List[Rule] = []
    not_firing_rules: List[Rule] = []
    for r in rules:
        if r.head != lit:
            continue
        fr, nfr = selection_rule(r, I_hist, i)
        if fr is not None:
            firing_rules.append(fr)
        elif nfr is not None:
            not_firing_rules.append(nfr)
    return firing_rules, not_firing_rules


def extract_choice(lit: str, rules: Iterable[Rule]) -> Tuple[List[Rule], List[Rule]]:
    c_r_rules_for_l = [r for r in rules if r.head == lit and r.choice_tag == "selected"]
    c_r_rules_for_neg_l = [r for r in rules if r.head == lit and r.choice_tag == "forced_dual"]
    return c_r_rules_for_l, c_r_rules_for_neg_l


def _join_bool_expr(op: str, parts: List[str]) -> str:
    parts = [p for p in parts if p]
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    return f" {op} ".join(parts)


def lnot(lit: str, dual_map: Dict[str, str]) -> str:
    return dual_map.get(lit, f"lnot({lit})")


def not_prevent(
    lit: str,
    rules: Sequence[Rule],
    I_hist: Dict[int, Set[str]],
    i: int,
    dual_map: Dict[str, str],
    memo: Dict[Tuple[str, int, str], object],
) -> object:
    key = ("not_prevent", i, lit)
    if key in memo:
        return memo[key]
    memo[key] = False

    if not is_objective_literal(lit):
        return False

    f_rules, _ = selection_rules(lit, rules, I_hist, i)
    _, c_r_for_neg_l = extract_choice(lit, rules)
    if not f_rules:
        return False

    disjuncts: List[str] = []
    for r in f_rules:
        to_prevent_parts: List[str] = []
        for b in r.pos:
            v = not_prevent(b, rules, I_hist, i, dual_map, memo)
            if v is not False:
                to_prevent_parts.append(str(v))

        not_to_prevent_parts: List[str] = []
        for b in r.neg:
            v = prevent(b, rules, I_hist, i - 1, dual_map, memo)
            if v is not False:
                not_to_prevent_parts.append(str(v))

        conjuncts: List[str] = []
        tp = _join_bool_expr("AND", to_prevent_parts)
        ntp = _join_bool_expr("AND", not_to_prevent_parts)
        if tp:
            conjuncts.append(tp)
        if ntp:
            conjuncts.append(ntp)
        if r in c_r_for_neg_l:
            conjuncts.append(lit)

        disjuncts.append(_join_bool_expr("AND", conjuncts))

    result = _join_bool_expr("OR", disjuncts)
    memo[key] = result
    return result


def prevent(
    lit: str,
    rules: Sequence[Rule],
    I_hist: Dict[int, Set[str]],
    i: int,
    dual_map: Dict[str, str],
    memo: Dict[Tuple[str, int, str], object],
) -> object:
    key = ("prevent", i, lit)
    if key in memo:
        return memo[key]
    memo[key] = False

    if not is_objective_literal(lit):
        return False

    f_rules, _ = selection_rules(lit, rules, I_hist, i)
    c_r_for_l, _ = extract_choice(lit, rules)
    if not f_rules:
        return False

    conjuncts: List[str] = []
    for r in f_rules:
        to_prevent_parts: List[str] = []
        for b in r.pos:
            v = prevent(b, rules, I_hist, i, dual_map, memo)
            if v is not False:
                to_prevent_parts.append(str(v))

        not_to_prevent_parts: List[str] = []
        for b in r.neg:
            v = not_prevent(b, rules, I_hist, i - 1, dual_map, memo)
            if v is not False:
                not_to_prevent_parts.append(str(v))

        disjuncts: List[str] = []
        tp = _join_bool_expr("OR", to_prevent_parts)
        ntp = _join_bool_expr("OR", not_to_prevent_parts)
        if tp:
            disjuncts.append(tp)
        if ntp:
            disjuncts.append(ntp)
        if r in c_r_for_l:
            disjuncts.append(lnot(lit, dual_map))

        conjuncts.append(_join_bool_expr("OR", disjuncts))

    result = _join_bool_expr("AND", conjuncts)
    memo[key] = result
    return result


def extract_clause(
    conflicting_pairs: Iterable[Tuple[str, str]],
    rules: Sequence[Rule],
    I_hist: Dict[int, Set[str]],
    i: int,
    dual_map: Dict[str, str],
) -> str:
    memo: Dict[Tuple[str, int, str], object] = {}
    clause_parts: List[str] = []
    for p, np in conflicting_pairs:
        left = prevent(p, rules, I_hist, i, dual_map, memo)
        right = prevent(np, rules, I_hist, i, dual_map, memo)
        disjuncts: List[str] = []
        if left is not False and str(left):
            disjuncts.append(str(left))
        if right is not False and str(right):
            disjuncts.append(str(right))
        if not disjuncts:
            clause_parts.append("False")
        else:
            clause_parts.append(_join_bool_expr("OR", disjuncts))
    return _join_bool_expr("AND", clause_parts)


def load_rules(raw_rules: Sequence[Dict[str, object]]) -> List[Rule]:
    rules: List[Rule] = []
    for row in raw_rules:
        head = row.get("head")
        if not isinstance(head, str):
            continue
        rules.append(
            Rule(
                rule_id=str(row["rule_id"]),
                head=head,
                pos=tuple(str(x) for x in row.get("pos", [])),
                neg=tuple(str(x) for x in row.get("neg", [])),
                choice_tag=str(row.get("choice_tag", "none")),
            )
        )
    return rules


def pick_target_iteration(trace: Dict[str, object], requested_iteration: Optional[int]) -> Dict[str, object]:
    raw_iterations = trace.get("iterations", [])
    if not isinstance(raw_iterations, list) or not raw_iterations:
        raise ValueError("Trace has no iterations.")

    if requested_iteration is not None:
        for row in raw_iterations:
            if int(row["iteration"]) == requested_iteration:
                return row
        raise ValueError(f"Iteration {requested_iteration} not found in trace.")

    no_model_rows = [row for row in raw_iterations if bool(row.get("no_model"))]
    if no_model_rows:
        return no_model_rows[-1]

    conflict_rows = [row for row in raw_iterations if row.get("conflicts")]
    if conflict_rows:
        return conflict_rows[-1]

    return raw_iterations[-1]


def collect_conflicts(iteration_row: Dict[str, object], dual_map: Dict[str, str]) -> List[Tuple[str, str]]:
    out: List[Tuple[str, str]] = []
    raw_conflicts = iteration_row.get("conflicts", [])
    if isinstance(raw_conflicts, list):
        for row in raw_conflicts:
            left = row.get("left")
            right = row.get("right")
            if isinstance(left, str) and isinstance(right, str):
                out.append((left, right))
    if out:
        return out

    interpretation = set(str(x) for x in iteration_row.get("interpretation", []))
    seen: Set[Tuple[str, str]] = set()
    for lit in interpretation:
        dual = dual_map.get(lit)
        if dual is None or dual not in interpretation:
            continue
        key = tuple(sorted((lit, dual)))
        if key in seen:
            continue
        seen.add(key)
        out.append((lit, dual))
    out.sort()
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate learned clause from XWFS trace")
    parser.add_argument("trace_json", type=Path, help="Trace file produced by compute_xwfs_model.py --trace-json")
    parser.add_argument("--iteration", type=int, default=None, help="Target iteration (default: latest conflicting/no_model)")
    parser.add_argument(
        "--program-version",
        choices=["auto", "normal", "seminormal"],
        default="auto",
        help="Rule version to use for clause extraction",
    )
    args = parser.parse_args()

    trace = json.loads(args.trace_json.read_text(encoding="utf-8"))
    iter_row = pick_target_iteration(trace, args.iteration)
    iteration = int(iter_row["iteration"])
    phase = str(iter_row.get("phase", "normal"))

    if args.program_version == "normal":
        raw_rules = iter_row.get("normal_program", [])
        program_version_used = "normal"
    elif args.program_version == "seminormal":
        raw_rules = iter_row.get("seminormal_program", [])
        program_version_used = "seminormal"
    else:
        raw_semi = iter_row.get("seminormal_program", [])
        if phase == "seminormal" and isinstance(raw_semi, list) and len(raw_semi) > 0:
            raw_rules = raw_semi
            program_version_used = "seminormal"
        else:
            raw_rules = iter_row.get("normal_program", [])
            program_version_used = "normal"

    rules = load_rules(raw_rules if isinstance(raw_rules, list) else [])
    raw_hist = trace.get("interpretation_history", {})
    I_hist = {int(k): set(str(x) for x in v) for k, v in raw_hist.items()} if isinstance(raw_hist, dict) else {}

    raw_dual = trace.get("dual_map", {})
    dual_map = {str(k): str(v) for k, v in raw_dual.items()} if isinstance(raw_dual, dict) else {}

    conflicts = collect_conflicts(iter_row, dual_map)
    if not conflicts:
        print("No conflicts found; no clause generated.")
        return

    clause = extract_clause(conflicts, rules, I_hist, iteration, dual_map)
    print(f"iteration: {iteration}")
    print(f"phase: {phase}")
    print(f"program_version: {program_version_used}")
    print(f"conflicts: {conflicts}")
    print("learned_clause:")
    print(clause if clause else "False")


if __name__ == "__main__":
    main()
