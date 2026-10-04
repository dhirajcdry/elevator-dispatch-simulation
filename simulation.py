"""Run one building: simulate() checks the requests and settings, builds the cars and
the chosen methods, and runs the clock (Simulation), which releases requests, asks the
methods for decisions, and logs car floors."""

from assignment import ForecastAssignment, NearestCar, RoundRobin
from elevator import Elevator
from passenger import Passenger
from service_order import DEFAULT_ALLOWED_DELAY, DirectionBased, Forecast, RequestOrder

ASSIGNMENTS = {'round-robin': RoundRobin, 'nearest': NearestCar, 'forecast': ForecastAssignment}
SERVICE_ORDERS = {'request': RequestOrder, 'direction': DirectionBased, 'forecast': Forecast}


def simulate(
    requests: list[tuple],
    floors: int = 100,
    elevators: int = 4,
    capacity: int = 10,
    assignment: str = 'forecast',
    service_order: str = 'forecast',
    allowed_delay: int | None = DEFAULT_ALLOWED_DELAY,
) -> tuple[list[list[int]], list[Passenger]]:
    """Run one building on a list of (time, id, source, dest) requests.

    Returns every car's floor at each tick from 0, and the passengers with their times.
    Fresh passengers and cars are built on every call, so the same list can be run
    again with other methods. allowed_delay applies to the forecast service order only
    (None: no limit). Raises ValueError with a clear message if anything is invalid.
    """
    check_building(floors, elevators, capacity, assignment, service_order, allowed_delay)

    passengers = []
    for number, request in enumerate(requests, start=1):
        if len(request) != 4:
            raise ValueError(f"request {number}: expected (time, id, source, dest), got {request!r}")
        time, id, source, destination = request
        passengers.append(Passenger(str(id), time, source, destination))
    check_requests(passengers, floors)

    cars = [Elevator(id=i, capacity=capacity) for i in range(elevators)]
    if service_order == 'forecast':
        chosen_order = Forecast(allowed_delay=allowed_delay)
    else:
        chosen_order = SERVICE_ORDERS[service_order]()
    if assignment == 'forecast':
        # Forecast predicts with the same service order the cars follow.
        chosen_assignment = ForecastAssignment(chosen_order)
    else:
        chosen_assignment = ASSIGNMENTS[assignment]()

    positions = Simulation(passengers, cars, chosen_assignment, chosen_order).run()
    return positions, passengers


def check_building(floors, elevators, capacity, assignment, service_order, allowed_delay) -> None:
    """Stop with a clear message if a building setting or method name is invalid."""
    for name, value in (('floors', floors), ('elevators', elevators), ('capacity', capacity)):
        if not is_whole_number(value) or value < 1:
            raise ValueError(f"{name} must be a whole number of at least 1, got {value!r}")
    if assignment not in ASSIGNMENTS:
        raise ValueError(f"assignment must be one of {', '.join(ASSIGNMENTS)}, got {assignment!r}")
    if service_order not in SERVICE_ORDERS:
        raise ValueError(f"service order must be one of {', '.join(SERVICE_ORDERS)}, got {service_order!r}")
    if allowed_delay is not None and (not is_whole_number(allowed_delay) or allowed_delay < 0):
        raise ValueError(f"allowed delay must be a whole number of at least 0 (or no limit), got {allowed_delay!r}")


def check_requests(passengers: list[Passenger], floors: int) -> None:
    """Stop with a clear message if any request cannot be served in this building."""
    seen_ids = set()
    for passenger in passengers:
        if not passenger.id.strip():
            raise ValueError("every passenger needs an id")
        if passenger.id in seen_ids:
            raise ValueError(f"passenger {passenger.id}: id is used more than once")
        seen_ids.add(passenger.id)
        for value in (passenger.request_time, passenger.source, passenger.destination):
            if not is_whole_number(value):
                raise ValueError(f"passenger {passenger.id}: time, source and dest must be whole numbers")
        if passenger.request_time < 0:
            raise ValueError(f"passenger {passenger.id}: request time cannot be negative")
        for floor in (passenger.source, passenger.destination):
            if not 1 <= floor <= floors:
                raise ValueError(f"passenger {passenger.id}: floor {floor} is outside floors 1 to {floors}")
        if passenger.source == passenger.destination:
            raise ValueError(f"passenger {passenger.id}: source and destination are the same floor")


def is_whole_number(value) -> bool:
    # True and False count as numbers in Python, so they are ruled out explicitly.
    return isinstance(value, int) and not isinstance(value, bool)


class Simulation:
    """One building: its cars, its passengers, and its two chosen methods."""

    def __init__(
        self,
        passengers: list[Passenger],
        elevators: list[Elevator],
        assignment,
        service_order,
    ):
        # Sorting by request time keeps input-file order within the same tick.
        self.passengers = sorted(
            passengers, key=lambda passenger: passenger.request_time
        )
        self.elevators = elevators
        self.assignment = assignment
        self.service_order = service_order

    def run(self) -> list[list[int]]:
        """Run until every passenger is delivered.

        Returns every car's floor at each tick, starting at tick 0.
        Always ends for checked input: the requests are finite, every car has room,
        and every service order keeps heading for the work it has left.
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
                car = self.assignment.choose(self.elevators, passenger, time)
                car.assign(passenger)
                self.service_order.plan_pickup(car, passenger, time)

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
