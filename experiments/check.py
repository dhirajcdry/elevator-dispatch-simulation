"""Check every rule from the outputs alone, on many runs.

    python3 experiments/check.py

The checks read only what a run returns (the position log and each passenger's times)
and never the simulation's own state, so they test the simulation from the outside.
Prints any rule that was broken, and a summary.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))  # the project folder, for simulate

from assignment import ForecastAssignment, NearestElevator, RoundRobin
from elevator import Elevator
from passenger import Passenger
from service_order import DEFAULT_ALLOWED_DELAY, Forecast
from simulation import Simulation, simulate
from traffic import TRAFFIC, make_requests

BUILDINGS = [(30, 4, 4), (100, 4, 10), (10, 2, 1)]  # floors, elevators, capacity
METHODS = ['round-robin', 'nearest', 'forecast']
SERVICE_ORDERS = ['request', 'direction', 'forecast']


def broken_rules(requests, positions, passengers, floors, capacity) -> list[str]:
    """Every rule this run broke, as messages. An empty list means every rule held."""
    problems = []

    # The position log: every elevator starts at floor 1, stays in the building,
    # and moves at most one floor per tick.
    if positions[0] != [1] * len(positions[0]):
        problems.append('an elevator did not start at floor 1')
    for time, row in enumerate(positions):
        for elevator, floor in enumerate(row):
            if not 1 <= floor <= floors:
                problems.append(f'tick {time}: elevator {elevator} at floor {floor}, outside the building')
            if time > 0 and abs(floor - positions[time - 1][elevator]) > 1:
                problems.append(f'tick {time}: elevator {elevator} moved more than one floor')

    # Each passenger: served, never picked up before asking, and picked up and dropped off
    # where their elevator actually was at those ticks.
    for p in passengers:
        if p.pickup_time is None or p.drop_off_time is None:
            problems.append(f'{p.id} was never delivered')
            continue
        if p.pickup_time < p.request_time:
            problems.append(f'{p.id} was picked up before asking')
        if positions[p.pickup_time][p.assigned_elevator] != p.source:
            problems.append(f'{p.id} was picked up away from floor {p.source}')
        if positions[p.drop_off_time][p.assigned_elevator] != p.destination:
            problems.append(f'{p.id} was dropped off away from floor {p.destination}')

    # Riders aboard each elevator at the end of each tick: picked up at or before it,
    # dropped off after it.
    for elevator in range(len(positions[0])):
        own = [p for p in passengers if p.assigned_elevator == elevator]
        for time in range(len(positions) - 1):
            riders = [p for p in own if p.pickup_time <= time < p.drop_off_time]
            if len(riders) > capacity:
                problems.append(f'tick {time}: elevator {elevator} carried {len(riders)}, capacity {capacity}')
            move = positions[time + 1][elevator] - positions[time][elevator]
            for rider in riders:
                # With riders aboard, an elevator never moves against their direction.
                going_up = rider.destination > rider.source
                if (going_up and move < 0) or (not going_up and move > 0):
                    problems.append(f'tick {time}: elevator {elevator} reversed with {rider.id} aboard')
    return problems


def no_peeking(requests, positions, floors, elevators, capacity, assignment, service_order) -> bool:
    """Rerun with every request after tick T removed: the log up to tick T must be identical,
    because no decision up to T may depend on a later request."""
    cutoff = requests[len(requests) // 2][0]
    earlier = [request for request in requests if request[0] <= cutoff]
    positions_without_later, _ = simulate(earlier, floors, elevators, capacity, assignment, service_order)
    return positions_without_later[:cutoff + 1] == positions[:cutoff + 1]


def allowed_delay_kept(requests, floors, elevators, capacity, assignment) -> bool:
    """The forecast service order's promise: nobody is dropped off more than K ticks
    after the drop-off time first forecast for them. Builds the run by hand to read those forecasts."""
    passengers = [Passenger(id, time, source, dest) for time, id, source, dest in requests]
    service_order = Forecast(allowed_delay=DEFAULT_ALLOWED_DELAY)
    if assignment == 'forecast':
        chosen_assignment = ForecastAssignment(service_order)
    elif assignment == 'nearest':
        chosen_assignment = NearestElevator()
    else:
        chosen_assignment = RoundRobin()
    building = [Elevator(id=i, capacity=capacity) for i in range(elevators)]
    Simulation(passengers, building, chosen_assignment, service_order).run()
    for p in passengers:
        if p.drop_off_time > service_order.first_forecast[p.id] + DEFAULT_ALLOWED_DELAY:
            return False
    return True


def main() -> None:
    runs = 0
    failures = 0
    for floors, elevators, capacity in BUILDINGS:
        for traffic in TRAFFIC:
            for assignment in METHODS:
                for service_order in SERVICE_ORDERS:
                    requests = make_requests(traffic, floors, elevators, seed=0)
                    positions, passengers = simulate(requests, floors, elevators, capacity, assignment, service_order)
                    problems = broken_rules(requests, positions, passengers, floors, capacity)
                    if not no_peeking(requests, positions, floors, elevators, capacity, assignment, service_order):
                        problems.append('the log changed when later requests were removed')
                    if service_order == 'forecast' and not allowed_delay_kept(
                            requests, floors, elevators, capacity, assignment):
                        problems.append(f'someone arrived more than {DEFAULT_ALLOWED_DELAY} ticks after their first forecast')
                    runs += 1
                    if problems:
                        failures += 1
                        print(f'{traffic}, {floors} floors, capacity {capacity}, {assignment} / {service_order}:')
                        for problem in problems[:5]:
                            print('   ', problem)
    print(f'{runs} runs checked, {failures} broke a rule.')


if __name__ == '__main__':
    main()
