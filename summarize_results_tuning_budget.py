from general import Settings
import pandas as pd

printing = False
save_resource_usage = False
settings_list = []
results = []
factory_name = "factory_1"
for simulator in ["simulator_3"]:
    for seed in range(1, 2):
        for size in [20, 40]:
            for id in range(1, 5):
                for l1 in [0.5]:
                    l2 = 1 - l1
                    for budget in [100, 200, 400, 800, 1000]:
                        for method in ["local_search"]:
                            for init in ["random"]:
                                setting = Settings(method=method, stop_criterium="Budget", budget=budget,
                                                   instance=f'{size}_{id}_{factory_name}', size=size, simulator=simulator,
                                                   objective=f'l1={l1}_l2={l2}', init=init, seed=seed, l1=l1, l2=l2)
                                settings_list.append(setting)

                            for method in ["local_search"]:
                                for init in ["sorted"]:
                                        setting = Settings(method=method, stop_criterium="Budget",
                                                           budget=budget,
                                                           instance=f'{size}_{id}_{factory_name}', size=size,
                                                           simulator=simulator,
                                                           objective=f'l1={l1}_l2={l2}', init=init, seed=seed, l1=l1,
                                                           l2=l2)
                                        settings_list.append(setting)

for setting in settings_list:
    if setting.simulator == "simulator_1":
        from classes.simulator_1 import Simulator
    elif setting.simulator == "simulator_2":
        from classes.simulator_2 import Simulator
    elif setting.simulator == "simulator_3":
        from classes.simulator_3 import Simulator

    # determine file name
    file_name = setting.make_file_name()
    print(file_name)

    # read in best sequence
    data = pd.read_csv(f'results/{file_name}.txt')
    data_x = data["Best_sequence"].tolist()[-1]
    data_x = data_x[1:-1].split(", ")
    data_x = [int(i) for i in data_x]
    sequence = [i + 1 for i in data_x]
    assert len(data_x) == setting.size
    # read in fitness
    data_y = data["Best_fitness"].tolist()[-1]

    # read runtime and fitness evaluations
    if setting.stop_criterium == "Time":
        runtime = setting.time_limit
        total_budget = data.shape[0]
    elif setting.stop_criterium == "Budget":
        runtime = data["Time"].tolist()[-1]
        total_budget = setting.budget

    # evaluate to find all KPIs
    instance = pd.read_pickle(f"factory_data/instances/instance_{setting.instance}.pkl")
    instance.set_sequence(data_x)
    simulator = Simulator(instance, printing=False)
    makespan, tardiness = simulator.simulate(SIM_TIME=10000000000, RANDOM_SEED=setting.seed, write=False)

    print(f'The best sequence for instance {setting.instance} using {setting.method} has fitness {data_y}')
    results.append({"simulator": setting.simulator,
                    "instance": setting.instance,
                    "method": setting.method,
                    "init": setting.init,
                    "objective": setting.objective,
                    "stop_criterium": setting.stop_criterium,
                    "time": round(runtime),
                    "budget": total_budget,
                    "seed": setting.seed,
                    "sequence": sequence,
                    "makespan": makespan,
                    "tardiness": tardiness,
                    "average_tardiness": tardiness/setting.size,
                    "fitness": data_y,
                    "lambda 1 ": setting.l1,
                    "lambda 2": setting.l2})

results = pd.DataFrame(results)
results.to_csv("results/tuning budget simpy.csv")

