"""Service order: which waiting passenger a car picks up next.

Each option plans a passenger's pickup right after they are assigned to a car:
  plan_pickup(car, passenger, time)
and every tick answers two questions about one car, in this order:
  who_boards(car)   - the waiting passengers who get on at this floor now
  next_target(car)  - the floor to head for, or None to stay put
The simulation carries out the answers with car.pick_up and car.move_one_floor_toward.
Drop-offs are not a choice: riders get off when the car reaches their floor.
"""

import copy

from elevator import Elevator
from passenger import Passenger


class RequestOrder:
    """First come, first served: pick up passengers in the order they requested.

    A later passenger is never picked up before an earlier one.
    Several riders can be aboard at once.
    """

    def plan_pickup(self, car: Elevator, passenger: Passenger, time: int) -> None:
        pass  # nothing to plan: pickups follow car.waiting, which is in request order

    def who_boards(self, car: Elevator) -> list[Passenger]:
        # car.waiting is in request order.
        return who_boards_in_order(car, car.waiting)

    def next_target(self, car: Elevator) -> int | None:
        return next_target_in_order(car, car.waiting)


class DirectionBased:
    """Sweep one way, picking up anyone on the way who is going that way and fits.

    Turns around only when the car is empty and nothing is left ahead.
    Ignores request order: an earlier passenger can be passed while the car fills up
    with later ones. Protecting earlier passengers is what forecast with allowed delay adds.
    """

    def __init__(self):
        # Each car's current sweep, by car id: 'up', 'down', or None when it has nothing to do.
        self.sweep: dict[int, str | None] = {}

    def plan_pickup(self, car: Elevator, passenger: Passenger, time: int) -> None:
        pass  # nothing to plan: the sweep decides each tick in who_boards

    def who_boards(self, car: Elevator) -> list[Passenger]:
        sweep = self.current_sweep(car)
        # car.waiting is in request order, so earlier requests get the free places first.
        going_our_way_here = [
            p for p in car.waiting if p.source == car.floor and p.direction == sweep
        ]
        free_places = car.capacity - len(car.riders)
        return going_our_way_here[:free_places]

    def next_target(self, car: Elevator) -> int | None:
        # Decided by who_boards this tick; boarding keeps the car going the same way.
        sweep = self.sweep.get(car.id)
        if sweep is None:
            return None
        # Head for the farthest floor ahead with work: a rider's destination or a waiting passenger.
        # The car passes every floor on the way, so drop-offs and boarding happen as it goes.
        work_floors = [rider.destination for rider in car.riders]
        work_floors += [passenger.source for passenger in car.waiting]
        ahead = [floor for floor in work_floors if car.is_ahead(floor, sweep)]
        if not ahead:
            return car.floor
        if sweep == "up":
            return max(ahead)
        return min(ahead)

    def current_sweep(self, car: Elevator) -> str | None:
        """Decide the car's sweep for this tick and remember it for next_target."""
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
                sweep = "up" if first.source > car.floor else "down"
        elif self.has_work_ahead(car, self.sweep[car.id]):
            # Empty, but someone is waiting ahead (or here, going this way): keep going.
            sweep = self.sweep[car.id]
        else:
            # Empty, and nothing left ahead: turn around.
            if self.sweep[car.id] == "up":
                sweep = "down"
            else:
                sweep = "up"
        self.sweep[car.id] = sweep
        return sweep

    def has_work_ahead(self, car: Elevator, sweep: str) -> bool:
        """Is anyone waiting farther along this sweep, or here and going this way?"""
        for passenger in car.waiting:
            if car.is_ahead(passenger.source, sweep):
                return True
            if passenger.source == car.floor and passenger.direction == sweep:
                return True
        return False


class Forecast:
    """Keep a pickup order for each car and follow it the same way request order does.

    When a passenger is assigned, try them at every position in the car's pickup order,
    predict everyone's finish times for each, and keep the one with the lowest combined
    total time, as long as nobody already assigned finishes more than allowed_delay ticks
    after their first prediction. Passengers already in the order keep their order among themselves.
    """

    def __init__(self, allowed_delay: int | None = None):
        self.allowed_delay = allowed_delay  # None: no limit
        # Each car's pickup order, by car id.
        self.pickup_orders: dict[int, list[Passenger]] = {}
        # Each passenger's finish time in the order chosen when they were placed:
        # the time they were first told. K is measured from this. By passenger id.
        self.first_predicted_finish: dict[str, int] = {}

    def plan_pickup(self, car: Elevator, passenger: Passenger, time: int) -> None:
        # The only time a pickup order changes, apart from passengers leaving it as they board.
        order = self.pickup_orders.get(car.id, [])
        self.pickup_orders[car.id] = self.place_newcomer(car, order, passenger, time)

    def who_boards(self, car: Elevator) -> list[Passenger]:
        order = self.pickup_orders.get(car.id, [])
        boarding = who_boards_in_order(car, order)
        # They board now, so they leave the pickup order.
        for passenger in boarding:
            order.remove(passenger)
        return boarding

    def next_target(self, car: Elevator) -> int | None:
        return next_target_in_order(car, self.pickup_orders.get(car.id, []))

    def place_newcomer(
        self, car: Elevator, order: list[Passenger], newcomer: Passenger, now: int
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
            trial.pickup_orders[car.id] = new_order
            predicted_finish = predict_finish_times(car, trial, now)
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
    car: Elevator, pickup_order: list[Passenger]
) -> list[Passenger]:
    """Board from the front of the pickup order: everyone here, going the same way, while there is room."""
    boarding = []
    free_places = car.capacity - len(car.riders)
    direction = car.direction

    for passenger in pickup_order:
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


def next_target_in_order(car: Elevator, pickup_order: list[Passenger]) -> int | None:
    """Where a car following this pickup order heads next, or None to stay put."""
    # Riders aboard: keep going their way until the last of them is delivered.
    # Floors passed on the way still get drop-offs and boarding each tick.
    if car.riders:
        return car.last_drop_off

    # Empty car: go to whoever is at the front of the pickup order.
    if pickup_order:
        return pickup_order[0].source

    # Nothing to do: stay put.
    return None


def predict_finish_times(car: Elevator, service_order, time: int, newcomer: Passenger | None = None) -> dict[str, int]:
    """Predict when everyone assigned to this car will reach their floors,
    by playing the car forward from `time` with the given service order.

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
