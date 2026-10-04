"""The clock: releases requests, asks the building's methods for decisions, and logs car floors."""

from elevator import Elevator
from passenger import Passenger


class Simulation:
    """One building: its cars, its passengers, and its two chosen methods."""

    def __init__(
        self,
        passengers: list[Passenger],
        elevators: list[Elevator],
        assignment,
        service_order,
        max_ticks: int = 1_000_000,
    ):
        # Sorting by request time keeps input-file order within the same tick.
        self.passengers = sorted(
            passengers, key=lambda passenger: passenger.request_time
        )
        self.elevators = elevators
        self.assignment = assignment
        self.service_order = service_order
        # A safety limit: a correct service order always finishes, so hitting it means a bug.
        self.max_ticks = max_ticks

    def run(self) -> list[list[int]]:
        """Run until every passenger is delivered.

        Returns every car's floor at each tick, starting at tick 0.
        """
        positions = []
        upcoming = list(self.passengers)  # requests not yet made
        time = 0

        while True:
            # 1. Drop off riders whose destination is this floor.
            for car in self.elevators:
                car.drop_off(time)

            # 2. Release requests made at this tick and assign each one immediately.
            while upcoming and upcoming[0].request_time <= time:
                passenger = upcoming.pop(0)
                car = self.assignment.choose(self.elevators, passenger)
                car.assign(passenger)
                self.service_order.assigned(car, passenger, time)

            # 3. Board whoever the service order allows at each car's floor.
            for car in self.elevators:
                for passenger in self.service_order.who_boards(car):
                    car.pick_up(passenger, time)

            # 4. Log where every car is at this tick.
            positions.append([car.floor for car in self.elevators])

            # 5. Stop once every request has been made and every passenger delivered.
            nobody_left = all(not car.riders and not car.waiting for car in self.elevators)
            if not upcoming and nobody_left:
                return positions

            # 6. Move each car one floor toward the target its service order chose.
            for car in self.elevators:
                target = self.service_order.next_target(car)
                if target is not None:
                    car.move_one_floor_toward(target)

            time += 1
            if time > self.max_ticks:
                raise RuntimeError(
                    f"stopped after {self.max_ticks} ticks with passengers still unserved"
                )
