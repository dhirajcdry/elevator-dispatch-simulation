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
