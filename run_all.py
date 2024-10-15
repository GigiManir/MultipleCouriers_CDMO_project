import os
import argparse
from MIP.mip_model import solve_MIP_with_timeout
# from SAT.sat_model import solve_SAT_with_timeout
# from SMT.smt_model import solve_SMT_with_timeout
# from CSP.csp_model import solve_CSP_with_timeout

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
        with open(filename, 'w') as file:
            file.write(str(result))


def main():
    parser = argparse.ArgumentParser(description='Choose the approach to solve the problem.')
    parser.add_argument('--approach', choices=['MIP', 'SAT', 'SMT', 'CSP'], required=True, help='The approach to use for solving the problem.')
    args = parser.parse_args()

    complete_solution = dict()
    approach = args.approach
    complete_solution[approach] = dict()

    instances_folder = 'instances'
    for filename in os.listdir(instances_folder):
        if filename.endswith('.dat'):
            instance_id = os.path.splitext(filename)[0]
            instance_path = os.path.join(instances_folder, filename)
            m, n, l, s, D = read_dat_file(instance_path)
            
            if args.approach == 'MIP': res = solve_MIP_with_timeout(m, n, l, s, D)
            # elif args.approach == 'SAT': res = solve_SAT_with_timeout(m, n, l, s, D)
            # elif args.approach == 'SMT': res = solve_SMT_with_timeout(m, n, l, s, D)
            # elif args.approach == 'CSP': res = solve_CSP_with_timeout(m, n, l, s, D)

            complete_solution[approach][instance_id] = res
            print(res)
            # save_result(f'results/{filename}_result.txt', res)
            print()

if __name__ == '__main__':
    main()