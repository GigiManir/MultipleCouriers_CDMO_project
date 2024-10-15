import re
import os
import subprocess
import multiprocessing


def extract_info_from_output(output_str):
    try:
        objective = re.search(r'z\s*=\s*(\d+);', output_str).group(1)

        # Extract journeys matrix
        journeys_text = re.search(r'journeys\s*=\s*\[([^\]]+)\]', output_str, re.DOTALL).group(1)
        journeys_rows = journeys_text.strip().split('|')[1:-1]
        journeys = [[int(num) for num in row.split(',')] for row in journeys_rows]

        # Extract time values
        solve_time = re.search(r'solveTime=(\d+\.\d+)', output_str).group(1)

        return objective, journeys, int(float(solve_time))
    except Exception as e:
        print(e)


def solve_instance_csp(instance_name, solver="gecode", timeout=300, queue=None):
    model_path = os.path.abspath(f"CSP/model.mzn")
    instance_path = os.path.abspath(f"CSP/{instance_name}.dzn")
    command = [
        'minizinc',
        f'--solver', f'{solver}',
        f'{model_path}',
        f'{instance_path}',
        '--solver-statistics',
        f'--solver-time-limit', f'{timeout * 1000}'
    ]
    if not os.path.exists(command[3]):
        print(f'File {command[3]} does not exist')
    if not os.path.exists(command[4]):
        print(f'File {command[4]} does not exist')

    try:
        # Run the command and capture the output
        result = subprocess.run(command, capture_output=True, text=True, timeout=302)

        if result.returncode != 0:
            return {
                'time': 0,
                'optimal': False,
                'obj': 'N/A',
                'sol': []
            }

        # Print the standard output and standard error
        output = result.stdout
    except subprocess.TimeoutExpired:
        return {
            'time': 0,
            'optimal': False,
            'obj': 'N/A',
            'sol': []
        }
    except Exception as e:
        print(e)

    if "=====UNKNOWN=====" not in output:
        objective, solution, time_needed = extract_info_from_output(output)
    else:
        return {
            'time': 0,
            'optimal': False,
            'obj': 'N/A',
            'sol': []
        }

    for i in range(len(solution)):
        solution[i] = [num for num in solution[i] if num != max(solution[i])]

    res = {"time": time_needed,
           "optimal": True if time_needed < 300 else False,
           "obj": int(objective),
           "sol": solution}
    if queue:
        queue.put(res)
    return res



