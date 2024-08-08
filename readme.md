# Cdmo
This is the 2022/2023 project for Combinatorial Decision Making and Optimization course.
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
- ```python3 gui_solvers.py``` to run a command line interface and choose the solver and the instance to solve.
- ```python3 solvers.py``` with the appropriate arguments to run the solving.

In particular for the solvers.py script the arguments are:
- ```--instances``` that is a list of comma separated instances numbers to solve. Also it's possible to pass only one instance or the string 'all' 
to run on all the instances.
- ```--model``` that is a list of comma separated models to use. Also it's possible to pass only one model or the string 'all' to select 
all model
- ```--max_process``` the maximum number of process to use. The default value is 4, for more than 4 process the computer need a lot of RAM.
- ```--result_folder``` the folder where to save the results.
- ```--build_plot``` if present the script will build the plot of the results.
- ```--plot_folder``` the folder where to save the plot.
