# Cdmo
This is the 2023/2024 project for Combinatorial Decision Making and Optimization course.
<br> 
---
The problem presented is the Multiple Couriers Programming.<br>
Different strategies have been used:
- Constraint Programming with MiniZinc
- SAT-Solvers with Z3
- SMT-Solvers with Z3
- Mixed Integer Programming with MIP
---
To run the project with docker:
- ```docker build -t cdmo .``` to build the docker image.
- ```docker run -it cdmo``` to run the docker image.

Then on the bash terminal it is possible to run the script with the command:
- ```python3 run_all.py``` to optimize all the instances with all the approaches and solvers (takes about 4h to finish)
- ```python3 run_single_approach.py``` to optimize all the instances with a single approach and solver.
- ```python3 run_single_instance.py``` to optimize a single instances with a single approach and solver.
- ```python3 run_multiple_instances.py``` to optimize multiple instances with a single approach and solver.

After solving some instances, it's possible to explore the results in the ```/res``` folder.<br>
To re-run the optimization on a given instance, you must remove the result file from the result folder with ```rm res/{approach}/instXX_result.json``` or ```rm res/``` (i.e. ``` rm res/MIP/inst03_result.json && python3 run_single_instance.py```)

---
By:
- Irene Burri
- Laura Lucchiari
- Luigi Manieri
- Luca Mercuriali
