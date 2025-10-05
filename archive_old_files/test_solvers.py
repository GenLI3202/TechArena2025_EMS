"""Quick solver availability test."""
import pyomo.environ as pyo

def test_solver_availability():
    solvers_to_test = ['cplex', 'gurobi', 'cbc', 'glpk', 'appsi_highs', 'scip', 'highs']
    available = []

    print("\n=== Solver Availability Test ===\n")

    for solver_name in solvers_to_test:
        try:
            solver = pyo.SolverFactory(solver_name)
            if solver.available():
                print(f"[OK] {solver_name.upper()}: Available")
                available.append(solver_name)
            else:
                print(f"[NO] {solver_name.upper()}: Not available")
        except Exception as e:
            print(f"[NO] {solver_name.upper()}: Error - {str(e)[:50]}")

    print(f"\nAvailable solvers: {available}")
    print(f"\nRecommended solver for this project: {'appsi_highs' if 'appsi_highs' in available else available[0] if available else 'None'}")
    return available

if __name__ == "__main__":
    test_solver_availability()
