Mixed-Integer Programming (MIP) with Python using mip
Install mip:

sh
Copia codice
pip install mip
Create and Solve a MIP Model:
Let's solve the assignment problem using mip.

python
Copia codice
from mip import Model, xsum, BINARY, MINIMIZE

# Number of tasks and workers
n = 3

# Cost matrix
cost = [
    [9, 2, 7],
    [6, 4, 3],
    [5, 8, 1]
]

# Create a model
model = Model(sense=MINIMIZE, solver_name='CBC')

# Decision variables
assignment = [[model.add_var(var_type=BINARY) for j in range(n)] for i in range(n)]

# Objective function
model.objective = xsum(cost[i][j] * assignment[i][j] for i in range(n) for j in range(n))

# Constraints
for i in range(n):
    model += xsum(assignment[i][j] for j in range(n)) == 1  # Each task is assigned to exactly one worker
for j in range(n):
    model += xsum(assignment[i][j] for i in range(n)) == 1  # Each worker is assigned exactly one task

# Optimize
model.optimize()

# Print the results
if model.num_solutions:
    print("Total Cost:", model.objective_value)
    for i in range(n):
        for j in range(n):
            if assignment[i][j].x >= 0.99:  # Binary variables might be slightly off due to floating-point precision
                print(f"Task {i+1} is assigned to Worker {j+1}")