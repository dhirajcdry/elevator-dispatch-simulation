"""Run one building: read requests, simulate, write the position log, print statistics.

Example:
    python3 main.py requests.csv --elevators 2 --assignment nearest --service-order request
"""

import argparse
import csv
import statistics

from assignment import NearestCar, RoundRobin
from elevator import Elevator
from passenger import Passenger
from service_order import DirectionBased, Forecast, RequestOrder
from simulation import Simulation

ASSIGNMENTS = {'round-robin': RoundRobin, 'nearest': NearestCar}
SERVICE_ORDERS = {'request': RequestOrder, 'direction': DirectionBased, 'forecast': Forecast}
REQUIRED_COLUMNS = ['time', 'id', 'source', 'dest']


def read_requests(path: str) -> list[Passenger]:
    """Read the request CSV (time,id,source,dest) into passengers, in file order."""
    with open(path, newline='') as file:
        reader = csv.DictReader(file)
        missing = [column for column in REQUIRED_COLUMNS if column not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{path}: missing column(s): {', '.join(missing)}")

        passengers = []
        for row_number, row in enumerate(reader, start=2):  # row 1 is the header
            if any(not row[column] for column in REQUIRED_COLUMNS):
                raise ValueError(f"{path} row {row_number}: every column needs a value")
            try:
                time, source, destination = int(row['time']), int(row['source']), int(row['dest'])
            except ValueError:
                raise ValueError(f"{path} row {row_number}: time, source and dest must be whole numbers")
            passengers.append(Passenger(row['id'].strip(), time, source, destination))
    return passengers


def check_requests(passengers: list[Passenger], floors: int) -> None:
    """Stop with a clear message if any request cannot be served in this building."""
    seen_ids = set()
    for passenger in passengers:
        if passenger.id in seen_ids:
            raise ValueError(f"passenger {passenger.id}: id is used more than once")
        seen_ids.add(passenger.id)
        if passenger.request_time < 0:
            raise ValueError(f"passenger {passenger.id}: request time cannot be negative")
        for floor in (passenger.source, passenger.destination):
            if not 1 <= floor <= floors:
                raise ValueError(f"passenger {passenger.id}: floor {floor} is outside floors 1 to {floors}")
        if passenger.source == passenger.destination:
            raise ValueError(f"passenger {passenger.id}: source and destination are the same floor")


def write_positions(path: str, positions: list[list[int]]) -> None:
    """One row per tick: the time, then every car's floor."""
    car_count = len(positions[0])
    with open(path, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['time'] + [f'elevator_{i}' for i in range(car_count)])
        for time, floors in enumerate(positions):
            writer.writerow([time] + floors)


def print_statistics(passengers: list[Passenger], positions: list[list[int]]) -> None:
    """Minimum, average and maximum wait, travel and total time, in ticks."""
    if not passengers:
        print('No passengers.')
        return
    print(f'Passengers: {len(passengers)}   Last tick: {len(positions) - 1}')
    for label, times in (
        ('Wait time', [p.wait_time for p in passengers]),
        ('Travel time', [p.travel_time for p in passengers]),
        ('Total time', [p.total_time for p in passengers]),
    ):
        print(f'{label:<12} min {min(times):>5}   average {statistics.mean(times):>8.2f}   max {max(times):>5}')


def main() -> None:
    parser = argparse.ArgumentParser(description='Simulate one building of elevators.')
    parser.add_argument('requests', help='CSV file with columns time,id,source,dest')
    parser.add_argument('--floors', type=int, default=100, help='number of floors (default 100)')
    parser.add_argument('--elevators', type=int, default=4, help='number of cars (default 4)')
    parser.add_argument('--capacity', type=int, default=10, help='passengers per car (default 10)')
    parser.add_argument('--assignment', choices=ASSIGNMENTS, default='round-robin')
    parser.add_argument('--service-order', choices=SERVICE_ORDERS, default='request')
    parser.add_argument('--allowed-delay', type=int, default=None,
                        help='forecast only: how far an earlier passenger may be pushed back, in ticks (default no limit)')
    parser.add_argument('--positions-out', default='positions.csv', help='position log file (default positions.csv)')
    args = parser.parse_args()

    for name in ('floors', 'elevators', 'capacity'):
        if getattr(args, name) < 1:
            parser.error(f'--{name} must be at least 1')
    if args.allowed_delay is not None:
        if args.service_order != 'forecast':
            parser.error('--allowed-delay only applies to --service-order forecast')
        if args.allowed_delay < 0:
            parser.error('--allowed-delay cannot be negative')

    try:
        passengers = read_requests(args.requests)
        check_requests(passengers, args.floors)
    except ValueError as error:
        parser.error(str(error))

    elevators = [Elevator(id=i, capacity=args.capacity) for i in range(args.elevators)]
    if args.service_order == 'forecast':
        service_order = Forecast(allowed_delay=args.allowed_delay)
    else:
        service_order = SERVICE_ORDERS[args.service_order]()
    simulation = Simulation(passengers, elevators, ASSIGNMENTS[args.assignment](), service_order)
    positions = simulation.run()

    write_positions(args.positions_out, positions)
    print(f'Building: {args.floors} floors, {args.elevators} cars, capacity {args.capacity}, '
          f'assignment {args.assignment}, service order {args.service_order}')
    if args.service_order == 'forecast':
        if args.allowed_delay is None:
            print('Allowed delay: no limit')
        else:
            print(f'Allowed delay: {args.allowed_delay}')
    print_statistics(passengers, positions)
    print(f'Position log written to {args.positions_out}')


if __name__ == '__main__':
    main()
