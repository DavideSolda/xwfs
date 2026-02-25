import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

import clingo


def atom_to_str(sym: clingo.Symbol) -> str:
    return str(sym)


def arg_to_int(sym: clingo.Symbol) -> int:
    if sym.type != clingo.SymbolType.Number:
        raise ValueError(f"Expected numeric symbol, got: {sym}")
    return int(sym.number)


def build_rule_map(symbols: Set[clingo.Symbol], pos_pred: str, neg_pred: str, iteration: Optional[int]) -> Dict[str, Dict[str, object]]:
    heads: Dict[str, str] = {}
    pos_by_rule: Dict[str, Set[str]] = defaultdict(set)
    neg_by_rule: Dict[str, Set[str]] = defaultdict(set)

    for atom in symbols:
        if atom.name == "resolved_head" and len(atom.arguments) == 2:
            heads[atom_to_str(atom.arguments[0])] = atom_to_str(atom.arguments[1])

    for atom in symbols:
        if atom.name != pos_pred:
            continue
        if iteration is not None:
            if len(atom.arguments) != 3 or arg_to_int(atom.arguments[2]) != iteration:
                continue
        elif len(atom.arguments) != 2:
            continue
        rid = atom_to_str(atom.arguments[0])
        lit = atom_to_str(atom.arguments[1])
        pos_by_rule[rid].add(lit)

    for atom in symbols:
        if atom.name != neg_pred:
            continue
        if iteration is not None:
            if len(atom.arguments) != 3 or arg_to_int(atom.arguments[2]) != iteration:
                continue
        elif len(atom.arguments) != 2:
            continue
        rid = atom_to_str(atom.arguments[0])
        lit = atom_to_str(atom.arguments[1])
        neg_by_rule[rid].add(lit)

    rule_ids = set(heads.keys()) | set(pos_by_rule.keys()) | set(neg_by_rule.keys())
    rules: Dict[str, Dict[str, object]] = {}
    for rid in rule_ids:
        rules[rid] = {
            "rule_id": rid,
            "head": heads.get(rid),
            "pos": sorted(pos_by_rule.get(rid, set())),
            "neg": sorted(neg_by_rule.get(rid, set())),
        }
    return rules


def extract_choice_trace(symbols: Set[clingo.Symbol]) -> Tuple[List[Dict[str, str]], List[Dict[str, str]], Dict[str, str]]:
    selected: List[Dict[str, str]] = []
    forced_dual: List[Dict[str, str]] = []
    rule_choice_tag: Dict[str, str] = {}

    for atom in symbols:
        if atom.name == "choice_selected" and len(atom.arguments) == 3:
            rid = f"({atom_to_str(atom.arguments[0])},{atom_to_str(atom.arguments[2])})"
            selected.append(
                {
                    "rule_id": atom_to_str(atom.arguments[0]),
                    "choice_id": atom_to_str(atom.arguments[1]),
                    "literal": atom_to_str(atom.arguments[2]),
                    "resolved_rule_id": rid,
                }
            )
            rule_choice_tag[rid] = "selected"
        elif atom.name == "choice_forced_dual" and len(atom.arguments) == 4:
            rid = f"({atom_to_str(atom.arguments[0])},{atom_to_str(atom.arguments[3])})"
            forced_dual.append(
                {
                    "rule_id": atom_to_str(atom.arguments[0]),
                    "choice_id": atom_to_str(atom.arguments[1]),
                    "unselected_literal": atom_to_str(atom.arguments[2]),
                    "forced_dual": atom_to_str(atom.arguments[3]),
                    "resolved_rule_id": rid,
                }
            )
            rule_choice_tag[rid] = "forced_dual"

    selected.sort(key=lambda x: (x["rule_id"], x["choice_id"], x["literal"]))
    forced_dual.sort(key=lambda x: (x["rule_id"], x["choice_id"], x["unselected_literal"]))
    return selected, forced_dual, rule_choice_tag


def add_choice_tags(program_rules: Dict[str, Dict[str, object]], rule_choice_tag: Dict[str, str]) -> List[Dict[str, object]]:
    tagged_rules: List[Dict[str, object]] = []
    for rid in sorted(program_rules.keys()):
        entry = dict(program_rules[rid])
        entry["choice_tag"] = rule_choice_tag.get(rid, "none")
        tagged_rules.append(entry)
    return tagged_rules


def extract_interpretation_history(symbols: Set[clingo.Symbol]) -> Dict[int, Set[str]]:
    out: Dict[int, Set[str]] = defaultdict(set)
    for atom in symbols:
        if atom.name == "trace_interpretation" and len(atom.arguments) == 2:
            lit = atom_to_str(atom.arguments[0])
            it = arg_to_int(atom.arguments[1])
            out[it].add(lit)
    return out


def extract_truth_values(symbols: Set[clingo.Symbol]) -> Dict[str, Dict[int, Set[str]]]:
    by_name: Dict[str, Dict[int, Set[str]]] = {
        "true": defaultdict(set),
        "und": defaultdict(set),
        "false": defaultdict(set),
    }
    for atom in symbols:
        if atom.name in by_name and len(atom.arguments) == 2:
            lit = atom_to_str(atom.arguments[0])
            it = arg_to_int(atom.arguments[1])
            by_name[atom.name][it].add(lit)
    return by_name


def extract_dual_map(symbols: Set[clingo.Symbol]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for atom in symbols:
        if atom.name == "dual" and len(atom.arguments) == 2:
            out[atom_to_str(atom.arguments[0])] = atom_to_str(atom.arguments[1])
    return out


def conflicts_for_iteration(interpretation: Iterable[str], dual_map: Dict[str, str]) -> List[Tuple[str, str]]:
    lits = set(interpretation)
    seen: Set[Tuple[str, str]] = set()
    out: List[Tuple[str, str]] = []
    for lit in lits:
        dual = dual_map.get(lit)
        if dual is None or dual not in lits:
            continue
        key = tuple(sorted((lit, dual)))
        if key in seen:
            continue
        seen.add(key)
        out.append((lit, dual))
    out.sort()
    return out


def solve_program(ctl: clingo.Control, seminormal: bool, iteration: int) -> Dict[str, object]:
    ctl.ground([("step", [clingo.Number(iteration)])])
    if seminormal:
        ctl.ground([("seminormal_step", [clingo.Number(iteration)])])

    first_model: Optional[Set[clingo.Symbol]] = None
    model_count = 0
    stop = False
    no_model = False

    def on_model(model: clingo.Model) -> None:
        nonlocal first_model, model_count, stop, no_model
        model_count += 1
        if first_model is None:
            first_model = set(model.symbols(atoms=True))
            for atom in first_model:
                if atom.name == "trace_stop" and len(atom.arguments) == 1 and arg_to_int(atom.arguments[0]) == iteration:
                    stop = True
                if atom.name == "trace_no_model" and len(atom.arguments) == 1 and arg_to_int(atom.arguments[0]) == iteration:
                    no_model = True

    ans = ctl.solve(on_model=on_model)
    if ans.unsatisfiable or first_model is None:
        raise RuntimeError(f"No model found at iteration {iteration}.")

    return {
        "symbols": first_model,
        "model_count": model_count,
        "stop": stop,
        "no_model": no_model,
    }


def tabfy(items: Sequence[str]) -> str:
    return "\t".join(items)


def print_xwfm(true: Sequence[str], und: Sequence[str], false: Sequence[str], atoms: Sequence[str]) -> None:
    print(f"atoms considered: {tabfy(atoms)}")
    print(f"true objective literals: {tabfy(true)}")
    print(f"false objective literals: {tabfy(false)}")
    print(f"undefined objective literals: {tabfy(und)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute XWFS model and export a trace for clause generation")
    parser.add_argument("instance", type=str, help="ASP program to solve")
    parser.add_argument("--encoder", type=str, default="encoder.lp", help="Path to the XWFS encoder")
    parser.add_argument("--max-iterations", type=int, default=10, help="Maximum number of alternation iterations")
    parser.add_argument("--trace-json", type=Path, default=None, help="Optional output path for JSON trace")
    args = parser.parse_args()

    ctl = clingo.Control()
    ctl.configuration.solve.models = 1
    ctl.load(args.encoder)
    ctl.load(args.instance)
    ctl.ground()

    cumulative_interpretation: Dict[int, Set[str]] = defaultdict(set)
    iterations_trace: List[Dict[str, object]] = []
    last_symbols: Optional[Set[clingo.Symbol]] = None
    stopped = False

    for iteration in range(1, args.max_iterations + 1):
        seminormal = (iteration % 2) == 1
        print(f"iteration number {iteration}")
        step_result = solve_program(ctl, seminormal, iteration)
        symbols: Set[clingo.Symbol] = step_result["symbols"]  # type: ignore[assignment]
        last_symbols = symbols

        interp_hist = extract_interpretation_history(symbols)
        for it, lits in interp_hist.items():
            cumulative_interpretation[it].update(lits)

        selected, forced_dual, rule_choice_tag = extract_choice_trace(symbols)
        normal_program = add_choice_tags(
            build_rule_map(symbols, "trace_normal_body_pos", "trace_normal_body_neg", iteration),
            rule_choice_tag,
        )
        seminormal_program = add_choice_tags(
            build_rule_map(symbols, "trace_seminormal_body_pos", "trace_seminormal_body_neg", iteration),
            rule_choice_tag,
        ) if seminormal else []

        iteration_interp = sorted(cumulative_interpretation.get(iteration, set()))
        dual_map = extract_dual_map(symbols)
        conflicts = [{"left": a, "right": b} for a, b in conflicts_for_iteration(iteration_interp, dual_map)]

        iterations_trace.append(
            {
                "iteration": iteration,
                "phase": "seminormal" if seminormal else "normal",
                "interpretation": iteration_interp,
                "normal_program": normal_program,
                "seminormal_program": seminormal_program,
                "choices_selected": selected,
                "choices_forced_dual": forced_dual,
                "conflicts": conflicts,
                "stop": bool(step_result["stop"]),
                "no_model": bool(step_result["no_model"]),
                "model_count": int(step_result["model_count"]),
            }
        )

        if step_result["stop"]:
            stopped = True
            break

    if last_symbols is None:
        raise RuntimeError("Solver produced no model.")

    truth_values = extract_truth_values(last_symbols)
    available_ts = set(truth_values["true"].keys()) | set(truth_values["und"].keys()) | set(truth_values["false"].keys())
    latest_tv_t = max(available_ts) if available_ts else None

    true = sorted(truth_values["true"].get(latest_tv_t, set())) if latest_tv_t is not None else []
    und = sorted(truth_values["und"].get(latest_tv_t, set())) if latest_tv_t is not None else []
    false = sorted(truth_values["false"].get(latest_tv_t, set())) if latest_tv_t is not None else []

    atoms = sorted(atom_to_str(atom.arguments[0]) for atom in last_symbols if atom.name == "atom" and len(atom.arguments) == 1)
    print_xwfm(true, und, false, atoms)

    if args.trace_json is not None:
        dual_map = extract_dual_map(last_symbols)
        static_program = add_choice_tags(
            build_rule_map(last_symbols, "resolved_body_pos", "resolved_body_neg", iteration=None),
            extract_choice_trace(last_symbols)[2],
        )
        trace_payload = {
            "instance": args.instance,
            "encoder": args.encoder,
            "max_iterations": args.max_iterations,
            "stopped": stopped,
            "iterations": iterations_trace,
            "interpretation_history": {
                str(it): sorted(lits) for it, lits in sorted(cumulative_interpretation.items(), key=lambda kv: kv[0])
            },
            "resolved_program_static": static_program,
            "dual_map": dual_map,
            "truth_values": {
                key: {str(it): sorted(vals) for it, vals in sorted(by_t.items(), key=lambda kv: kv[0])}
                for key, by_t in truth_values.items()
            },
            "truth_values_iteration": latest_tv_t,
        }
        args.trace_json.write_text(json.dumps(trace_payload, indent=2), encoding="utf-8")
        print(f"wrote trace: {args.trace_json}")


if __name__ == "__main__":
    main()
