# -*- coding: utf-8 -*-
"""SMT.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1Bc44Ujuez3-c9Lpe88sDx6jUTuibPEYS
"""

# !pip install z3-solver

from z3 import *
from time import time as timer
import multiprocessing
import math

MAX_ITERATIONS = 50

# Return the maximum value from a list of Z3 expressions.
def get_max_value(values) -> int:
    max_value = values[0]
    for v in values[1:]:
        max_value = If(v > max_value, v, max_value)
    return max_value

# Compares two vectors lexicographically. Returns True if 'first' is lexicographically less than 'second'.
def lexicographically_less(first_vec, second_vec) -> bool:
    if not first_vec or not second_vec:
        return True
    return Or(first_vec[0] <= second_vec[0], And(first_vec[0] == second_vec[0], lexicographically_less(first_vec[1:], second_vec[1:])))

# Lexicographically compare two matrices row by row.
def compare_matrices_lex(first_matrix, second_matrix) -> bool:
    if not first_matrix:
        return True
    if not second_matrix:
        return False
    return Or(lexicographically_less(first_matrix[0], second_matrix[0]),
              And(first_matrix[0] == second_matrix[0], compare_matrices_lex(first_matrix[1:], second_matrix[1:])))


def optimize_courier_routes(output, num_couriers, num_packages, distances, weight_limits, package_weights):
    result_data = {
        'time': 0,
        'optimal': False,
        'obj': 0,
        'sol': []
        }

    package_weights += [0]  # Add dummy package with zero weight

    package_indices = range(num_packages + 1)
    time_slots = range((math.ceil(1.5 * num_packages/num_couriers)+ 2))
    non_zero_time_slots = range(1, time_slots[-1] + 1)

    courier_indices = range(num_couriers)
    final_package = num_packages
    final_time_slot = time_slots[-1]

    solver = Then('simplify', 'elim-term-ite', 'solve-eqs', 'smt').solver()

    # Create variables for the solution matrix
    journeys = [[[Int(f"assign_{pkg}_{t}_{courier}") for courier in courier_indices] for t in time_slots] for pkg in package_indices]

    # Add constraints to ensure valid assignments
    for pkg in package_indices:
        for courier in courier_indices:
            for t in time_slots:
                solver.add(journeys[pkg][t][courier] <= 1)
                solver.add(journeys[pkg][t][courier] >= 0)

    # Calculate total weight carried by each courier
    courier_weights = [Sum([package_weights[pkg] * journeys[pkg][t][courier] for t in time_slots for pkg in package_indices]) for courier in courier_indices]

    # Calculate distances traveled by each courier
    travel_distances = []
    for courier in courier_indices:
        courier_dists = []
        for t in non_zero_time_slots:
            for p1 in package_indices:
                for p2 in package_indices:
                    pickup = journeys[p1][t - 1][courier] == 1
                    dropoff = journeys[p2][t][courier] == 1
                    courier_dists.append(distances[p1][p2] * And(pickup, dropoff))
        travel_distances.append(Sum(courier_dists))

    # Ensure each package (except the final package) is picked up exactly once
    for pkg in package_indices:
        if pkg == final_package:
            continue
        solver.add(Sum([journeys[pkg][t][courier] for t in time_slots for courier in courier_indices]) == 1)

    # Ensure valid time slots and couriers are assigned to packages
    for courier in courier_indices:
        for t in time_slots:
            solver.add(Sum([journeys[pkg][t][courier] for pkg in package_indices]) == 1)
        solver.add(Sum([journeys[pkg][t][courier] for pkg in package_indices if pkg != final_package for t in time_slots]) >= 1)

    # Ensure the final package is the first and last in the route for each courier
    for courier in courier_indices:
        solver.add(journeys[final_package][0][courier] == 1)
        solver.add(journeys[final_package][final_time_slot][courier] == 1)

    # Enforce weight constraints
    for courier in courier_indices:
        solver.add(courier_weights[courier] <= weight_limits[courier])

    # Additional constraints for base package handling
    # for courier in courier_indices:
    #     solver.add(journeys[final_package][1][courier] != 1)

    # Each courier can return to the base only after delivering all the packages they are carrying
    for courier in courier_indices:
        for t in non_zero_time_slots:
            current_pickup = journeys[final_package][t][courier]
            for t2 in range(t + 1, final_time_slot):
                future_pickup = journeys[final_package][t2][courier]
                solver.add(Implies(current_pickup == 1, future_pickup == 1))

    # Symmetry breaking by lexicographical comparison
    for c1 in courier_indices:
        for c2 in courier_indices:
            if c1 < c2 and weight_limits[c1] == weight_limits[c2]:
                solver.add(compare_matrices_lex(journeys[c1], journeys[c2]))

    # Objective: minimize the maximum distance any courier has to travel
    max_travel_distance = get_max_value(travel_distances)
    min_possible_distance = min(distances[i][j] for i in range(len(distances)) for j in range(len(distances[i])) if distances[i][j] != 0)
    max_possible_distance = sum(max(distances[i]) for i in range(len(distances)))
    max_possible_distance = math.ceil(max_possible_distance)
    min_possible_distance = max(min_possible_distance, math.floor(min_possible_distance))

    start_time = timer()
    iteration_count = 1
    last_best_solution = None

    while True:
        current_guess = int((min_possible_distance + max_possible_distance) / 2)
        solver.push()
        solver.add(max_travel_distance <= current_guess)
        solution_found = solver.check()

        if solution_found != sat:
            min_possible_distance = current_guess
        else:
            last_best_solution = solver.model()
            max_possible_distance = last_best_solution.eval(max_travel_distance).as_long()

            solution_matrix = [[0 for _ in range(final_time_slot + 1)] for _ in range(len(courier_indices))]
            for courier in courier_indices:
                for t in time_slots:
                    value = sum(pkg * last_best_solution.eval(journeys[pkg][t][courier]) for pkg in package_indices)
                    solution_matrix[courier][t] = last_best_solution.eval(value + 1).as_long()

            result_data["sol"] = solution_matrix
            result_data["time"] = int(timer() - start_time)
            result_data["obj"] = max_possible_distance
            result_data["optimal"] = False
            for i in range(len(result_data['sol'])):
                result_data['sol'][i] = [num for num in result_data['sol'][i] if num != num_packages + 1]
            output.append(result_data)

        if abs(min_possible_distance - max_possible_distance) <= 1 or iteration_count >= MAX_ITERATIONS:
            result_data["optimal"] = True
            output.append(result_data)
            return
        else:
            iteration_count += 1
            solver.pop()

# Function to solve a courier optimization problem using Z3 SMT solver
def solve_courier_problem(m, n, limits, sizes, dist_matrix, solver=None, timeout=300):
    solution_data = {}
    optimize_courier_routes(m, n, dist_matrix, limits, sizes, solution_data=solution_data, timeout=timeout)
    for i in range(len(solution_data['sol'])):
        solution_data['sol'][i] = [num for num in solution_data['sol'][i] if num != n + 1]
    solution_data['time'] = int(solution_data['time'])
    return solution_data

# Solve the problem with a timeout
def solve_SMT_with_timeout(m, n, limits, sizes, dist_matrix, solver_type=None, timeout: int = 300):
    manager = multiprocessing.Manager()
    results = manager.list()
    process = multiprocessing.Process(target=optimize_courier_routes, args=(results, m, n, dist_matrix, limits, sizes))

    process.start()
    process.join(timeout)

    if process.is_alive():
        process.terminate()
        process.join()  # Ensure process termination

    if results:
        res = results[-1]
        if not res['optimal']:
            res['time'] = 300
        return res
    else:
        return {
            'time': 0,
            'optimal': False,
            'obj': 'N/A',
            'sol': []
        }



def read_instance_from_file(filename):
    with open(filename, 'r') as file:
        lines = file.readlines()

    # Leggi m e n
    m = int(lines[0].strip())
    n = int(lines[1].strip())

    # Leggi le capacità dei corrieri
    l = list(map(int, lines[2].strip().split()))

    # Leggi i pesi dei pacchetti
    s = list(map(int, lines[3].strip().split()))

    # Leggi la matrice delle distanze
    D = []
    for i in range(4, 4 + (n + 1)):
        D.append(list(map(int, lines[i].strip().split())))

    return m, n, l, s, D

if __name__ == '__main__':
      filename = f'inst07.dat'
      m, n, l, s, D = read_instance_from_file(filename)
      result = solve_SMT_with_timeout(m, n, l, s, D)
      print("Tempo di esecuzione:", result['time'])
      print("Obiettivo:", result['obj'])
      print("Ottimale:", result['optimal'])
      print("Soluzione:")
      for sol in result['sol']:
          print(sol)

if __name__ == '__main__':
    for i in range(1, 22):
      print('#### INSTANCE', i)
      if i < 10:
        filename = f'inst0{i}.dat'
      else:
        filename = f'inst{i}.dat'

      # Leggi l'istanza dal file
      m, n, l, s, D = read_instance_from_file(filename)

      # Risolvi l'istanza usando il solver SMT
      result = solve_SMT_with_timeout(m, n, l, s, D)

      # Stampa i risultati
      print("Tempo di esecuzione:", result['time'])
      print("Obiettivo:", result['obj'])
      print("Ottimale:", result['optimal'])
      print("Soluzione:")
      for sol in result['sol']:
          print(sol)

# Instance [7, 11...21] N\A