"""Run one building: read requests, simulate, write the position log, print statistics.

Example:
    python3 main.py requests.csv --elevators 2 --assignment nearest --service-order request
"""

import argparse
import csv
import statistics

from passenger import Passenger
from service_order import DEFAULT_ALLOWED_DELAY
from simulation import ASSIGNMENTS, SERVICE_ORDERS, simulate

REQUIRED_COLUMNS = ['time', 'id', 'source', 'dest']


def read_requests(path: str) -> list[tuple[int, str, int, int]]:
    """Read the request CSV into (time, id, source, dest) rows, in file order."""
    with open(path, newline='') as file:
        reader = csv.DictReader(file)
        missing = [column for column in REQUIRED_COLUMNS if column not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{path}: missing column(s): {', '.join(missing)}")

        requests = []
        for row_number, row in enumerate(reader, start=2):  # row 1 is the header
            if any(not row[column] for column in REQUIRED_COLUMNS):
                raise ValueError(f"{path} row {row_number}: every column needs a value")
            try:
                time, source, destination = int(row['time']), int(row['source']), int(row['dest'])
            except ValueError:
                raise ValueError(f"{path} row {row_number}: time, source and dest must be whole numbers")
            requests.append((time, row['id'].strip(), source, destination))
    return requests


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
    parser.add_argument('--allowed-delay', default=None,
                        help='forecast only: how many ticks an earlier passenger may be pushed back; '
                             f'a whole number, or "none" for no limit (default {DEFAULT_ALLOWED_DELAY})')
    parser.add_argument('--positions-out', default='positions.csv', help='position log file (default positions.csv)')
    args = parser.parse_args()

    allowed_delay = DEFAULT_ALLOWED_DELAY
    if args.allowed_delay is not None:
        if args.service_order != 'forecast':
            parser.error('--allowed-delay only applies to --service-order forecast')
        if args.allowed_delay.strip().lower() == 'none':
            allowed_delay = None
        else:
            try:
                allowed_delay = int(args.allowed_delay)
            except ValueError:
                parser.error('--allowed-delay must be a whole number or "none"')

    try:
        requests = read_requests(args.requests)
        positions, passengers = simulate(
            requests, args.floors, args.elevators, args.capacity,
            args.assignment, args.service_order, allowed_delay,
        )
    except ValueError as error:
        parser.error(str(error))

    write_positions(args.positions_out, positions)
    print(f'Building: {args.floors} floors, {args.elevators} cars, capacity {args.capacity}, '
          f'assignment {args.assignment}, service order {args.service_order}')
    if args.service_order == 'forecast':
        if allowed_delay is None:
            print('Allowed delay: no limit')
        else:
            print(f'Allowed delay: {allowed_delay}')
    print_statistics(passengers, positions)
    print(f'Position log written to {args.positions_out}')


if __name__ == '__main__':
    main()
