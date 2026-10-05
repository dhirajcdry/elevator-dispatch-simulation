"""Elevator assignment: which elevator serves a new passenger.

Each option has one method, choose(elevators, passenger, time), which returns the chosen elevator.
The simulation then calls elevator.assign(passenger); the choice never changes.
"""

from elevator import Elevator
from passenger import Passenger
from service_order import forecast_drop_off_times


class RoundRobin:
    """Take turns: elevator 0, 1, 2, ..., then back to elevator 0. Ignores where elevators are."""

    def __init__(self):
        self.next_index = 0

    def choose(self, elevators: list[Elevator], passenger: Passenger, time: int) -> Elevator:
        elevator = elevators[self.next_index % len(elevators)]
        self.next_index += 1
        return elevator


class NearestElevator:
    """The elevator that could pick the passenger up soonest.

    If several elevators are equally close, the least busy one (fewest passengers aboard
    or waiting) wins; if still tied, the lowest elevator number.
    Distance decides; it does not forecast room or delays to others. That is what forecast adds.
    """

    def choose(self, elevators: list[Elevator], passenger: Passenger, time: int) -> Elevator:
        # Pairs compare their first number, then the second only on a tie.
        # min keeps the first elevator in the list (the lowest number) if still tied.
        return min(elevators, key=lambda elevator: (floors_until_pickup(elevator, passenger), elevator.passenger_count))


class ForecastAssignment:
    """The elevator whose combined total time goes up the least by taking the passenger.

    For each elevator, forecast everyone's drop-off times with and without the newcomer,
    using the building's own service order, so forecasts match what will happen.
    Equally good elevators: the least busy, then the lowest elevator number (as for nearest elevator).
    """

    def __init__(self, service_order):
        # The same service order the elevators follow in this run.
        self.service_order = service_order

    def choose(self, elevators: list[Elevator], passenger: Passenger, time: int) -> Elevator:
        # Same tie-break as nearest elevator.
        return min(elevators, key=lambda elevator: (self.added_time(elevator, passenger, time), elevator.passenger_count))

    def added_time(self, elevator: Elevator, passenger: Passenger, time: int) -> int:
        """The newcomer's own total time plus any delay they cause this elevator's passengers."""
        without = forecast_drop_off_times(elevator, self.service_order, time)
        with_newcomer = forecast_drop_off_times(elevator, self.service_order, time, newcomer=passenger)
        # Request times are fixed, so a difference in drop-off times is a difference in total times.
        return sum(with_newcomer.values()) - sum(without.values())


def floors_until_pickup(elevator: Elevator, passenger: Passenger) -> int:
    """How many floors the elevator must travel before it could pick this passenger up."""
    distance = abs(elevator.floor - passenger.source)

    # Where the elevator is going next (its target), and which way.
    if elevator.riders:
        # With riders aboard, the elevator must keep going their way: it never reverses with riders.
        target = elevator.last_drop_off
        direction = elevator.direction
    elif elevator.waiting:
        # An empty elevator on its way to its first assigned pickup is going there, not idle.
        target = elevator.waiting[0].source
        if target > elevator.floor:
            direction = 'up'
        else:
            direction = 'down'
    else:
        # An idle elevator can go straight to the passenger.
        return distance

    # The elevator can collect the passenger on the way only if they are ahead of it
    # and want to travel the way it is going.
    passenger_is_ahead = passenger.source == elevator.floor or elevator.is_ahead(passenger.source, direction)
    if passenger_is_ahead and passenger.direction == direction:
        return distance

    # Otherwise the elevator first reaches its target, then travels back to the passenger.
    # Example: elevator at 10 with riders going up to 20, passenger at 8:
    # 10 floors up to 20, then 12 floors back down to 8, so 22.
    return abs(target - elevator.floor) + abs(target - passenger.source)
