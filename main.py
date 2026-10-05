"""Run one building: read requests, simulate, write the position log, print statistics.

Example:
    python3 main.py requests.csv                     (forecast for both decisions, allowed delay 80)
    python3 main.py requests.csv --elevators 2 --assignment nearest --service-order request
"""

import argparse
import csv
import os
import re
import statistics

from passenger import Passenger
from service_order import DEFAULT_ALLOWED_DELAY
from simulation import ASSIGNMENTS, SERVICE_ORDERS, simulate

REQUIRED_COLUMNS = ['time', 'id', 'source', 'dest']
# Digits 0-9 only, with an optional sign. Python's int() also accepts '1_0' and non-English digits.
WHOLE_NUMBER = re.compile(r'[+-]?[0-9]+')


def read_requests(path: str) -> list[tuple[int, str, int, int]]:
    """Read the request CSV into (time, id, source, dest) rows, in file order.

    Column names may have spaces around them and any case; other columns are ignored.
    Blank lines are skipped. Errors name the file and the line.
    """
    try:
        # utf-8-sig also accepts the invisible marker Excel puts at the start of "CSV UTF-8" files.
        with open(path, newline='', encoding='utf-8-sig') as file:
            reader = csv.reader(file)
            header = next(reader, None)
            if header is None:
                raise ValueError(f"{path}: the file is empty")
            names = [name.strip().lower() for name in header]
            missing = [column for column in REQUIRED_COLUMNS if column not in names]
            if missing:
                raise ValueError(f"{path}: missing column(s): {', '.join(missing)}")
            if len(set(names)) != len(names):
                raise ValueError(f"{path}: a column name appears more than once")

            requests = []
            for row in reader:
                line = reader.line_num
                if not any(cell.strip() for cell in row):
                    continue  # blank line
                if len(row) != len(header):
                    raise ValueError(f"{path} line {line}: expected {len(header)} values, found {len(row)}")
                value = {name: row[names.index(name)].strip() for name in REQUIRED_COLUMNS}
                if not all(value.values()):
                    raise ValueError(f"{path} line {line}: every column needs a value")
                for name in ('time', 'source', 'dest'):
                    if not WHOLE_NUMBER.fullmatch(value[name]):
                        raise ValueError(f"{path} line {line}: {name} must be a whole number, got {value[name]!r}")
                requests.append((int(value['time']), value['id'], int(value['source']), int(value['dest'])))
    except UnicodeDecodeError:
        raise ValueError(f"{path}: not a UTF-8 text file")
    except OSError as error:
        raise ValueError(f"{path}: {error.strerror}")
    return requests


def check_output_path(path: str, input_path: str) -> None:
    """Stop before the run if the position log could not be written."""
    folder = os.path.dirname(os.path.abspath(path))
    if os.path.isdir(path):
        raise ValueError(f"{path}: is a folder, not a file")
    if not os.path.isdir(folder):
        raise ValueError(f"{path}: folder {folder} does not exist")
    if not os.access(folder, os.W_OK):
        raise ValueError(f"{path}: folder {folder} is not writable")
    if os.path.abspath(path) == os.path.abspath(input_path):
        raise ValueError(f"{path}: the position log would overwrite the input file")


def write_positions(path: str, positions: list[list[int]]) -> None:
    """One row per tick: the time, then every elevator's floor."""
    elevator_count = len(positions[0])
    with open(path, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['time'] + [f'elevator_{i}' for i in range(elevator_count)])
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
    parser.add_argument('--elevators', type=int, default=4, help='number of elevators (default 4)')
    parser.add_argument('--capacity', type=int, default=10, help='passengers per elevator (default 10)')
    # Forecast for both decisions by default: the best results in the review runs.
    parser.add_argument('--assignment', choices=ASSIGNMENTS, default='forecast',
                        help='which elevator takes each new passenger (default forecast)')
    parser.add_argument('--service-order', choices=SERVICE_ORDERS, default='forecast',
                        help='which waiting passenger each elevator picks up next (default forecast)')
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
        check_output_path(args.positions_out, args.requests)
        requests = read_requests(args.requests)
        positions, passengers = simulate(
            requests, args.floors, args.elevators, args.capacity,
            args.assignment, args.service_order, allowed_delay,
        )
    except ValueError as error:
        parser.error(str(error))

    write_positions(args.positions_out, positions)
    noun = 'elevator' if args.elevators == 1 else 'elevators'
    print(f'Building: {args.floors} floors, {args.elevators} {noun}, capacity {args.capacity}, '
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
