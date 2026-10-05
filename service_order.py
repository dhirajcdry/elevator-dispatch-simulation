"""Service order: which waiting passenger an elevator picks up next.

Each option plans a passenger's pickup right after they are assigned to an elevator:
  plan_pickup(elevator, passenger, time)
and every tick answers two questions about one elevator, in this order:
  who_boards(elevator)   - the waiting passengers who get on at this floor now
  next_target(elevator)  - the floor to head for, or None to stay put
The simulation carries out the answers with elevator.pick_up and elevator.move_one_floor_toward.
Drop-offs are not a choice: riders get off when the elevator reaches their floor.

Predictions (predict_finish_times) play one elevator forward on a copy. For that, each option
also answers:
  possible_stops(elevator) - floors where the elevator may have to stop next: a drop-off,
                        or someone who could board there
  for_one_elevator(elevator)    - a service order holding only what a prediction for this elevator needs,
                        so only that is copied
"""

import copy

from elevator import Elevator
from passenger import Passenger


class RequestOrder:
    """First come, first served: pick up passengers in the order they requested.

    A later passenger is never picked up before an earlier one.
    Several riders can be aboard at once.
    """

    def plan_pickup(self, elevator: Elevator, passenger: Passenger, time: int) -> None:
        pass  # nothing to plan: pickups follow elevator.waiting, which is in request order

    def who_boards(self, elevator: Elevator) -> list[Passenger]:
        # elevator.waiting is in request order.
        return who_boards_in_order(elevator, elevator.waiting)

    def next_target(self, elevator: Elevator) -> int | None:
        return next_target_in_order(elevator, elevator.waiting)

    def possible_stops(self, elevator: Elevator) -> list[int]:
        return possible_stops_in_order(elevator, elevator.waiting)

    def for_one_elevator(self, elevator: Elevator) -> 'RequestOrder':
        return RequestOrder()  # request order remembers nothing about any elevator


class DirectionBased:
    """Sweep one way, picking up anyone on the way who is going that way and fits.

    Turns around only when the elevator is empty and nothing is left ahead.
    Ignores request order: an earlier passenger can be passed while the elevator fills up
    with later ones. Protecting earlier passengers is what forecast with allowed delay adds.
    """

    def __init__(self):
        # Each elevator's current sweep, by elevator id: 'up', 'down', or None when it has nothing to do.
        self.sweep: dict[int, str | None] = {}

    def plan_pickup(self, elevator: Elevator, passenger: Passenger, time: int) -> None:
        pass  # nothing to plan: the sweep decides each tick in who_boards

    def who_boards(self, elevator: Elevator) -> list[Passenger]:
        sweep = self.current_sweep(elevator)
        # elevator.waiting is in request order, so earlier requests get the free places first.
        going_our_way_here = [
            p for p in elevator.waiting if p.source == elevator.floor and p.direction == sweep
        ]
        free_places = elevator.capacity - len(elevator.riders)
        return going_our_way_here[:free_places]

    def next_target(self, elevator: Elevator) -> int | None:
        # who_boards set this elevator's sweep earlier this tick.
        sweep = self.sweep.get(elevator.id)
        if sweep is None:
            return None
        # Head for the farthest possible stop in the sweep's direction. The elevator passes every
        # floor on the way, so drop-offs and boarding still happen as it goes.
        # Adding the elevator's own floor means it stays put if nothing is ahead.
        floors = self.possible_stops(elevator) + [elevator.floor]
        if sweep == "up":
            return max(floors)
        return min(floors)

    def possible_stops(self, elevator: Elevator) -> list[int]:
        # Anyone waiting may board as the elevator passes, so every waiting passenger's floor counts.
        return elevator.rider_destinations + [passenger.source for passenger in elevator.waiting]

    def for_one_elevator(self, elevator: Elevator) -> 'DirectionBased':
        """Only this elevator's remembered sweep (None if it has had no work yet)."""
        part = DirectionBased()
        part.sweep[elevator.id] = self.sweep.get(elevator.id)
        return part

    def current_sweep(self, elevator: Elevator) -> str | None:
        """Decide the elevator's sweep for this tick and remember it for next_target."""
        if elevator.riders:
            # With riders aboard, the sweep is their direction: the elevator cannot reverse.
            sweep = elevator.direction
        elif not elevator.waiting:
            # Empty and nobody waiting: nothing to do, so the elevator stays put.
            sweep = None
        elif self.sweep.get(elevator.id) is None:
            # Was idle and has just been given work: start fresh from whoever requested first.
            first = elevator.waiting[0]
            if first.source == elevator.floor:
                # Already here: go the way they want to travel, so they can board now.
                sweep = first.direction
            else:
                # Elsewhere: go toward them.
                sweep = "up" if first.source > elevator.floor else "down"
        elif self.has_work_ahead(elevator, self.sweep[elevator.id]):
            # Empty, but someone is waiting ahead (or here, going this way): keep going.
            sweep = self.sweep[elevator.id]
        else:
            # Empty, and nothing left ahead: turn around.
            if self.sweep[elevator.id] == "up":
                sweep = "down"
            else:
                sweep = "up"
        self.sweep[elevator.id] = sweep
        return sweep

    def has_work_ahead(self, elevator: Elevator, sweep: str) -> bool:
        """Is anyone waiting farther along this sweep, or here and going this way?"""
        for passenger in elevator.waiting:
            if elevator.is_ahead(passenger.source, sweep):
                return True
            if passenger.source == elevator.floor and passenger.direction == sweep:
                return True
        return False


# Chosen from the allowed-delay sweep on the default building (100 floors, 4 elevators, capacity 10):
# the average stops improving at about 80 ticks, and the longest wait is lowest there.
DEFAULT_ALLOWED_DELAY = 80


class Forecast:
    """Keep a pickup order for each elevator and follow it the same way request order does.

    When a passenger is assigned, try them at every position in the elevator's pickup order,
    predict everyone's finish times for each, and keep the one with the lowest combined
    total time, as long as nobody already assigned finishes more than allowed_delay ticks
    after their first prediction. Passengers already in the order keep their order among themselves.
    """

    def __init__(self, allowed_delay: int | None = DEFAULT_ALLOWED_DELAY):
        self.allowed_delay = allowed_delay  # None: no limit
        # Each elevator's pickup order, by elevator id.
        self.pickup_orders: dict[int, list[Passenger]] = {}
        # Each passenger's finish time in the order chosen when they were placed:
        # the time they were first told. K is measured from this. By passenger id.
        self.first_predicted_finish: dict[str, int] = {}

    def plan_pickup(self, elevator: Elevator, passenger: Passenger, time: int) -> None:
        # The only time a pickup order changes, apart from passengers leaving it as they board.
        order = self.pickup_orders.get(elevator.id, [])
        self.pickup_orders[elevator.id] = self.place_newcomer(elevator, order, passenger, time)

    def who_boards(self, elevator: Elevator) -> list[Passenger]:
        order = self.pickup_orders.get(elevator.id, [])
        boarding = who_boards_in_order(elevator, order)
        # They board now, so they leave the pickup order.
        for passenger in boarding:
            order.remove(passenger)
        return boarding

    def next_target(self, elevator: Elevator) -> int | None:
        return next_target_in_order(elevator, self.pickup_orders.get(elevator.id, []))

    def possible_stops(self, elevator: Elevator) -> list[int]:
        return possible_stops_in_order(elevator, self.pickup_orders.get(elevator.id, []))

    def for_one_elevator(self, elevator: Elevator) -> 'Forecast':
        """Only this elevator's pickup order, and the first forecasts of its passengers
        (the only ones the allowed-delay check looks at)."""
        part = Forecast(self.allowed_delay)
        part.pickup_orders[elevator.id] = self.pickup_orders.get(elevator.id, [])
        for passenger in elevator.riders + elevator.waiting:
            if passenger.id in self.first_predicted_finish:
                part.first_predicted_finish[passenger.id] = self.first_predicted_finish[passenger.id]
        return part

    def place_newcomer(
        self, elevator: Elevator, order: list[Passenger], newcomer: Passenger, now: int
    ) -> list[Passenger]:
        """Try the newcomer at every position in the pickup order and return the best allowed order."""
        best_order = None
        best_total = None
        newcomer_finish = None

        # Every position from the back: the end first, then each earlier one.
        # The end never delays anyone, so it is always allowed and best_order is always set.
        # On a tie the later position is kept.
        for position in reversed(range(len(order) + 1)):
            new_order = order[:position] + [newcomer] + order[position:]
            # A fresh forecast holding only this order: playing it forward follows new_order.
            trial = Forecast()
            trial.pickup_orders[elevator.id] = new_order
            predicted_finish = predict_finish_times(elevator, trial, now)
            if not self.within_allowed_delay(predicted_finish):
                continue
            # Request times are fixed, so the lowest sum of finish times is the lowest combined total time.
            total = sum(predicted_finish.values())
            if best_order is None or total < best_total:
                best_order = new_order
                best_total = total
                newcomer_finish = predicted_finish[newcomer.id]

        self.first_predicted_finish[newcomer.id] = newcomer_finish
        return best_order

    def within_allowed_delay(self, predicted_finish: dict[str, int]) -> bool:
        """Does every earlier passenger still finish within allowed_delay of their first prediction?"""
        if self.allowed_delay is None:
            return True
        for passenger_id, time in predicted_finish.items():
            # The newcomer has no first prediction yet, so is skipped.
            if passenger_id not in self.first_predicted_finish:
                continue
            if time > self.first_predicted_finish[passenger_id] + self.allowed_delay:
                return False
        return True


def who_boards_in_order(
    elevator: Elevator, pickup_order: list[Passenger]
) -> list[Passenger]:
    """Board in pickup order, starting with the next passenger to be picked up:
    everyone here, going the same way, while there is room."""
    boarding = []
    free_places = elevator.capacity - len(elevator.riders)
    direction = elevator.direction

    for passenger in pickup_order:
        # Stop at the first passenger who cannot board now:
        # nobody later in the pickup order may be picked up before them.
        if passenger.source != elevator.floor or free_places == 0:
            break
        if direction is not None and passenger.direction != direction:
            break
        boarding.append(passenger)
        free_places -= 1
        # Once someone boards, everyone after them must be going the same way.
        direction = passenger.direction
    return boarding


def next_target_in_order(elevator: Elevator, pickup_order: list[Passenger]) -> int | None:
    """Where an elevator following this pickup order heads next, or None to stay put."""
    # Riders aboard: keep going their way until the last of them is delivered.
    # Floors passed on the way still get drop-offs and boarding each tick.
    if elevator.riders:
        return elevator.last_drop_off

    # Empty elevator: go to the next passenger to be picked up.
    if pickup_order:
        return pickup_order[0].source

    # Nothing to do: stay put.
    return None


def possible_stops_in_order(elevator: Elevator, pickup_order: list[Passenger]) -> list[int]:
    """Every floor where an elevator following this pickup order may have to stop next:
    riders' destinations, and the floor of the next passenger to be picked up.
    Nobody later in the pickup order can board before them, so their floors are not stops yet."""
    if pickup_order:
        return elevator.rider_destinations + [pickup_order[0].source]
    return elevator.rider_destinations


def predict_finish_times(elevator: Elevator, service_order, time: int, newcomer: Passenger | None = None) -> dict[str, int]:
    """Predict when everyone assigned to this elevator will reach their floors,
    by playing the elevator forward from `time` with the given service order.

    With a newcomer, they are assigned to the elevator first. Works on copies,
    so the real elevator, passengers and service order are unchanged.
    Follows the same tick order as the simulation, starting at the pick-up step.
    """
    # Copy only this elevator and its part of the service order, never other elevators.
    # Copied together, so the copied elevator and order share the same copied passengers.
    elevator, service_order, newcomer = copy.deepcopy((elevator, service_order.for_one_elevator(elevator), newcomer))
    if newcomer is not None:
        elevator.assign(newcomer)
        service_order.plan_pickup(elevator, newcomer, time)

    predicted_finish = {}
    while True:
        for passenger in service_order.who_boards(elevator):
            elevator.pick_up(passenger, time)
        if not elevator.riders and not elevator.waiting:
            return predicted_finish
        # No new requests arrive during a prediction, so nothing can happen between
        # possible stops: go straight to the next one, counting one tick per floor.
        # (The real simulation never does this: it moves one floor per tick.)
        target = service_order.next_target(elevator)
        stop = next_possible_stop(elevator, target, service_order.possible_stops(elevator))
        time += abs(stop - elevator.floor)
        elevator.move_to(stop)
        for passenger in elevator.drop_off(time):
            predicted_finish[passenger.id] = time


def next_possible_stop(elevator: Elevator, target: int, possible_stops: list[int]) -> int:
    """The first possible stop between the elevator and its target, or the target itself."""
    if target > elevator.floor:
        on_the_way = [floor for floor in possible_stops if elevator.floor < floor < target]
        return min(on_the_way + [target])  # going up: the lowest one comes first
    on_the_way = [floor for floor in possible_stops if target < floor < elevator.floor]
    return max(on_the_way + [target])  # going down: the highest one comes first
