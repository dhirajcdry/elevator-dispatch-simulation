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
        if passenger not in self.waiting:
            raise ValueError(f"{passenger.id} is not waiting for elevator {self.id}")
        if passenger.source != self.floor:
            raise ValueError(f"{passenger.id} is at floor {passenger.source}, elevator {self.id} is at {self.floor}")
        if len(self.riders) >= self.capacity:
            raise ValueError(f"elevator {self.id} is full")
        if self.direction is not None and passenger.direction != self.direction:
            raise ValueError(f"{passenger.id} is going {passenger.direction}, elevator {self.id} is going {self.direction}")

        self.waiting.remove(passenger)
        self.riders.append(passenger)
        passenger.pickup_time = time

    def move_toward(self, target_floor: int) -> None:
        """Move one floor toward the target, or stay if already there."""
        if target_floor > self.floor:
            step = 1
        elif target_floor < self.floor:
            step = -1
        else:
            return
        if self.direction == 'up' and step == -1 or self.direction == 'down' and step == 1:
            raise ValueError(f"elevator {self.id} cannot reverse with riders aboard")
        self.floor += step
