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

def run_multiple_instances(approach, solver, indices):
            instances_folder = 'instances'
            filenames = [f for f in os.listdir(instances_folder) if f.endswith('.dat')]
            filenames.sort()
            for index in indices:
                if index <= 0 or index > len(filenames):
                    print(f"Index {index} out of range, skipping.")
                    continue
                
                filename = filenames[index-1]
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
    print("Running the script from the command line.")
    print("Please provide the approach and the solver to use.")
    approach = input("Enter the approach (MIP, SAT, SMT, CSP): ").upper()
    solver = input("Enter the solver (gecode, chuffed) only for CSP \n or press Enter for default: ").lower() or 'Default'
    indices = []
    while True:
        index = int(input("Enter the instance number (1 to 21) you want to solve (0 to stop): "))
        if index == 0:
            break
        if 1 <= index <= 21:
            indices.append(index)
        else:
            print("Invalid index. Please enter a number between 1 and 21.")
    if approach != 'CSP': solver='Default'
    else:
        if solver=='Default': solver='gecode'

    if approach not in ("MIP", "SAT", "SMT", "CSP"): raise Exception("Incorrect approach")
    if solver not in ("gecode", "chuffed", "Default"): raise Exception("Incorrect solver")
    run_multiple_instances(approach=approach, solver=solver, indices=indices)

if __name__ == '__main__':
    main()

