import os
import argparse
from MIP.mip_model import solve_MIP_with_timeout
from SAT.SAT import solve_SAT_with_timeout
from SMT.smt import solve_SMT_with_timeout
from CSP.run_csp import solve_instance_csp
import json

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

def save_result(filename, result):
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'w') as file:
            file.write(str(result))

def run_from_script(approach, solver):
    instances_folder = 'instances'
    for filename in os.listdir(instances_folder).sort():
        if filename.endswith('.dat'):
            instance_id = os.path.splitext(filename)[0]
            instance_path = os.path.join(instances_folder, filename)
            m, n, l, s, D = read_dat_file(instance_path)
            
            results_file = f"res/{approach}/{instance_id}_result.json"
            # Load existing results if file exists
            if os.path.exists(results_file):
                with open(results_file, 'r') as file:
                    complete_solution = json.load(file)
            else:
                complete_solution = {}

            # Initialize a new entry for the current approach if not already present
            if solver not in complete_solution:
                complete_solution[solver] = {}
            
                print(f'Processing instance: {instance_id} with approach: {approach} and solver {solver}')
                if approach == 'MIP': 
                    res = solve_MIP_with_timeout(m, n, l.copy(), s.copy(), D)
                elif approach == 'SAT': 
                    res = solve_SAT_with_timeout(m, n, l, s, D)
                elif approach == 'SMT': 
                    res = solve_SMT_with_timeout(m, n, l, s, D)
                elif approach == 'CSP': 
                    res = solve_instance_csp(instance_id, solver=solver)
                
                print(f'Result for {instance_id}: {res}')

                # Store the result for the current instance under the current approach
                complete_solution[solver] = res

                # Save the results to a json file
                json_sol = json.dumps(complete_solution, indent=4)
                save_result(results_file, json_sol)
            else:
                print(f'Skipping instance: {instance_id} with approach: {approach} and solver {solver} as it has already been solved.')

def main():
    approaches = ['MIP', 'SAT', 'SMT', 'CSP']
    solvers = ['gecode', 'chuffed']
    
    for approach in approaches:
        if approach != 'CSP':
            solver='Default'
            run_from_script(approach=approach,solver=solver)
        else: 
            for solver in solvers:
                run_from_script(approach=approach, solver=solver)

if __name__ == '__main__':
    main()