import copy
from collections import namedtuple

import simpy
import random
import pandas as pd

from classes.classes import SimulatorLogger, Action, FailureCode


class Simulator:
    def __init__(self, plan, operator, printing=False):
        self.plan = plan
        self.resource_names = plan.factory.resource_names
        self.nr_resources = len(self.resource_names)
        self.capacity = plan.factory.capacity
        self.resources = []
        self.env = simpy.Environment()
        self.resource_usage = {}
        self.printing = printing
        self.nr_clashes = 0
        self.operator = operator
        self.logger = SimulatorLogger(self.__class__.__name__)

    def _availability_constraint_check(self, needs, product_index, activity_id):
        # Check if all resources are available
        failure_code = None
        for r, need in enumerate(needs):
            if need > 0:
                resource_names = self.resource_names[r]
                available_machines = [i.resource_group for i in self.factory.items].count(resource_names)
                if self.printing:
                    print(
                        f'At time {self.env.now}: we need {need} {resource_names} for product index {product_index} with product id {self.plan.products[product_index].id}, activity {activity_id} and currently '
                        f'in the factory we have {available_machines} available')
                if available_machines < need:
                    failure_code = FailureCode.AVAILABILITY
        return failure_code

    def _precedence_constraint_check(self, product_index, activity_id):
        predecessors = self.plan.products[product_index].predecessors[activity_id]
        for pred_activity_id in predecessors:
            temp_rel = self.plan.products[product_index].temporal_relations[(pred_activity_id, activity_id)]
            min_lag = temp_rel.min_lag
            start_pred_log = self.logger.fetch_latest_entry(product_index,
                                                            pred_activity_id, Action.START)

            if start_pred_log is None:
                if self.printing:
                    print(
                        f'At time {self.env.now}: product {product_index}, activity {activity_id} cannot start because '
                        f' predecessors {product_index}, {pred_activity_id} did not start yet')

                return FailureCode.PRECEDENCE
            else:
                start_pred = start_pred_log.timestamp
                if self.env.now - start_pred < min_lag:
                    if self.printing:
                        print(
                            f'At time {self.env.now}: product {product_index} with id {self.plan.products[product_index].id}, activity {activity_id} cannot start because '
                            f' minimal time lag with {product_index}, {pred_activity_id} is not satisfied')
                    start_processing = False
                    self.logger.failure_code = FailureCode.MIN_LAG
                elif temp_rel.max_lag and self.env.now - start_pred > temp_rel.max_lag:
                    if self.printing:
                        print(
                            f'At time {self.env.now}: product {product_index} with id {self.plan.products[product_index].id}, activity {activity_id} cannot start because '
                            f' maximal time lag with {product_index}, {pred_activity_id} is not satisfied')
                    start_processing = False
                    return FailureCode.MAX_LAG
        return None

    def _compatibility_constraint_check(self, product_index, activity_id):
        for constraint in self.plan.products[product_index].activities[activity_id].constraints:
            if (constraint.product_id, constraint.activity_id) in self.logger.active_processes:
                if self.printing:
                    print(
                        f'At time {self.env.now}: activity {activity_id} of product {self.plan.products[product_index].id} has incompatibility with activity {constraint.activity_id} of product {constraint.product_id} which is currently active')
                return FailureCode.COMPATIBILITY

        return None

    def activity_processing(self, activity_id, product_index, proc_time, needs):
        """
        :param activity_id: id of the activity (int)
        :param product_index: id of the product (int)
        :param proc_time: processing time of this activity (int)
        :param resources_required: list with SimPy processes for resource requests (list)
        :param resources_names: list with the corresponding resource names (list)
        :return: generator
        """
        # Trace back the moment in time that the resources are requested
        request_time = self.env.now

        if self.printing:
            print(f'At time {self.env.now}: the available resources are {self.factory.items}')

        self.logger.failure_code = self._availability_constraint_check(needs, product_index, activity_id) or \
                                   self._precedence_constraint_check(product_index, activity_id) or \
                                   self._compatibility_constraint_check(product_index, activity_id)

        # If it is available start the request and processing
        if self.logger.failure_code is None:
            if self.printing:
                print(
                    f'At time {self.env.now}: product {product_index} ACTIVITY {activity_id} requested resources: {needs}')

                # SimPy request
            resources = []
            for r, need in enumerate(needs):
                if need > 0:
                    resource_names = self.resource_names[r]
                    for _ in range(0, need):
                        resource = yield self.factory.get(lambda resource: resource.resource_group == resource_names)
                        resources.append(resource)
            # Trace back the moment in time that the resources are retrieved
            retrieve_time = self.env.now

            if self.printing:
                print(
                    f'At time {self.env.now}: product {product_index} ACTIVITY {activity_id} retrieved resources: {needs}')

            # Trace back the moment in time that the activity starts processing
            start_time = self.env.now
            self.logger.log_activity(self.plan.products[product_index].id,
                                     activity_id, product_index, Action.START, start_time)
            # self.log_start_times[(product_id, activity_id)] = start_time

            # Generator for processing the activity
            yield self.env.timeout(proc_time)

            # Trace back the moment in time that the activity ends processing
            end_time = self.env.now
            self.logger.log_activity(self.plan.products[product_index].id,
                                     activity_id,  product_index, Action.END, end_time)

            # Release the resources that were used during processing the activity
            # For releasing use the SimPy put function from the FilterStore object
            for resource in resources:
                yield self.factory.put(resource)

            if self.printing:
                print(
                    f'At time {self.env.now}: product index {product_index} with id {self.plan.products[product_index].id} ACTIVITY {activity_id} released resources: {needs}')

            # TODO: (Deepali) merge into logger
            self.resource_usage[(product_index, activity_id)] = \
                {"ProductIndex": product_index,
                 "Activity": activity_id,
                 "Needs": needs,
                 "resources": resources,
                 "Request": request_time,
                 "Retrieve": retrieve_time,
                 "Start": start_time,
                 "Finish": end_time}
            # print(self.plan.PRODUCTS[product_ID].ACTIVITIES[activity_ID].start_time)
            # print(self.resource_usage[(product_ID, activity_ID)])
        # If it is not available then we don't process this activity, so we avoid that there starts a queue in the
        # factory
        else:
            if self.printing:
                print(
                    f"At time {self.env.now}: there are no resources available for product {product_index} ACTIVITY {activity_id}, so it cannot start")
            self.operator.signal_failed_activity(product_index=product_index, activity_id=activity_id,
                                                 current_time=self.env.now, failure_code=self.logger.failure_code)
            self.nr_clashes += 1

    def activity_generator(self):
        """Generate activities that arrive at the factory based on earliest start times."""

        finish = False

        # Ask operator about next activity
        while not finish:
            send_activity, delay, activity_id, product_index, proc_time, needs, finish = \
                self.operator.send_next_activity(current_time=self.env.now)

            if send_activity:
                self.env.process(self.activity_processing(activity_id, product_index, proc_time, needs))

            # Generator object that does a time-out for a time period equal to delay value
            yield self.env.timeout(delay)

    def simulate(self, sim_time=1000, random_seed=1, write=False, output_location="Results.csv"):
        """
        :param sim_time: time allowed for running the discrete-event simulation (int)
        :param random_seed: random seed when used in stochastic mode (int)
        :param write: set to true if you want to write output to a csv file (boolean)
        :param output_location: give location for output file (str)
        :return:
        """
        if self.printing:
            print(f'START factory SIMULATION FOR seed {random_seed}\n')

        # Set random seed
        random.seed(random_seed)

        # Reset environment
        self.env = simpy.Environment()

        for act in self.plan.earliest_start:
            self.resource_usage[(act["product_index"], act["activity_id"])] = {"ProductIndex": act["product_index"],
                                                                               "Activity": act["activity_id"],
                                                                               "Needs": float("inf"),
                                                                               "resources": "NOT PROCESSED DUE TO CLASH",
                                                                               "Request": float("inf"),
                                                                               "Retrieve": float("inf"),
                                                                               "Start": float("inf"),
                                                                               "Finish": float("inf")}

        # Create the factory that is a SimPy FilterStore object
        self.factory = simpy.FilterStore(self.env, capacity=sum(self.capacity))

        # Create the resources that are present in the SimPy FilterStore
        Resource = namedtuple('Machine', 'resource_group, id')
        items = []
        for r in range(0, self.nr_resources):
            for j in range(0, self.capacity[r]):
                resource = Resource(self.resource_names[r], j)
                items.append(copy.copy(resource))
        self.factory.items = items

        # Execute the activity_generator
        self.env.process(self.activity_generator())
        self.env.run(until=sim_time)

        # Process results
        resource_usage_df = []
        for i in self.resource_usage:
            resource_usage_df.append(self.resource_usage[i])

        self.resource_usage = pd.DataFrame(resource_usage_df)

        if self.printing:
            print(f' \nSIMULATION OUTPUT\n {self.resource_usage}')
        finish_times = self.resource_usage["Finish"].tolist()
        finish_times = [i for i in finish_times if i != float("inf")]
        makespan = max(finish_times)
        lateness = 0

        nr_unfinished_products = 0
        for p in range(len(self.plan.products)):
            schedule = self.resource_usage[self.resource_usage["ProductIndex"] == p]
            finish = max(schedule["Finish"])
            if finish == float("inf"):
                nr_unfinished_products += 1
                if self.printing:
                    print(f'Product {p} did not finish, while the deadline was {self.plan.products[p].deadline}.')

            else:
                lateness += max(0, finish - self.plan.products[p].deadline)
                if self.printing:
                    print(
                        f'Product {p} finished at time {finish}, while the deadline was {self.plan.products[p].deadline}.')

        if self.printing:
            print(f"The makespan corresponding to this schedule is {makespan}")
            print(f"The lateness corresponding to this schedule is {lateness}")
            print(f"The number of unfinished products is {nr_unfinished_products}")

        if write:
            self.resource_usage.to_csv(output_location)

        return makespan, lateness, nr_unfinished_products
