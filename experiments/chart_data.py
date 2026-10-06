"""Run the simulations behind the charts and write experiments/data/charts.json.

    python3 experiments/chart_data.py

Default building (100 floors, 4 elevators, capacity 10), synthetic seeded traffic.
Every value is kept per seed, so a chart can show the spread as well as the mean.
"""

import json
import os
import statistics
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))  # the project folder, for simulate

from main import percentile_95
from simulation import simulate
from traffic import TRAFFIC, make_requests

FLOORS, ELEVATORS, CAPACITY = 100, 4, 10
SEEDS = range(5)
COMBINATIONS = [
    (assignment, service_order)
    for assignment in ['round-robin', 'nearest', 'forecast']
    for service_order in ['request', 'direction', 'forecast']
]
ALLOWED_DELAYS = [0, 10, 20, 40, 80, 120, 160, 320, None]  # None: no limit
PASSENGER_PAIRS = [('round-robin', 'request'), ('round-robin', 'direction'),
                   ('nearest', 'direction'), ('forecast', 'forecast')]


def summary(passengers) -> dict:
    totals = [p.total_time for p in passengers]
    return {
        'average_total': statistics.mean(totals),
        'p95_total': percentile_95(totals),
        'longest_wait': max(p.wait_time for p in passengers),
    }


def every_combination() -> list[dict]:
    """All nine method pairs on every traffic type, one row per seed."""
    rows = []
    for assignment, service_order in COMBINATIONS:
        started = time.perf_counter()
        for traffic_type in TRAFFIC:
            for seed in SEEDS:
                requests = make_requests(traffic_type, FLOORS, ELEVATORS, seed)
                _, passengers = simulate(requests, FLOORS, ELEVATORS, CAPACITY, assignment, service_order)
                rows.append({'assignment': assignment, 'service_order': service_order,
                             'traffic': traffic_type, 'seed': seed, **summary(passengers)})
        print(f'{assignment} / {service_order}: {time.perf_counter() - started:.1f} s', flush=True)
    return rows


def allowed_delay_sweep() -> list[dict]:
    """Forecast for both decisions at each allowed delay K, one row per traffic type and seed."""
    rows = []
    for allowed_delay in ALLOWED_DELAYS:
        started = time.perf_counter()
        for traffic_type in TRAFFIC:
            for seed in SEEDS:
                requests = make_requests(traffic_type, FLOORS, ELEVATORS, seed)
                _, passengers = simulate(requests, FLOORS, ELEVATORS, CAPACITY,
                                         'forecast', 'forecast', allowed_delay)
                rows.append({'allowed_delay': allowed_delay, 'traffic': traffic_type,
                             'seed': seed, **summary(passengers)})
        print(f'K = {allowed_delay}: {time.perf_counter() - started:.1f} s', flush=True)
    return rows


def every_passenger() -> list[dict]:
    """Each passenger's wait and total time, heavy random traffic, all seeds pooled."""
    rows = []
    for assignment, service_order in PASSENGER_PAIRS:
        for seed in SEEDS:
            requests = make_requests('heavy', FLOORS, ELEVATORS, seed)
            _, passengers = simulate(requests, FLOORS, ELEVATORS, CAPACITY, assignment, service_order)
            for p in passengers:
                rows.append({'assignment': assignment, 'service_order': service_order, 'seed': seed,
                             'wait': p.wait_time, 'total': p.total_time})
    return rows


def main() -> None:
    data = {
        'building': {'floors': FLOORS, 'elevators': ELEVATORS, 'capacity': CAPACITY},
        'traffic_types': TRAFFIC,
        'every_passenger': every_passenger(),
        'every_combination': every_combination(),
        'allowed_delay_sweep': allowed_delay_sweep(),
    }
    with open(os.path.join(HERE, 'data', 'charts.json'), 'w') as file:
        json.dump(data, file)
    print('Written to experiments/data/charts.json')


if __name__ == '__main__':
    main()
