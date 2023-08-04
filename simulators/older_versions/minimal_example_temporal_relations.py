from classes.classes import Factory, TemporalRelation
from classes.classes import Product
from classes.classes import Activity
import pandas as pd

my_factory = Factory(name="Myfactory", resource_names=["Filter", "Mixer", "Dryer"], capacity=[1, 1, 1])
product = Product(name="Enzyme_1", id=0)
activity0 = Activity(id=0, processing_time=[4, 4], product="Enzyme_1",
                     product_id="0", needs=[1, 0, 0])
activity1 = Activity(id=1, processing_time=[5, 5], product="Enzyme_1",
                     product_id="0", needs=[0, 1, 0])
product.add_activity(activity=activity0)
product.add_activity(activity=activity1)
product.set_temporal_relations(temporal_relations={(0, 1): TemporalRelation(1)})
my_factory.add_product(product=product)

# Make the activites for product 1
activity0 = Activity(id=0, processing_time=[3, 3], product="Enzyme_2",
                     product_id="1", needs=[0, 0, 1])
activity1 = Activity(id=1, processing_time=[6, 6], product="Enzyme_2",
                     product_id="1", needs=[0, 1, 0])
product = Product(name="Enzyme_2", id=1)
product.add_activity(activity=activity0)
product.add_activity(activity=activity1)
product.set_temporal_relations(temporal_relations={(0, 1): TemporalRelation(1)})
my_factory.add_product(product=product)

from classes.classes import ProductionPlan
my_productionplan = ProductionPlan(id=0, size=2, name="ProductionPlanJanuary", factory=my_factory,
                                   product_ids=[0, 1], deadlines=[8, 20])
my_productionplan.list_products()
my_productionplan.set_sequence(sequence=[0, 1])

from classes.simulator_3 import Simulator
my_simulator = Simulator(plan=my_productionplan, printing=True)
my_simulator.simulate(sim_time=1000, random_seed=1, write=True, output_location=f"minimal_example.csv")
print('------------------------------------------------------------ \n END OF SIMULATION PRINTING \n')

# read input
print('------------------------------------------------------------ \n CONSTRAINT CHECKING \n')
gannt = pd.read_csv("minimal_example.csv")

# initialize number of violations
number_of_violations = 0
# iterate over products
for p, product in enumerate(my_productionplan.products):
    # obtain temporal relations
    for (i, j) in product.temporal_relations:
        print(i, j)
        print(f'The difference between the start time of activity {i} and activity {j} '
              f'from product {p} should be exactly {product.temporal_relations[(i, j)].min_lag}')
        start_i = gannt.loc[(gannt['Product'] == p) & (gannt['Activity'] == i)]['Start'].values[0]
        start_j = gannt.loc[(gannt['Product'] == p) & (gannt['Activity'] == j)]['Start'].values[0]

        print(f'The simulated difference between the start time of activity {i} and activity {j} is {start_j-start_i}')
        if start_j-start_i == product.temporal_relations[(i, j)].min_lag:
            print("CONSTRAINT SATISFIED")
        else:
            print("CONSTRAINT VIOLATED")
            number_of_violations += 1

# check violations of temporal relations by comparing start times of activities within temporal relations
# report on violated relations
print(f'TOTAL NUMBER OF VIOLATIONS {number_of_violations}')
# check violations of temporal relations by comparing start times of activities within temporal relations
# report on violated relations



