import itertools
import math

from z3 import BoolRef, Or, Not, And, PbLe, Bool, Solver, Implies, sat, Context
from itertools import combinations
from utils.converter import get_instances
from time import time


def at_least_one(variables: list[BoolRef], context: Context = None):
    """
    Return constraint that at least one of the variables in variables is true
    :param variables: List of variables
    :param context: Context of the variables
    :return:
    """

    if context is None:
        context = variables[0].ctx

    return Or(variables, context)


def at_most_one(variables: list[BoolRef], context: Context = None):
    """
    Return constraint that at most one of the variables in variables is true
    :param variables: List of variables
    :param context: Context of the variables
    :return:
    """

    if context is None:
        context = variables[0].ctx

    return [Not(And(pair[0], pair[1], context)) for pair in combinations(variables, 2)]


def exactly_one(variables: list[BoolRef], context: Context = None):
    """
    Return constraint that exactly one of the variable in variables is true
    :param bool_vars: List of variables
    :param context: Context of the variables
    """

    if context is None:
        context = variables[0].ctx

    return at_most_one(variables, context) + [at_least_one(variables, context)]


def at_most_k_correct(variables: list[BoolRef], k: int):
    """
    Return constraint that at most k of the variables in vars are true
    :param variables: List of variables
    :param k: Maximum number of variables that can be true
    :return:
    """

    return PbLe([(var, 1) for var in variables], k)


def less_than(a: BoolRef, b: BoolRef, context: Context = None):
    """
    Return constraint that a < b
    """

    if context is None:
        context = a.ctx

    return And(a, Not(b), context)


def equal(a: BoolRef, b: BoolRef, context: Context = None):
    """
    Return constraint that a == b
    """

    if context is None:
        context = a.ctx

    return Or(And(a, b, context), And(Not(a), Not(b), context), context)


def lex_less_single(a: list[BoolRef], b: list[BoolRef], context: Context = None) -> bool:
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

    if context is None:
        context = a[0].ctx

    return Or(
        less_than(a[0], b[0], context),
        And(equal(a[0], b[0], context), lex_less_single(a[1:], b[1:], context), context),
        context
    )


def lex_less(a: list[list[BoolRef]], b: list[list[BoolRef]], context: Context = None) -> bool:
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

    if context is None:
        context = a[0][0].ctx

    return Or(
        lex_less_single(a[0], b[0], context),
        And(a[0] == b[0], lex_less(a[1:], b[1:], context), context),
        context
    )


MAXITER = 500


def multiple_couriers(
        m: int,
        n: int,
        D: list[list[int]],
        l: list[int],
        s: list[int],
        model_result: dict,
):
    """
    SAT solver
    :param m: Number of couriers
    :param n: Number of packages
    :param D: Matrix of packages distances
    :param l: List of carriable weight by each courier
    :param s: List of weights of the packages
    :return: Minimized distance, found solution, computation time and iterations number
    """

    # So that the package representing the base doesn't count in the weight calculation
    s += [0]

    ### Ranges ###
    package_range = range(n + 1)
    time_range = range(n + 2)
    time_range_no_zero = range(1, time_range[-1] + 1)
    courier_range = range(m)

    ### Constant ###
    base_package = n
    last_time = time_range[-1]
    variable_coordinates = list(itertools.product(package_range, time_range, courier_range))

    ### Solver ###
    context = Context()
    solver = Solver(ctx=context)

    ### Variables ###
    # # y[courier][time][package] = True if the courier carries the package at time
    y = [[[Bool(f"y_{courier}_{_time}_{package}", ctx=context)
           for package in package_range]
          for _time in time_range]
         for courier in courier_range]

    # # weights[courier][package] = True if the courier carries the package
    weights = [[Bool(f"weights_{courier}_{package}", ctx=context)
                for package in package_range]
               for courier in courier_range]

    # # distance[courier][start][end] = True if the courier goes from start to end at some time in the route
    distances = [[[Bool(f"distances_{courier}_{start}_{end}", ctx=context)
                   # for d in range(D[start][end])]
                   for end in package_range]
                  for start in package_range]
                 for courier in courier_range]

    ### Constraints ###

    # Binding the weights
    for courier in courier_range:
        for _time in time_range:
            for package in package_range:
                solver.add(Implies(y[courier][_time][package], weights[courier][package]))

    # Binding the distances
    for courier in courier_range:
        for _time in time_range_no_zero:
            for p1 in package_range:
                for p2 in package_range:
                    if p1 == p2:
                        continue
                    condition = And(y[courier][_time - 1][p1], y[courier][_time][p2])

                    solver.add(
                        Implies(
                            condition,
                            distances[courier][p1][p2],
                        )
                    )

    # At each time, the courier carries exactly one package or he is at base
    for courier in courier_range:
        for _time in time_range:
            solver.add(exactly_one(y[courier][_time][:]))

    # Each package is carried only once
    for package in package_range:
        if package != base_package:
            solver.add(
                exactly_one([y[courier][_time][package] for courier in courier_range for _time in time_range]))

    # The total weight carried by each courier must be less or equal than his
    # carriable weight
    for courier in courier_range:
        solver.add(at_most_k_correct(
            [weights[courier][package] for package in package_range for _ in range(s[package])],
            l[courier]
        ))

    # At start/end the courier must be at the base
    for courier in courier_range:
        solver.add(y[courier][0][base_package])
        solver.add(y[courier][last_time][base_package])

    ### Optimization ###

    # Couriers must immediately start with a package after the base if they carry a package
    for courier in courier_range:
        for _time in time_range_no_zero:
            a = y[courier][_time][base_package]
            b = y[courier][1][base_package]

            solver.add(Implies(Not(a), Not(b)))

    # Couriers cannot go back to the base before taking other packages
    for courier in courier_range:
        for _time in time_range_no_zero:
            a = y[courier][_time][base_package]

            for _time2 in range(_time + 1, last_time):
                b = y[courier][_time2][base_package]
                solver.add(Implies(a, b))

    ### Breaking Symmetry ###
    # Lexicographic order for each courier
    for c1 in courier_range:
        for c2 in courier_range:
            if c1 < c2 and l[c1] == l[c2]:
                solver.add(lex_less(y[c1], y[c2]))

    ### Objective function ###

    # Getting minimum and maximum distance
    min_distance = math.inf
    for i in range(len(D)):
        for j in range(len(D[i])):
            if D[i][j] <= min_distance and D[i][j] != 0:
                min_distance = D[i][j]

    max_distance = 0
    for i in range(len(D)):
        max_distance += max(D[i])

    start_time = time()
    iterations = 1
    last_best_model = None
    while True:
        k = int((min_distance + max_distance) / 2)

        # Getting the maximum distance
        solver.push()

        for courier in courier_range:
            courier_dist = [
                distances[courier][p1][p2] for p1 in package_range for p2 in package_range for _ in range(D[p1][p2])
            ]

            solver.add(at_most_k_correct(courier_dist, k))

        model_result["ready"] = True

        sol = solver.check()

        if sol != sat:
            min_distance = k
        else:
            # max_distance = k
            last_best_model = solver.model()

            # Build the solution matrix and store the intermediate solution

            last_solution_matrix = [[0 for _ in range(last_time + 1)] for _ in range(len(courier_range))]
            for package, _time, courier in variable_coordinates:
                if last_best_model[y[courier][_time][package]]:
                    last_solution_matrix[courier][_time] = package + 1

            dd = []
            for courier in courier_range:
                s = 0
                for t in time_range_no_zero:
                    p_1 = last_solution_matrix[courier][t - 1] - 1
                    p_2 = last_solution_matrix[courier][t] - 1
                    s += D[p_1][p_2]

                dd += [s]

            max_distance = max(dd)
            #
            # for courier in courier_range]
            # print(last_solution_matrix)


            model_result["sol"] = last_solution_matrix
            model_result["time"] = time() - start_time
            model_result["iterations"] = iterations
            model_result["min_dist"] = max_distance
            model_result["optimal"] = False

        # If one of the stopping conditions is met, return the solution
        if abs(min_distance - max_distance) <= 1 or iterations >= MAXITER:
            model_result["optimal"] = True
            return model_result["min_dist"], model_result["sol"], model_result["time"], model_result["iterations"]
        else:
            iterations += 1
            solver.pop()


def minimizer_binary(instance, solver=multiple_couriers, maxiter=MAXITER, model_result=None):
    if model_result is None:
        model_result = {}

    m = instance["m"]
    n = instance["n"]
    D = instance["D"]
    l = instance["l"]
    s = instance["s"]
    return solver(m, n, D, l, s, model_result=model_result)


def solve_one(instance: dict, instance_index: int, model_result: dict = None) -> dict:
    if model_result is None:
        model_result = {}

    minimizer_binary(instance, model_result=model_result)

    return model_result
