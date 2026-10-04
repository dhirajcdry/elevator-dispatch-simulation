"""Service order: which waiting passenger a car picks up next.

Every tick, each option answers two questions about one car:
  who_boards(car)   - the waiting passengers who get on at this floor now
  next_target(car)  - the floor to head for, or None to stay put
The simulation carries out the answers with car.pick_up and car.move_toward.
Drop-offs are not a choice: riders get off when the car reaches their floor.
"""

from elevator import Elevator
from passenger import Passenger


class RequestOrder:
    """First come, first served: pick up passengers in the order they requested.

    A later passenger is never picked up before an earlier one.
    Several riders can be aboard at once.
    """

    def who_boards(self, car: Elevator) -> list[Passenger]:
        boarding = []
        free_places = car.capacity - len(car.riders)
        direction = car.direction

        # car.waiting is in request order, so the front of the line comes first.
        for passenger in car.waiting:
            # Stop at the first passenger who cannot board now:
            # nobody behind them may be picked up first.
            if passenger.source != car.floor or free_places == 0:
                break
            if direction is not None and passenger.direction != direction:
                break
            boarding.append(passenger)
            free_places -= 1
            # Once someone boards, everyone after them must be going the same way.
            direction = passenger.direction
        return boarding

    def next_target(self, car: Elevator) -> int | None:
        # Riders aboard: keep going their way until the last of them is delivered.
        # Floors passed on the way still get drop-offs and boarding each tick.
        if car.riders:
            destinations = [rider.destination for rider in car.riders]
            return max(destinations) if car.direction == 'up' else min(destinations)

        # Empty car: go to whoever is at the front of the line.
        if car.waiting:
            return car.waiting[0].source

        # Nothing to do: stay put.
        return None


class DirectionBased:
    """Sweep one way, picking up anyone on the way who is going that way and fits.

    Turns around only when the car is empty and nothing is left ahead.
    Ignores request order: an earlier passenger can be passed while the car fills up
    with later ones. Protecting earlier passengers is what forecast with allowed delay adds.
    """

    def __init__(self):
        # Each car's current sweep, by car id: 'up', 'down', or None when it has nothing to do.
        self.sweep: dict[int, str | None] = {}

    def who_boards(self, car: Elevator) -> list[Passenger]:
        sweep = self.current_sweep(car)
        # car.waiting is in request order, so earlier requests get the free places first.
        going_our_way_here = [p for p in car.waiting if p.source == car.floor and p.direction == sweep]
        free_places = car.capacity - len(car.riders)
        return going_our_way_here[:free_places]

    def next_target(self, car: Elevator) -> int | None:
        sweep = self.current_sweep(car)
        if sweep is None:
            return None
        # Head for the farthest floor ahead with work: a rider's destination or a waiting passenger.
        # The car passes every floor on the way, so drop-offs and boarding happen as it goes.
        work_floors = [rider.destination for rider in car.riders] + [p.source for p in car.waiting]
        if sweep == 'up':
            ahead = [floor for floor in work_floors if floor > car.floor]
            return max(ahead) if ahead else car.floor
        ahead = [floor for floor in work_floors if floor < car.floor]
        return min(ahead) if ahead else car.floor

    def current_sweep(self, car: Elevator) -> str | None:
        """Decide the car's sweep for this tick and remember it.

        Called by both who_boards and next_target; both calls give the same answer.
        """
        if car.riders:
            # With riders aboard, the sweep is their direction: the car cannot reverse.
            sweep = car.direction
        elif not car.waiting:
            # Empty and nobody waiting: nothing to do, so the car stays put.
            sweep = None
        elif self.sweep.get(car.id) is None:
            # Was idle and has just been given work: start fresh from whoever requested first.
            first = car.waiting[0]
            if first.source == car.floor:
                # Already here: go the way they want to travel, so they can board now.
                sweep = first.direction
            else:
                # Elsewhere: go toward them.
                sweep = 'up' if first.source > car.floor else 'down'
        elif self.has_work_ahead(car, self.sweep[car.id]):
            # Empty, but someone is waiting ahead (or here, going this way): keep going.
            sweep = self.sweep[car.id]
        else:
            # Empty, and nothing left ahead: turn around.
            sweep = 'down' if self.sweep[car.id] == 'up' else 'up'
        self.sweep[car.id] = sweep
        return sweep

    def has_work_ahead(self, car: Elevator, sweep: str) -> bool:
        """Is anyone waiting farther along this sweep, or here and going this way?"""
        for passenger in car.waiting:
            if passenger.source == car.floor and passenger.direction == sweep:
                return True
            if sweep == 'up' and passenger.source > car.floor:
                return True
            if sweep == 'down' and passenger.source < car.floor:
                return True
        return False
