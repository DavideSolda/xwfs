import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple
from time import time

import clingo

def arg_to_int(sym: clingo.Symbol) -> int:
    if sym.type != clingo.SymbolType.Number:
        raise ValueError(f"Expected numeric symbol, got: {sym}")
    return int(sym.number)

def atom_to_str(sym: clingo.Symbol) -> str:
    return str(sym)

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

def solve_program(ctl: clingo.Control, seminormal: bool, iteration: int) -> Dict[str, object]:
    ctl.ground([("step", [clingo.Number(iteration)])])
    if seminormal:
        ctl.ground([("seminormal_step", [clingo.Number(iteration)])])

    first_model: Optional[Set[clingo.Symbol]] = None
    model_count = 0
    stop = False
    no_model = False
    no_model_reasons = []

    def on_model(model: clingo.Model) -> None:
        nonlocal first_model, model_count, stop, no_model
        model_count += 1
        if first_model is None:
            first_model = set(model.symbols(atoms=True))

            for atom in first_model:
                if atom.name == "stop" and len(atom.arguments) == 1 and arg_to_int(atom.arguments[0]) == iteration:
                    stop = True
                if atom.name == "no_model" and len(atom.arguments) >= 1 and arg_to_int(atom.arguments[0]) == iteration:
                    no_model = True
                    if no_model:
                      no_model_reasons.append(str(atom.arguments[1]))

    ans = ctl.solve(on_model=on_model)
    #if ans.unsatisfiable or first_model is None:
    #    raise RuntimeError(f"No model found at iteration {iteration}.")

    

    return {
        "symbols": first_model,
        "model_count": model_count,
        "stop": stop,
        "no_model": no_model,
        "no_model_reasons": no_model_reasons,
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

    args = parser.parse_args()

    ctl = clingo.Control() # initialization
    ctl.configuration.solve.models = 1
    t=time()
    ctl.load(args.encoder) # parsing
    ctl.load(args.instance)
    print(f"Parsing took {time()-t}")
    ctl.ground() # solving

    stopped = False

    for iteration in range(1, args.max_iterations + 1):
        seminormal = (iteration % 2) == 1
        print(f"iteration number {iteration}")
        step_result = solve_program(ctl, seminormal, iteration)
        symbols: Set[clingo.Symbol] = step_result["symbols"]  # type: ignore[assignment]
        last_symbols = symbols

        if step_result["stop"]:
            stopped = True
            break

        if last_symbols is None:
            raise RuntimeError("Solver produced no model.")

        print(f"output of iteration {iteration}")
        for a in symbols:
            if "undefined" in str(a) or "und" in str(a) or "stop" in str(a) or "diff" in str(a) or "no_model" in str(a):
                print(f"\t {a}")


        truth_values = extract_truth_values(last_symbols)
        available_ts = set(truth_values["true"].keys()) | set(truth_values["und"].keys()) | set(truth_values["false"].keys())
        latest_tv_t = max(available_ts) if available_ts else None

        true = sorted(truth_values["true"].get(latest_tv_t, set())) if latest_tv_t is not None else []
        und = sorted(truth_values["und"].get(latest_tv_t, set())) if latest_tv_t is not None else []
        false = sorted(truth_values["false"].get(latest_tv_t, set())) if latest_tv_t is not None else []

        no_model = step_result["no_model"]
        if no_model:
           print(f"no model because of {step_result['no_model_reasons']}")

        atoms = sorted(atom_to_str(atom.arguments[0]) for atom in last_symbols if atom.name == "atom" and len(atom.arguments) == 1)
        print_xwfm(true, und, false, atoms)

if __name__ == "__main__":
    main()
