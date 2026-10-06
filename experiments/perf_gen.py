"""Seeded workload generator for the performance review.

make_workload(pattern, passengers, arrival, floors, seed) -> list of (time, id, source, dest)
  pattern:  interfloor (random source and dest), up_peak (lobby 1 -> random floor),
            down_peak (random floor -> lobby 1), mixed (each request: 1/3 up_peak, 1/3 down_peak,
            1/3 interfloor)
  arrival:  spread (first request at tick 0, then a gap of 1, 2 or 3 ticks, uniform, between
            consecutive requests: about 0.5 requests per tick) or tick0 (every request at tick 0)
The RNG is random.Random(f'{pattern}-{passengers}-{arrival}-{floors}-{seed}').
Running this file writes the CSV for one workload:  python3 experiments/perf_gen.py pattern n arrival floors seed out.csv
"""
import csv
import random
import sys


def make_workload(pattern, passengers, arrival, floors, seed):
    rng = random.Random(f'{pattern}-{passengers}-{arrival}-{floors}-{seed}')
    rows = []
    time = 0
    for number in range(passengers):
        if arrival == 'spread' and number > 0:
            time += rng.randint(1, 3)
        kind = pattern
        if pattern == 'mixed':
            kind = rng.choice(['up_peak', 'down_peak', 'interfloor'])
        if kind == 'up_peak':
            source, dest = 1, rng.randint(2, floors)
        elif kind == 'down_peak':
            source, dest = rng.randint(2, floors), 1
        elif kind == 'interfloor':
            source = rng.randint(1, floors)
            dest = rng.randint(1, floors - 1)
            if dest >= source:
                dest += 1
        else:
            raise ValueError(pattern)
        rows.append((time if arrival == 'spread' else 0, f'p{number}', source, dest))
    return rows


def workload_name(pattern, passengers, arrival, floors, seed):
    return f'{pattern}_n{passengers}_{arrival}_f{floors}_s{seed}'


def write_csv(rows, path):
    with open(path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['time', 'id', 'source', 'dest'])
        w.writerows(rows)


if __name__ == '__main__':
    pattern, n, arrival, floors, seed, out = sys.argv[1:7]
    write_csv(make_workload(pattern, int(n), arrival, int(floors), int(seed)), out)
