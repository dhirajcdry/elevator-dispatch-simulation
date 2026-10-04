"""Car assignment: which car serves a new passenger.

Each option has one method, choose(elevators, passenger, time), which returns the chosen car.
The simulation then calls car.assign(passenger); the choice never changes.
"""

from elevator import Elevator
from passenger import Passenger
from service_order import predict_finish_times


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


def floors_until_pickup(car: Elevator, passenger: Passenger) -> int:
    """How many floors the car must travel before it could pick this passenger up."""
    distance = abs(car.floor - passenger.source)

    # Where the car's current trip ends, and which way it is going there.
    if car.riders:
        # With riders aboard, the car must keep going their way: it never reverses with riders.
        trip_end = car.last_drop_off
        heading = car.direction
    elif car.waiting:
        # An empty car on its way to its first assigned pickup is heading there, not idle.
        trip_end = car.waiting[0].source
        if trip_end > car.floor:
            heading = 'up'
        else:
            heading = 'down'
    else:
        # An idle car can go straight to the passenger.
        return distance

    # The car can collect the passenger on the way only if they are ahead of it
    # and want to travel the way it is heading.
    passenger_is_ahead = passenger.source == car.floor or car.is_ahead(passenger.source, heading)
    if passenger_is_ahead and passenger.direction == heading:
        return distance

    # Otherwise the car first finishes its trip, then travels back to the passenger.
    # Example: car at 10 with riders going up to 20, passenger at 8:
    # 10 floors up to 20, then 12 floors back down to 8, so 22.
    return abs(trip_end - car.floor) + abs(trip_end - passenger.source)
