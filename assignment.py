"""Car assignment: which car serves a new passenger.

Each option has one method, choose(elevators, passenger, time), which returns the chosen car.
The simulation then calls car.assign(passenger); the choice never changes.
"""

import copy

from elevator import Elevator
from passenger import Passenger


class RoundRobin:
    """Take turns: car 0, 1, 2, ..., then back to car 0. Ignores where cars are."""

    def __init__(self):
        self.next_index = 0

    def choose(self, elevators: list[Elevator], passenger: Passenger, time: int) -> Elevator:
        car = elevators[self.next_index % len(elevators)]
        self.next_index += 1
        return car


class NearestCar:
    """The car that could pick the passenger up soonest.

    If several cars are equally close, the least busy one (fewest passengers aboard
    or waiting) wins; if still tied, the lowest car number.
    Distance decides; it does not predict room or delays to others. That is what forecast adds.
    """

    def choose(self, elevators: list[Elevator], passenger: Passenger, time: int) -> Elevator:
        # The best car so far, and the two numbers it is judged on.
        best_car = None
        best_floors_away = None
        best_passenger_count = None
        for car in elevators:
            floors_away = floors_until_pickup(car, passenger)
            closer = best_car is None or floors_away < best_floors_away
            just_as_close_but_less_busy = (
                floors_away == best_floors_away and car.passenger_count < best_passenger_count
            )
            # Neither closer nor less busy: the earlier car in the list (lower number) is kept.
            if closer or just_as_close_but_less_busy:
                best_car = car
                best_floors_away = floors_away
                best_passenger_count = car.passenger_count
        return best_car


class ForecastAssignment:
    """The car whose combined total time goes up the least by taking the passenger.

    For each car, predict everyone's finish times with and without the newcomer,
    using the building's own service order, so predictions match what will happen.
    Equally good cars: the least busy, then the lowest car number (as for nearest car).
    """

    def __init__(self, service_order):
        # The same service order the cars follow in this run.
        self.service_order = service_order

    def choose(self, elevators: list[Elevator], passenger: Passenger, time: int) -> Elevator:
        # The best car so far, and the two numbers it is judged on.
        best_car = None
        best_added_time = None
        best_passenger_count = None
        for car in elevators:
            without = predict_finish_times(car, self.service_order, time)
            with_newcomer = predict_finish_times(car, self.service_order, time, newcomer=passenger)
            # The newcomer's own total time plus any delay they cause this car's passengers.
            # Request times are fixed, so a difference in finish times is a difference in total times.
            added_time = sum(with_newcomer.values()) - sum(without.values())
            better = best_car is None or added_time < best_added_time
            just_as_good_but_less_busy = (
                added_time == best_added_time and car.passenger_count < best_passenger_count
            )
            # Neither better nor less busy: the earlier car in the list (lower number) is kept.
            if better or just_as_good_but_less_busy:
                best_car = car
                best_added_time = added_time
                best_passenger_count = car.passenger_count
        return best_car


def predict_finish_times(car: Elevator, service_order, time: int, newcomer: Passenger | None = None) -> dict[str, int]:
    """Predict when everyone assigned to this car will reach their floors,
    by playing the car forward from `time` with the building's service order.

    With a newcomer, they are assigned to the car first. Works on copies,
    so the real car, passengers and service order are unchanged.
    Follows the same tick order as the simulation, starting at the pick-up step.
    """
    # Copied together, so the copies still point at each other.
    car, service_order, newcomer = copy.deepcopy((car, service_order, newcomer))
    if newcomer is not None:
        car.assign(newcomer)
        service_order.plan_pickup(car, newcomer, time)

    predicted_finish = {}
    while True:
        for passenger in service_order.who_boards(car):
            car.pick_up(passenger, time)
        if not car.riders and not car.waiting:
            return predicted_finish
        target = service_order.next_target(car)
        if target is not None:
            car.move_one_floor_toward(target)
        time += 1
        for passenger in car.drop_off(time):
            predicted_finish[passenger.id] = time


def floors_until_pickup(car: Elevator, passenger: Passenger) -> int:
    """How many floors the car must travel before it could pick this passenger up."""
    distance = abs(car.floor - passenger.source)

    # An empty car can go straight to the passenger.
    if car.direction is None:
        return distance

    # With riders aboard, the car must keep going their way: it never reverses with riders.
    # It can collect the passenger on the way only if they are ahead of the car
    # and want to travel in the same direction as the riders.
    passenger_is_ahead = passenger.source == car.floor or car.is_ahead(passenger.source, car.direction)
    if passenger_is_ahead and passenger.direction == car.direction:
        return distance

    # Otherwise the car first delivers its riders, finishing at the farthest destination
    # in its direction, then travels back to the passenger.
    # Example: car at 10 with riders going up to 20, passenger at 8:
    # 10 floors up to 20, then 12 floors back down to 8, so 22.
    return abs(car.last_drop_off - car.floor) + abs(car.last_drop_off - passenger.source)
