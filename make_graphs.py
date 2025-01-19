import os
import json
import pathlib as pl
import numpy as np
import matplotlib.pyplot as plt

# Define the directory where 'res' folder is located
base_dir = 'res' 

def make_plot(data):
    # Prepare the data for plotting
    models = list(data.keys())
    solvers = {model: list(data[model].keys()) for model in models}

    # Plotting the times for each solver in each model
    fig, ax = plt.subplots()

    for model in models:
        for solver in solvers[model]:
            times = data[model][solver]["time"][:10]
            ax.plot(list(range(1, len(times) + 1)), times, label=f'{model} - {solver}')

    ax.set_xlabel('Instance')
    ax.set_ylabel('Time')
    ax.set_title('Solver Times for Each Model')
    ax.legend()
    plt.xticks(list(range(1, len(times) + 1)))
    
    # save the graph to file
    plt.savefig(f"graph_all.png", dpi=500)

    plt.show()


def plot_all():
    # Initialize dictionaries to store results
    model_data = {}

    # Traverse through each model folder
    for model_folder in os.listdir(base_dir):
        model_path = os.path.join(base_dir, model_folder)

        if os.path.isdir(model_path):
            model_data[model_folder] = {}

            # Initialize lists for time and obj values for each solver
            for filename in os.listdir(model_path):
                if filename.endswith('.json'):
                    json_file = os.path.join(model_path, filename)

                    # Read and parse JSON file
                    with open(json_file, 'r') as f:
                        data = json.load(f)

                        for key, value in data.items():
                            solver_name = key
                            time_value = value.get('time')
                            obj_value = value.get('obj')

                            if solver_name not in model_data[model_folder]:
                                model_data[model_folder][solver_name] = {'time': [], 'obj': []}

                            if time_value is not None:
                                model_data[model_folder][solver_name]['time'].append(time_value)

                            if obj_value is not None:
                                model_data[model_folder][solver_name]['obj'].append(obj_value)

    # Print or use the collected data as needed
    for model, solver_data in model_data.items():
        print(f"Model: {model}")
        for solver, values in solver_data.items():
            print(f"- Solver: {solver}")
            print(f"  - Times: {values['time']}")
            print(f"  - Objs: {values['obj']}")
    make_plot(model_data)


def plot_one(model):

    data_dir = pl.Path(base_dir) / model

    # Get the data
    data = {}

    # load all json file
    for file in data_dir.glob('*.json'):
        with open(file) as f:
            data[file.stem] = json.load(f)

    instance_number = len(data)

    # extract the time
    data_model = {}

    for instance_id, instance_data in data.items():
        instance_id = instance_id[4:]

        for model_name, model_data in instance_data.items():
            if model_name not in data_model:
                data_model[model_name] = [_ for _ in range(instance_number)]

            data_model[model_name][int(instance_id[:2]) - 1] = model_data['time']

    label = list(data_model.keys())
    times = np.array(list(data_model.values()))


    print("Shape of times:", times.shape)
    print("Data model:", data_model)

    fontsize = 20
    # Plot the data
    plt.figure(figsize=(20, 10))
    plt.grid()
    plt.title("Time passed computing each instance", weight="bold", fontsize=fontsize)
    plt.xlabel("Instance n°", weight="bold", fontsize=fontsize)
    plt.ylabel("Average time (in sec)", weight="bold", fontsize=fontsize)

    # Make x axis ticks

    plt.xticks(np.arange(0, times.shape[1], 1), labels=np.arange(1, times.shape[1] + 1, 1),  fontsize=fontsize)
    plt.yticks(fontsize=fontsize)


    # Change marker style for each line

    markers = ['o', 'v', 's', 'p', 'P', '*', 'h', 'H', 'D', 'd', 'X', 'x', '+', '|', '_']
    for i, model_name in enumerate(label):
        # Change marker size
        # plt.plot(times[i], label=model_name, marker=markers[i])
        plt.plot(times[i], label=model_name, marker=markers[i], markersize=12, linewidth=3)

    plt.legend(fontsize=fontsize, loc='upper right')

    # save the graph to file
    plt.savefig(f"{model}_graph.png", dpi=500)

    plt.show()

def main():
    plot_all()
    plot_one('CSP')
    plot_one('SAT')
    plot_one('SMT')
    plot_one('MIP')

if __name__ == '__main__':
    main()