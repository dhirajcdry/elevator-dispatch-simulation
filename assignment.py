"""Car assignment: which car serves a new passenger.

Each option has one method, choose(elevators, passenger), which returns the chosen car.
The simulation then calls car.assign(passenger); the choice never changes.
"""

from elevator import Elevator
from passenger import Passenger


class RoundRobin:
    """Take turns: car 0, 1, 2, ..., then back to car 0. Ignores where cars are."""

    def __init__(self):
        self.next_index = 0

    def choose(self, elevators: list[Elevator], passenger: Passenger) -> Elevator:
        car = elevators[self.next_index % len(elevators)]
        self.next_index += 1
        return car


class NearestCar:
    """The car that could pick the passenger up soonest.

    If several cars are equally close, the least busy one (fewest passengers aboard
    or waiting) wins; if still tied, the lowest car number.
    Distance decides; it does not predict room or delays to others. That is what forecast adds.
    """

    def choose(self, elevators: list[Elevator], passenger: Passenger) -> Elevator:
        best_car = None
        best_floors = None
        best_load = None
        for car in elevators:
            floors = floors_until_pickup(car, passenger)
            load = len(car.riders) + len(car.waiting)
            closer = best_car is None or floors < best_floors
            just_as_close_but_less_busy = floors == best_floors and load < best_load
            # Neither closer nor less busy: the earlier car in the list (lower number) is kept.
            if closer or just_as_close_but_less_busy:
                best_car = car
                best_floors = floors
                best_load = load
        return best_car


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
