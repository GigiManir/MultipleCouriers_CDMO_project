Satisfiability (SAT) with Python using z3
Install z3:

sh
Copia codice
pip install z3-solver
Create and Solve a SAT Model:
Let's create a simple SAT problem where we need to find a satisfying assignment for a given Boolean formula.

python
Copia codice
from z3 import Solver, Bool, Or, Not, sat

# Create a solver instance
solver = Solver()

# Create Boolean variables
A = Bool('A')
B = Bool('B')

# Add clauses (example: (A or B) and (not A or B))
solver.add(Or(A, B))
solver.add(Or(Not(A), B))

# Check if the problem is satisfiable
if solver.check() == sat:
    print("SATISFIABLE")
    model = solver.model()
    print(f"A: {model[A]}")
    print(f"B: {model[B]}")
else:
    print("UNSATISFIABLE")