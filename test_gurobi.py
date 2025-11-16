import pyomo.environ as pyo
import subprocess
import sys

# Create a simple test model
model = pyo.ConcreteModel()
model.x = pyo.Var(bounds=(0, 10))
model.y = pyo.Var(bounds=(0, 10))
model.obj = pyo.Objective(expr=model.x + model.y, sense=pyo.maximize)
model.con = pyo.Constraint(expr=model.x + 2*model.y <= 15)

# Try solving with Gurobi
try:
    # Write model to LP file
    model.write('test_model.lp')

    # Call gurobi_cl directly
    result = subprocess.run(
        ['gurobi_cl', 'test_model.lp'],
        capture_output=True,
        text=True
    )

    print("=== Gurobi CLI Output ===")
    print(result.stdout)

    # Check for version in output
    for line in result.stdout.split('\n'):
        if 'Gurobi' in line and 'version' in line.lower():
            print(f"\n✅ {line.strip()}")

except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
