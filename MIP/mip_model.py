import os
import math
from mip import *
import itertools
from time import time
import multiprocessing
import json
from gurobipy import setParam, Env

def save_result(filename, result):
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'w') as file:
            file.write(str(result))

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

def extract_solution_from_path_increment(lst):
    buff = dict()
    for i, val in enumerate(lst):
        if val != 0:
            buff[val] = i + 1
    return list(dict(sorted(buff.items())).values())


def mip_model(num_couriers, num_locations, max_weights, package_weights, distance_matrix, solver=None, timeout=300, queue=None):
    # Validate inputs
    assert num_locations >= num_couriers
    assert len(distance_matrix) == num_locations + 1, "Distance matrix should include the depot"
    assert len(package_weights) == num_locations, "There should be one weight for each location (excluding depot)"
    assert len(max_weights) == num_couriers, "There should be one max weight for each courier"

    package_weights += [0]

    limit = num_locations

    # Create the model
    # print("Creating model")
    # model = Model(solver_name=CBC)
    model = Model(solver_name='GRB')

    """ VARIABLES """
    # print("Creating variables")
    # journeys[c][i][j] = 1 means that courier c go from i to j, with i the row and j the column
    # Basically a NxN matrix for each courrier
    # limit + 1 because of the depot
    journeys = [[[model.add_var(name=f"c:{c}_from:{l1}_to:{l2}", var_type=BINARY) for l2 in range(limit + 1)] for l1 in
          range(limit+1)] for c in
         range(num_couriers)]

    # Weight carried by each courier
    weights = [
        xsum(package_weights[l1] * journeys[c][l1][l2] for l1 in range(limit + 1) for l2 in range(limit + 1))
        for c in range(num_couriers)]

    # Distance travelled by each courrier
    distances = [xsum(
        distance_matrix[l1][l2] * journeys[courier][l1][l2] for l1 in range(limit + 1) for l2 in range(limit + 1))
        for courier in range(num_couriers)]

    """ PATH CORRECTNESS """
    for courier in range(num_couriers):
        # If y[courier][l1][l2] == 1 then y[courier][l3][l1] == 1
        for l1 in range(limit + 1):
            for l2 in range(limit + 1):
                condition = journeys[courier][l1][l2]
                l3_gen_base = (
                    l3 for l3 in range(limit + 1) if
                    (l3 == limit)  # Edge case 1: start from depot
                    or (l1 == limit)  # Edge case 2: end in depot
                    or (l3 != l1 and l3 != l2)
                )
                # There must be 1 in some l3->l1 if we have 1 in l1->l2 because we have to reach l1 in some way
                results = xsum(journeys[courier][l3][l1] for l3 in l3_gen_base)

                # If condition is 1, results must be >=1, but if condition is 0 courrier may have still be in l1 in another moment
                model += results >= condition

    path_increment = [[model.add_var(name=f"path_increment_{courier}_{l}", var_type=INTEGER, lb=0, ub=num_locations)
                       for l in range(limit + 1)]
                      for courier in range(num_couriers)]

    # We fix depot as starting point of the path
    for courier in range(num_couriers):
        path_increment[courier][limit] = 0

    for courier in range(num_couriers):
        for l1 in range(limit + 1):
            # We don't consider depot since it is always the last of the path and we don't need to know it's orederr in the path
            for l2 in range(limit):
                # This means that we want path_increment[courier][l2] == path_increment[courier][l1]+1, if journeys[courier][l1][l2] is 1
                # if journeys[courier][l1][l2] is 1, then path_increment[courier][l2] is at most path_increment[courier][l1] + 1
                model += path_increment[courier][l2] >= path_increment[courier][l1] + 1 - limit * (
                            1 - journeys[courier][l1][l2])
                # if journeys[courier][l1][l2] is 1, then path_increment[courier][l2] is at least path_increment[courier][l1] + 1
                model += path_increment[courier][l2] <= path_increment[courier][l1] + 1 + limit * (
                            1 - journeys[courier][l1][l2])

    # Impose all the path_increment number not touched to be 0
    for courier in range(num_couriers):
        for p in range(limit + 1):
            model += path_increment[courier][p] <= xsum([journeys[courier][p][p2] for p2 in range(limit + 1)]) * (limit + 1)

    """ CONSTRAINT """
    # print("Adding constraints")
    # Add constraints for weight capacity of each courier
    for courier in range(num_couriers):
        model.add_constr(weights[courier] <= max_weights[courier])

    # No travel from place to same place
    for courier in range(num_couriers):
        for l1 in range(limit + 1):
            model += journeys[courier][l1][l1] <= 0
            model += journeys[courier][l1][l1] >= 0

    # Every carried package must be delivered to destination and every courier must start from destination
    for courier in range(num_couriers):
        # Leave depot
        model += xsum(journeys[courier][limit][package] for package in range(limit + 1)) <= 1
        model += xsum(journeys[courier][limit][package] for package in range(limit + 1)) >= 1
        # Back to depot
        model += xsum(journeys[courier][package][limit] for package in range(limit + 1)) <= 1
        model += xsum(journeys[courier][package][limit] for package in range(limit + 1)) >= 1

    # Each package is carried only once
    for package in range(limit):
        model += xsum(journeys[courier][package][l2] for courier in range(num_couriers) for l2 in range(limit + 1)) <= 1
        model += xsum(journeys[courier][package][l2] for courier in range(num_couriers) for l2 in range(limit + 1)) >= 1

    # We impose that if we arrive in l2 than we also have to leave l2
    for courier in range(num_couriers):
        for l1 in range(limit + 1):
            for l2 in range(limit):
                condition = journeys[courier][l1][l2]
                results = xsum(journeys[courier][l2][l3] for l3 in range(limit + 1))

                model += results >= condition

    # Add objective: minimize the maximum distance traveled by any courier
    max_distance = model.add_var(name="max_distance", var_type=INTEGER)
    for courier in range(num_couriers):
        model.add_constr(max_distance >= distances[courier])
    # print("Adding objective")
    model.objective = minimize(max_distance)

    # Optimize the model
    model.verbose = 0
    model.threads = -1
    model.max_seconds = timeout
    try:
        # print("Optimizing")
        start = time()
        model.optimize(max_seconds=timeout, max_seconds_same_incumbent=timeout)
        time_needed = int(time() - start)
        # print("Optimization done")
        # print(f"Time needed for optimization: {time_needed}")
    except Exception as e:
        print("Error in optimization")
        return {
            'time': 0,
            'optimal': False,
            'obj': 'N/A',
            'sol': []
        }
        return res

    # time_needed = int(time() - start)
    if time_needed == 301:
        time_needed = 300

    # Build the solution
    solution = []

    for courier in range(num_couriers):
        tmp_list = []
        for l1 in range(limit + 1):
            try:
                z_value = int(path_increment[courier][l1].x)
            except:
                z_value = 0
            #print(z_value, end=', ')
            tmp_list.append(z_value)
        solution.append(extract_solution_from_path_increment(tmp_list))
        #print()

    if model.objective_value:
        res = {"time": time_needed,
               "optimal": model.status == OptimizationStatus.OPTIMAL,
               "obj": int(model.objective_value),
               "sol": solution}
    else:
        print("No solution found")
        res = {
            'time': 0,
            'optimal': False,
            'obj': 'N/A',
            'sol': []
        }
    # print("Time needed for completing the process: ", time() - start)
    if queue:
        queue.put(res)
    return res


def solve_MIP_with_timeout(m, n, l, s, D, solver_type=None, timeout: int = 360):
    queue = multiprocessing.Queue()
    process = multiprocessing.Process(target=mip_model, args=(m, n, l, s, D, solver_type, timeout, queue))

    process.start()
    process.join(timeout)

    if process.is_alive():
        process.terminate()
        process.join()  # Ensure the process is terminated

    if not queue.empty():
        res = queue.get()
        if not res['optimal']:
            res['time'] = 300
        return res
    else:
        print("Timeout")
        return {
            'time': 0,
            'optimal': False,
            'obj': 'N/A',
            'sol': []
        }



def main():
    # Read the data file
    for filename in os.listdir('instances'):
        if filename.endswith('.dat'):
            instance_id = os.path.splitext(filename)[0]
            instance_path = os.path.join('instances', filename)
            m, n, l, s, D = read_dat_file(instance_path)
            
            print(f"Instance: {instance_id}")
            result = mip_model(m, n, l, s, D)
            # result = solve_MIP_with_timeout(m, n, l, s, D)
            # Print the results
            # print(f"Optimal: {result['optimal']}")
            # print(f"Objective: {result['obj']}")
            # print(f"Time: {result['time']} seconds")
            # print(f"Solution: {result['sol']}")
            # print()
            # print()
            result= json.dumps(result, indent=4)
            save_result(f'results/MIP/{instance_id}_result.json', result)

            

if __name__ == "__main__":
    main()