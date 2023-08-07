"""
For running this script set working directory to ~/SimPyManufacturing
"""
import os

import pandas as pd
import random
from classes.classes import ProductionPlan, Factory, Scenario, Activity
import pickle
import json
import numpy as np
from classes.distributions import NormalDistribution, PoissonDistribution


def produce_json_data(source_path, output_path):
    production_plan = pd.read_pickle(source_path)
    for i in range(len(production_plan.factory.products)):
        activities = []
        for activity in production_plan.factory.products[i].activities:
            processing_time = activity.processing_time[0]
            default_variance = np.sqrt(processing_time)
            #distribution = NormalDistribution(processing_time, default_variance)
            distribution = PoissonDistribution(processing_time)
            activity_stoch = Activity(activity.id, activity.processing_time, activity.product, activity.product_id,
                                      activity.needs, distribution, activity.sequence_id)
            activities.append(activity_stoch)
        production_plan.factory.products[i].activities = activities
        production_plan.list_products()

    json_str = production_plan.to_json()
    instance_name = source_path.split('/')[-1].split('.')[0]

    file_name = output_path + instance_name + '.json'
    with open(file_name, 'w+') as file:
        file.write(json_str)


if __name__ == '__main__':
    base_path = 'factory_data/instances_legacy/instances_new/'
    output_path = f'factory_data/instances_legacy/stochastic/json_instances/'

    source_instances = os.listdir(base_path)
    error_count = 0
    for instance in source_instances:
        try:
            produce_json_data(base_path + instance, output_path)
            print(instance)
        except Exception as error:
            print("Could not convert instance:" + instance, error)
            error_count += 1
    print("Percent error of conversion", error_count * 100 / len(source_instances))
