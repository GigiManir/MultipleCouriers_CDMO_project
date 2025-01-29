import os
import datetime as t
import time  as tm
import minizinc


def solve_instance_csp(instance_name, solver="gecode", timeout=300, queue=None):
    model_path = os.path.abspath(f"CSP/model.mzn")
    instance_path = os.path.abspath(f"CSP/instances/{instance_name}.dzn")

    # Load the MiniZinc model
    model = minizinc.Model()
    model.add_file(model_path)
    model.add_file(instance_path)

    # Create a MiniZinc instance
    instance = minizinc.Instance(minizinc.Solver.lookup(solver), model)

    # Set the time limit (in milliseconds)
    instance["time_limit"] = timeout * 1000

    try:
        # Solve the instance
        start_time = tm.time()
        result = instance.solve(timeout=t.timedelta(seconds=timeout))
        end_time = tm.time()
        total_time = end_time - start_time 
        print(result.status)
        if result.status is minizinc.Status.UNSATISFIABLE:
                                return {
                                    'time': int(result.statistics['solveTime'].total_seconds()), 
                                    'optimal': False, 
                                    'obj': "N/A", 
                                    'sol': []
                                    }
                               
        elif result.status is minizinc.Status.UNKNOWN:
            return {
                'time': timeout, 
                'optimal': False, 
                'obj': "N/A", 
                'sol': []
                }
        
        else:
            if total_time < timeout:
                optimal = True
                time = result.statistics['solveTime'].total_seconds() 
            else:
                optimal = False
                time =timeout
            
           
            objective = result['z']
            solution = result['journeys']
            for i in range(len(solution)):
                solution[i] = [num for num in solution[i] if num != max(solution[i])] 
            

            return {
                'time': int(time), 
                'optimal': optimal, 
                'obj': objective, 
                'sol': solution
                }
            
    
    except Exception as e:
        print(e)
        return {
            'time': 0,
            'optimal': False,
            'obj': 'N/A',
            'sol': []
        }

def main():
    instances_folder = 'instances'
    for filename in os.listdir(instances_folder):
        if filename.endswith('.dzn'):
            instance_id = os.path.splitext(filename)[0]
            res = solve_instance_csp(instance_id)
            print(res)
            print()

if __name__ == '__main__':
    main()