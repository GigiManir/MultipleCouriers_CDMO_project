import os
import math
from progetto_gio_tancre_fra.CDMO_D.SMT.SMT_model import solve_SMT_with_timeout
from z3 import Or, And, Not, Implies, PbLe, Bool, Solver, sat
import itertools
from time import time
import multiprocessing
from progetto_gio_tancre_fra.CDMO_D.SAT.SAT_model import solve_SAT_with_timeout


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
        # sol = solve_SAT_with_timeout(m, n, l, s, d, solver)
    # if approach == "SMT":
    sol = solve_SMT_with_timeout(m, n, l, s, d, solver)
    # if approach == "MIP":
        # sol = solve_MIP_with_timeout(m, n, l.copy(), s.copy(), d, solver)
    return sol


def main():
    solver= 'Default'
    res=run_model_and_solver(None, None, None, solver)
    results = []
    results.append(res)
    print(results)

if __name__ == "__main__":
    main()