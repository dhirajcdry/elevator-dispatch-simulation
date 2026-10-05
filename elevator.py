from passenger import Passenger


class Elevator:
    """One car: where it is, who is aboard, and who is waiting for it."""

    def __init__(self, id: int, capacity: int, floor: int = 1):
        self.id = id
        self.capacity = capacity
        self.floor = floor

        # Both lists keep passengers in the order they were assigned to this car.
        self.riders: list[Passenger] = []   # aboard now
        self.waiting: list[Passenger] = []  # assigned here, not yet picked up

    @property
    def direction(self) -> str | None:
        """'up' or 'down' while riders are aboard: the car must keep going this way.

        None when the car is empty: it is free to go either way, and the
        service order's next target decides where it moves.
        A car never reverses with riders aboard, so every rider is heading the same way.
        """
        if not self.riders:
            return None
        return 'up' if self.riders[0].destination > self.floor else 'down'

    @property
    def passenger_count(self) -> int:
        """Everyone this car is responsible for: aboard plus waiting."""
        return len(self.riders) + len(self.waiting)

    @property
    def rider_destinations(self) -> list[int]:
        """The floor each rider aboard is going to."""
        return [rider.destination for rider in self.riders]

    @property
    def last_drop_off(self) -> int:
        """The farthest rider destination in the car's direction: where its current trip ends."""
        if self.direction == 'up':
            return max(self.rider_destinations)
        return min(self.rider_destinations)

    def is_ahead(self, floor: int, direction: str) -> bool:
        """Going up: is the floor above the car? Going down: is it below the car?"""
        if direction == 'up':
            return floor > self.floor
        return floor < self.floor

    def assign(self, passenger: Passenger) -> None:
        """Make this car responsible for the passenger. An assignment never changes."""
        if passenger.assigned_elevator is not None:
            raise ValueError(f"{passenger.id} is already assigned to elevator {passenger.assigned_elevator}")
        passenger.assigned_elevator = self.id
        self.waiting.append(passenger)

    def drop_off(self, time: int) -> list[Passenger]:
        """Let out every rider whose destination is this floor. Returns who left."""
        leaving = [p for p in self.riders if p.destination == self.floor]
        for passenger in leaving:
            self.riders.remove(passenger)
            passenger.drop_off_time = time
        return leaving

    def pick_up(self, passenger: Passenger, time: int) -> None:
        """Board one waiting passenger at this floor.

        The service order decides who boards; these checks only catch mistakes.
        """
        if passenger.source != self.floor:
            raise ValueError(f"{passenger.id} is at floor {passenger.source}, elevator {self.id} is at {self.floor}")
        if len(self.riders) >= self.capacity:
            raise ValueError(f"elevator {self.id} is full")
        if self.direction is not None and passenger.direction != self.direction:
            raise ValueError(f"{passenger.id} is going {passenger.direction}, elevator {self.id} is going {self.direction}")

        self.waiting.remove(passenger)
        self.riders.append(passenger)
        passenger.pickup_time = time

    def move_one_floor_toward(self, target_floor: int) -> None:
        """Move one floor toward the target, or stay if already there."""
        if target_floor == self.floor:
            return
        # With riders aboard, the target must be ahead: the car never reverses.
        if self.riders and not self.is_ahead(target_floor, self.direction):
            raise ValueError(f"elevator {self.id} cannot reverse with riders aboard")
        if target_floor > self.floor:
            self.floor += 1
        else:
            self.floor -= 1

    def move_to(self, floor: int) -> None:
        """Go straight to a floor. Used by predictions, which count the ticks themselves."""
        # With riders aboard, the floor must be ahead: the car never reverses.
        if self.riders and not self.is_ahead(floor, self.direction):
            raise ValueError(f"elevator {self.id} cannot reverse with riders aboard")
        self.floor = floor
