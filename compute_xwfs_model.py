import clingo
import argparse
from pathlib import Path
from collections import defaultdict, namedtuple


def solve_program(ctl, seminormal, iteration):

    ctl.ground([("step", [clingo.Number(iteration)])])

    if seminormal: ctl.ground([("seminormal_step", [clingo.Number(iteration)])])

    collected_atoms = set()

    und   = set()
    true  = set()
    false = set()

    stop = False

    def on_model(model):

        nonlocal stop

        s = set()

        for atom in model.symbols(atoms=True):
            if atom.name in set(["reduct_body", "holds_body", "interpretation", "delete"]):
                print(atom)
            s.add(atom)

        for atom in s:

            if atom.name == "atom":
                collected_atoms.add(atom.arguments[0])

            if atom.name == "und":
                und.add(atom.arguments[0])
            if atom.name == "true":
                true.add(atom.arguments[0])
            if atom.name == "false":
                false.add(atom.arguments[0])

            if atom.name == "stop":
                stop = True

    ans = ctl.solve(on_model=on_model)

    if ans.unsatisfiable:
        print("UNSATISFIABLE")

    return stop, true, und, false, collected_atoms


def tabfy(x):
    return "\t".join([str(y) for y in x])


def compute_xwfm(true, und, false, atoms):

    print(f"atoms considered: {tabfy(atoms)}")

    print(f"true objective literals: {tabfy(true)}")

    print(f"false objective literals: {tabfy(false)}")

    print(f"undefined objective literals: {tabfy(und)}")

    return None

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Compute XWFS model")
    parser.add_argument("instance", type=str, help="ASP program to solve")
    args = parser.parse_args()

    ctl = clingo.Control()
    ctl.load("encoder.lp")
    ctl.load(args.instance)

    ctl.ground()

    for iter in range(1, 100):
        print(f"iteration number {iter}")
        stop, true, und, false, collected_atoms = solve_program(ctl, (iter % 2) == 1, iter)
        if stop:
             break

    compute_xwfm(true, und, false, collected_atoms)
