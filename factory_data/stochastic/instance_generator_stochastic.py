"""
For running this script set working directory to ~/SimPyManufacturing
"""
import os

import pandas as pd
import random
from classes.classes import ProductionPlan, Factory, Scenario, Activity
import pickle
import json

from classes.distributions import NormalDistribution

instance_name = 'instance_10_1_factory_1.pkl'
production_plan = pd.read_pickle('factory_data/instances_new/' + instance_name)
default_variance = 2
for i in range(len(production_plan.factory.products)):
    activities = []
    for activity in production_plan.factory.products[i].activities:
        processing_time = activity.processing_time[0]
        distribution = NormalDistribution(processing_time, default_variance)
        activity_stoch = Activity(activity.id, activity.processing_time, activity.product, activity.product_id,
                                  activity.needs, distribution, activity.sequence_id)
        activities.append(activity_stoch)
    production_plan.factory.products[i].activities = activities
    production_plan.list_products()

file_name = f'factory_data/stochastic/instances/' + instance_name
with open(file_name, 'wb') as file:
    pickle.dump(production_plan, file)
    print(f'Object successfully saved to "{file_name}"')
