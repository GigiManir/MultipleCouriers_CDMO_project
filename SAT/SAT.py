import math
from z3 import Or, And, Not, Implies, PbLe, Bool, Solver, sat
import itertools
from time import time
import multiprocessing
 
 
# Define the constraint at least one
def at_least_one(variables):
    """
    Return constraint that at least one of the variables in variables is true
    :param variables: List of variables
    :param context: Context of the variables
    :return:
    """
    return Or(variables)
 
 
def at_most_one(variables):
    """
    Return constraint that at most one of the variables in variables is true
    :param variables: List of variables
    :param context: Context of the variables
    :return:
    """
    return [Not(And(pair[0], pair[1])) for pair in itertools.combinations(variables, 2)]
 
 
# Define the constraint exactly one
def exactly_one(variables):
    """
    Return constraint that exactly one of the variable in variables is true
    :param bool_vars: List of variables
    :param context: Context of the variables
    """
 
    return at_most_one(variables) + [at_least_one(variables)]
 
 
def at_most_k(variables, k):
    """
    Return constraint that at most k of the variables in vars are true
    :param variables: List of variables
    :param k: Maximum number of variables that can be true
    :return:
    """
 
    return PbLe([(var, 1) for var in variables], k)
 
 
def less_than(a, b):
    """
    Return constraint that a < b
    """
 
    return And(a, Not(b))
 
 
def equal(a, b):
    """
    Return constraint that a == b
    """
 
    return Or(And(a, b), And(Not(a), Not(b)))
 
 
def lex_less_single(a, b) -> bool:
    """
    Return constraint that a < b in lexicographic order:
    a := a_1, ..., a_n
    b := b_1, ..., b_n
    a_1 < b_1 or (a_1 == b_1 and lex_less_single(a_2...a_n, b_2...b_n))
    :param a: list of bools
    :param b: list of bools
    :param context: Context of the variables
    :return:
    """
    if not a or not b:
        return True
 
    return Or(less_than(a[0], b[0]),
              And(equal(a[0], b[0]),
                  lex_less_single(a[1:], b[1:])))
 
 
# Define the lex less constraint for symmetry breaking
def lex_less(a, b) -> bool:
    """
    Return constraint that a < b in lexicographic order:
    :param a: List of lists of bools where each sublist is the encoding of a number
    :param b: List of lists of bools where each sublist is the encoding of a number
    :param context: Context of the variables
    :return:
    """
 
    if not a:
        return True
    if not b:
        return False
 
    return Or(lex_less_single(a[0], b[0]),
              And(a[0] == b[0],
                  lex_less(a[1:], b[1:])))
 
 
# Define the problem
def solve_instance_sat(
        result,
        m,
        n,
        l,
        s,
        D,
        solver_type=None,
        timeout: int = 300, ):
    model_result = {
        'time': 0,
        'optimal': False,
        'obj': 0,
        'sol': []
    }
 
    # So that the package representing the base doesn't count in the weight calculation
    s += [0]
 
    ## RANGES ##
    package_range = range(n + 1)
    time_range = range(math.ceil((1.5*n/m)+2))
    time_range_no_zero = range(1, time_range[-1] + 1)
    courier_range = range(m)
 
    ## CONSTANTS ##
    base_package = n
    last_time = time_range[-1]
    variable_coordinates = list(itertools.product(package_range, time_range, courier_range))
 
    ## SOLVER ##
    solver = Solver()
 
 
    ### VARIABLES ###
 
    # journeys[cou][ti][pac] = True if the courier carries the package at time ti
    journeys = [[[Bool(f'journeys_{cou}_{ti}_{pac}')
           for pac in package_range]
          for ti in time_range]
         for cou in courier_range]
 
    # weights[cou][pac] = True if the courier carries the package
    weights = [[Bool(f'weights_{cou}_{pac}')
                for pac in package_range]
               for cou in courier_range]
 
    # distances[cou][start][end] = True if the courier goes from start to end at some time in the route
    distances = [[[Bool(f'distances_{cou}_{start}_{end}')
                   for end in package_range]
                  for start in package_range]
                 for cou in courier_range]
 
 
    ## CONSTRAINTS ##
 
    # Constraint the weights variable to be true if the courier carries the package
    for cou in courier_range:
        for ti in time_range:
            for pac in package_range:
                solver.add(Implies(journeys[cou][ti][pac], weights[cou][pac]))
 
    # Constraint the distances variable
    for cou in courier_range:
        for ti in time_range_no_zero:
            for pac1 in package_range:
                for pac2 in package_range:
                    if pac1 == pac2:
                        continue
                    condition = And(journeys[cou][ti - 1][pac1], journeys[cou][ti][pac2])
                    solver.add(Implies(condition, distances[cou][pac1][pac2]))
 
    # At each time, the courier can only carry exactly one package or it is at base
    for cou in courier_range:
        for ti in time_range:
            solver.add(exactly_one(journeys[cou][ti][:]))
 
    # Each package is carried only once
    for pac in package_range:
        if pac != base_package:
            solver.add(exactly_one([journeys[cou][ti][pac] for cou in courier_range for ti in time_range]))
 
    # The total weight carried by each courier must be less or equal than its maximum capacity
    for cou in courier_range:
        solver.add(at_most_k([weights[cou][pac] for pac in package_range for _ in range(s[pac])], l[cou]))
 
    # The courier must be at the base at start and end
    for cou in courier_range:
        solver.add(journeys[cou][0][base_package])
        solver.add(journeys[cou][last_time][base_package])
 
 
    ## OPTIMIZATION CONSTRAINTS ##
        
    # Couriers cannot go back to the base before delivering all the other packages
    for cou in courier_range:
        for ti in time_range_no_zero:
            a = journeys[cou][ti][base_package]
 
            for ti2 in range(ti + 1, last_time):
                b = journeys[cou][ti2][base_package]
                solver.add(Implies(a, b))
 
    # Couriers must stay at the base once they return
    for cou in courier_range:
        for ti in time_range_no_zero:
            solver.add(Implies(journeys[cou][ti][base_package],
                           And([journeys[cou][_t][base_package] for _t in range(ti, last_time + 1)])))
 
    ## SYMMETRY BREAKING CONSTRAINTS ##
 
    # If two couriers have the same capacity then they are symmetric,
    # to break the symmetry we impose an order (for the package they pick up) betweem them.
    for cou1 in courier_range:
        for cou2 in courier_range:
            if cou1 < cou2 and l[cou1] == l[cou2]:
                solver.add(lex_less(journeys[cou1], journeys[cou2]))
 
 
    ## OBJECTIVE FUNCTION ##
 
    # Inizializzation
    start_time = time()
    last_best_model = None
 
    min_distance = math.inf
    max_distance = 0
 
    # Initialize min and max distances using a better heuristic
    for i in range(len(D)):
        for j in range(len(D[i])):
            if D[i][j] != 0:
                min_distance = min(min_distance, D[i][j])
 
    for i in range(len(D)):
        max_distance += sum(D[i])
 
    while True:
        k = int((min_distance + max_distance) / 2)
        
        solver.push()
        
        for cou in courier_range:
            courier_dist = [distances[cou][pac1][pac2] for pac1 in package_range for pac2 in package_range
                            for _ in range(D[pac1][pac2])]
            solver.add(at_most_k(courier_dist, k))
        
        sol = solver.check()
 
        if sol != sat:
            min_distance = k
        else:
            last_best_model = solver.model()
 
            last_solution_matrix = [[0 for _ in range(last_time + 1)] for _ in range(len(courier_range))]
            for pac, ti, cou in variable_coordinates:
                if last_best_model[journeys[cou][ti][pac]]:
                    last_solution_matrix[cou][ti] = pac + 1
 
            distd = []
            for cou in courier_range:
                s = 0
                for ti in time_range_no_zero:
                    pac1 = last_solution_matrix[cou][ti - 1] - 1
                    pac2 = last_solution_matrix[cou][ti] - 1
                    s += D[pac1][pac2]
                distd += [s]
 
            max_distance = max(distd)
 
            for i in range(len(last_solution_matrix)):
                last_solution_matrix[i] = [num for num in last_solution_matrix[i] if num != base_package + 1]
 
            model_result['time'] = int(time() - start_time)
            model_result['optimal'] = False
            model_result['obj'] = max_distance
            model_result['sol'] = last_solution_matrix
            result.append(model_result)
 
        if (time() - start_time) >= timeout:
            print('TIME OUT OF RANGE')
            return model_result
        
        if abs(min_distance - max_distance) <= 1:
            model_result['optimal'] = True
            result.append(model_result)
            return model_result
        else:
            # If we find a solution, we might adjust the search space more aggressively
            if sol == sat:
                # If a solution was found, we can try narrowing the search space more aggressively
                max_distance = k - 1  # Try a smaller max_distance for the next
            else:
                # If no solution was found, we try a larger k
                min_distance = k + 1
        
        solver.pop()    
 
def solve_SAT_with_timeout(m, n, l, s, D, solver_type=None,
                           timeout: int = 300):
    manager = multiprocessing.Manager()
    result = manager.list()
    process = multiprocessing.Process(target=solve_instance_sat, args=(result, m, n, l, s, D, solver_type))
 
    process.start()
    process.join(timeout)
 
    if process.is_alive():
        process.terminate()
        process.join()  # Ensure the process is terminated
 
    if result:
        res = result[-1]
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
 
 
def read_dat_file(file_path):
    with open(file_path, 'r') as file:
        # Read the first two integers
        m = int(file.readline().strip())
        n = int(file.readline().strip())
 
        # Read the next line as a list of integers
        l = list(map(int, file.readline().strip().split()))
 
        # Read the next line as a list of integers
        s = list(map(int, file.readline().strip().split()))
 
        # Read the remaining lines into the distance matrix D
        D = []
        for line in file:
            D.append(list(map(int, line.strip().split())))
 
    return m, n, l, s, D
 
def main():
    solver = 'Default'
 
    results = []
 
    # Loop through all instances from inst01.dat to inst10.dat
    for i in range(1, 2):
        # Generate file path dynamically
        file_name = f'instances/inst{i:02d}.dat'
 
        try:
            # Read the instance file
            instance = read_dat_file(file_name)
            m, n, l, s, d = instance
 
            # Solve the problem using the solve_SAT_with_timeout function
            print(f"Solving instance {file_name}...")
            res = solve_SAT_with_timeout(m, n, l, s, d)
 
            # Store the result for the current instance
            results.append({
                'instance': file_name,
                'result': res
            })
            print(f"Result for {file_name}: {res}")
 
        except FileNotFoundError:
            print(f"File {file_name} not found. Skipping this instance.")
        except Exception as e:
            print(f"An error occurred while processing {file_name}: {e}")
 
if __name__ == "__main__":
    main()