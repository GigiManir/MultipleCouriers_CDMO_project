import os
import math
from z3 import Or, And, Not, Implies, PbLe, Bool, Solver, sat
import itertools
from time import time
import multiprocessing


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


def run_model_and_solver(instance_id, instance_data, approach, solver):
    instances_dir = 'instances'
    for instance_file in os.listdir(instances_dir):
        if instance_file.endswith('.dat'):  # Assuming instances are in .txt files
            instance_id = os.path.splitext(instance_file)[0]
            instance_path = os.path.join(instances_dir, instance_file)
            instance_data = read_dat_file(instance_path)

            m, n, l, s, d = instance_data
    
    # if approach == "CSP" or approach == 'CSP_wout_SB':
    #     instance_file = f"instances/{instance_id}"
    #     sol = solve_instance_csp(instance_file, solver)
    # if approach == "SAT":
    sol = solve_SAT_with_timeout(m, n, l, s, d, solver)
    # if approach == "SMT":
        # sol = solve_SMT_with_timeout(m, n, l, s, d, solver)
    # if approach == "MIP":
        # sol = solve_MIP_with_timeout(m, n, l.copy(), s.copy(), d, solver)
    return sol



## SAT model Gio Tancredi Francesco

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


# Define the constraint at most one with sequential encoding
def at_most_one_seq(bool_vars):
    constraints = []
    n = len(bool_vars)
    s = [Bool(f's_m_{i}') for i in range(n - 1)]
    constraints.append(Or(Not(bool_vars[0]), s[0]))
    constraints.append(Or(Not(bool_vars[-1]), Not(s[-1])))
    for i in range(1, n - 1):
        constraints.append(Or(Not(bool_vars[i]), s[i]))
        constraints.append(Or(Not(s[i - 1]), s[i]))
        constraints.append(Or(Not(bool_vars[i]), Not(s[i - 1])))
    return And(constraints)


# Define the constraint exactly one
def exactly_one(variables):
    """
    Return constraint that exactly one of the variable in variables is true
    :param bool_vars: List of variables
    :param context: Context of the variables
    """

    return at_most_one(variables) + [at_least_one(variables)]

# Define the constraint exactly one with sequential encoding
def exactly_one_seq(variables):
    """
    Return constraint that exactly one of the variable in variables is true with sequential encoding.
    :param bool_vars: List of variables
    :param context: Context of the variables
    """

    return And(at_most_one_seq(variables), at_least_one(variables))


# Define the constraint at most k with sequential encoding
def at_most_k_seq(variables, k):
    """
    Return constraint that at most k of the variables in variables are true using sequential encoding.
    :param variables: List of variables
    :param k: Maximum number of variables that can be true
    :param context: Context of the variables
    :return: Conjunction of constraints
    """

    constraints = []
    n = len(variables)

    if k <= 0:
        return And([Not(v) for v in variables])  # All variables must be false
    if n <= k:
        return True  # The constraint is trivially satisfied if the number of variables is less than or equal to k

    # Auxiliary variables
    s = [[Bool(f's_{i}_{j}') for j in range(k)] for i in range(n)]

    # Encoding the constraints
    constraints.append(Or(Not(variables[0]), s[0][0]))
    for j in range(1, k):
        constraints.append(Not(s[0][j]))

    for i in range(1, n):
        constraints.append(Or(Not(variables[i]), s[i][0]))
        constraints.append(Or(Not(s[i - 1][0]), s[i][0]))
        constraints.append(Or(Not(variables[i]), Not(s[i - 1][0])))

        for j in range(1, k):
            constraints.append(Or(Not(variables[i]), Not(s[i - 1][j - 1]), s[i][j]))
            constraints.append(Or(Not(s[i - 1][j]), s[i][j]))

        constraints.append(Not(s[i - 1][k - 1]))

    return And(constraints)


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
    time_range = range(n - m + 3)
    time_range_no_zero = range(1, time_range[-1] + 1)
    courier_range = range(m)

    ## CONSTANTS ##
    base_package = n
    last_time = time_range[-1]
    variable_coordinates = list(itertools.product(package_range, time_range, courier_range))

    ## SOLVER ##
    solver = Solver()


    ### VARIABLES ###

    # y[cou][ti][pac] = True if the courier carries the package at time ti
    y = [[[Bool(f'y_{cou}_{ti}_{pac}')
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
                solver.add(Implies(y[cou][ti][pac], weights[cou][pac]))

    # Constraint the distances variable
    for cou in courier_range:
        for ti in time_range_no_zero:
            for pac1 in package_range:
                for pac2 in package_range:
                    if pac1 == pac2:
                        continue
                    condition = And(y[cou][ti - 1][pac1], y[cou][ti][pac2])
                    solver.add(Implies(condition, distances[cou][pac1][pac2]))

    # At each time, the courier can only carry exactly one package or it is at base
    for cou in courier_range:
        for ti in time_range:
            solver.add(exactly_one(y[cou][ti][:]))

    # Each package is carried only once
    for pac in package_range:
        if pac != base_package:
            solver.add(exactly_one([y[cou][ti][pac] for cou in courier_range for ti in time_range]))

    # The total weight carried by each courier must be less or equal than its maximum capacity
    for cou in courier_range:
        solver.add(at_most_k([weights[cou][pac] for pac in package_range for _ in range(s[pac])], l[cou]))

    # The courier must be at the base at start and end
    for cou in courier_range:
        solver.add(y[cou][0][base_package])
        solver.add(y[cou][last_time][base_package])


    ## OPTIMIZATION CONSTRAINTS ##

    # Couriers must immediately start with a package after the base if they carry a package
    for cou in courier_range:
        for ti in time_range_no_zero:
            a = y[cou][ti][base_package]
            b = y[cou][1][base_package]

            solver.add(Implies(Not(a), Not(b)))

    # Couriers cannot go back to the base before delivering all the other packages
    for cou in courier_range:
        for ti in time_range_no_zero:
            a = y[cou][ti][base_package]

            for ti2 in range(ti + 1, last_time):
                b = y[cou][ti2][base_package]
                solver.add(Implies(a, b))

    # Couriers have to bring at least one package
    for cou in courier_range:
        solver.add(at_least_one([y[cou][ti][pac] for ti in time_range_no_zero for pac in range(n)]))


    ## SYMMETRY BREAKING CONSTRAINTS ##

    # If two couriers have the same capacity then they are symmetric,
    # to break the symmetry we impose an order (for the package they pick up) betweem them.
    for cou1 in courier_range:
        for cou2 in courier_range:
            if cou1 < cou2 and l[cou1] == l[cou2]:
                solver.add(lex_less(y[cou1], y[cou2]))



    ''' OTHER SYMMETRY BREAKING CONSTRAINTS THAT PRODUCE BAD PERFORMANCE
    # Two couriers path are exchangeable if the maximum weight of the two is 
    # less than the minimum loading capacity
    # in that case we impose an ordering between them
    for cou1 in courier_range:
        for cou2 in courier_range:
            minload = min(l[cou1], l[cou2])
            if (at_most_k([weights[cou1][pac] for pac in package_range for _ in range(s[pac])], minload) and
                at_most_k([weights[cou2][pac] for pac in package_range for _ in range(s[pac])], minload)) and cou1 < cou2:
                solver.add(lex_less(y[cou1], y[cou2]))'''
    
    '''
    # se due viaggi di due corrieri sono della stessa lunghezza e i due corrieri hanno la possibilità di portare tutti e due
    # i pacchi, allora c'è simmetria
    for cou1 in courier_range:
        for cou2 in courier_range:
            w1 = sum(weights[cou1] * s)
            w2 = sum(weights[cou2] * s)
            condition_distances = True  # non riuscito ad implementarla
            if cou1 < cou2 and (max(w1, w2) <= min(l[cou1], l[cou2])) and condition_distances:
                solver.add(lex_less(y[cou1], y[cou2]))
    '''

    ## OBJECTIVE FUNCTION ##

    # Get the minimum and maximum distance
    min_distance = math.inf
    for i in range(len(D)):
        for j in range(len(D[i])):
            if D[i][j] <= min_distance and D[i][j] != 0:
                min_distance = D[i][j]

    max_distance = 0
    for i in range(len(D)):
        max_distance += max(D[i])

    start_time = time()
    iteration = 1
    last_best_model = None
    while True:
        k = int((min_distance + max_distance) / 2)

        # Get the maximum distance
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

            # Build the solution matrix and store the intermediate solution
            last_solution_matrix = [[0 for _ in range(last_time + 1)] for _ in range(len(courier_range))]
            for pac, ti, cou, in variable_coordinates:
                if last_best_model[y[cou][ti][pac]]:
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
            iteration += 1

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


## End of SAT model Gio Tancredi Francesco


def main():
    solver= 'Default'
    res=run_model_and_solver(None, None, None, solver)
    results = []
    results.append(res)
    print(results)

if __name__ == "__main__":
    main()