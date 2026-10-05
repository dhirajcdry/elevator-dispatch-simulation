"""Synthetic traffic for the experiments: seeded, so every run gives the same requests.

make_requests(traffic, floors, elevators, seed) returns (time, id, source, dest) rows,
the same shape simulate() takes. Requests arrive over 300 ticks; the number per tick is
random (Poisson), with an average that grows with the number of elevators.
"""

import math
import random

TICKS = 300

# Each traffic type, and what it models.
TRAFFIC = {
    'up_peak': 'morning: 90% go from the lobby up',
    'down_peak': 'evening: 90% go down to the lobby',
    'lunch': 'lunch: 40% up from the lobby, 40% down to it, 20% between floors',
    'interfloor': 'between floors: random source and destination',
    'hot_floor': 'one busy floor: 70% of trips start or end at the middle floor',
    'bursts': 'light background, plus a burst of lobby requests every 60 ticks',
    'sparse': 'very light, random trips',
    'stream_long': 'one long trip down, asked first, among a stream of short trips near the lobby',
    'heavy': 'heavy, random trips',
    'light': 'light, random trips',
}

# Average requests per tick for each elevator in the building.
RATE_PER_ELEVATOR = {
    'up_peak': 0.12, 'down_peak': 0.12, 'lunch': 0.12, 'interfloor': 0.12, 'hot_floor': 0.12,
    'bursts': 0.02, 'sparse': 0.02, 'stream_long': 0, 'heavy': 0.35, 'light': 0.03,
}


def make_requests(traffic: str, floors: int, elevators: int, seed: int) -> list[tuple]:
    rng = random.Random(f'{traffic}-{floors}-{elevators}-{seed}')
    rate = RATE_PER_ELEVATOR[traffic] * elevators
    middle = max(2, floors // 2)
    trips = []  # (time, source, dest)

    for time in range(TICKS):
        for _ in range(poisson(rng, rate)):
            share = rng.random()
            if traffic == 'up_peak':
                if share < 0.9:
                    trips.append((time, 1, rng.randint(2, floors)))
                else:
                    trips.append((time, *random_trip(rng, floors)))
            elif traffic == 'down_peak':
                if share < 0.9:
                    trips.append((time, rng.randint(2, floors), 1))
                else:
                    trips.append((time, *random_trip(rng, floors)))
            elif traffic == 'lunch':
                if share < 0.4:
                    trips.append((time, 1, rng.randint(2, floors)))
                elif share < 0.8:
                    trips.append((time, rng.randint(2, floors), 1))
                else:
                    trips.append((time, *random_trip(rng, floors)))
            elif traffic == 'hot_floor':
                if share < 0.35:
                    trips.append((time, middle, other_floor(rng, floors, middle)))
                elif share < 0.7:
                    trips.append((time, other_floor(rng, floors, middle), middle))
                else:
                    trips.append((time, *random_trip(rng, floors)))
            else:
                trips.append((time, *random_trip(rng, floors)))
        if traffic == 'bursts' and time % 60 == 0:
            for _ in range(5 * elevators):
                trips.append((time, 1, rng.randint(2, floors)))

    if traffic == 'stream_long':
        # The long trip asks first; short trips between the lobby and a tenth of the way up follow.
        trips.append((0, floors - 1, 1))
        top_of_stream = max(3, floors // 10)
        for time in range(TICKS):
            for _ in range(poisson(rng, 0.25 * elevators)):
                source = rng.randint(1, top_of_stream - 1)
                trips.append((time, source, rng.randint(source + 1, top_of_stream)))

    requests = []
    for number, (time, source, dest) in enumerate(trips):
        requests.append((time, f'p{number}', source, dest))
    return requests


def poisson(rng: random.Random, average: float) -> int:
    """A random count with this average (Knuth's method: multiply random numbers until small)."""
    limit = math.exp(-average)
    count = 0
    product = 1.0
    while True:
        product *= rng.random()
        if product <= limit:
            return count
        count += 1


def random_trip(rng: random.Random, floors: int) -> tuple[int, int]:
    source = rng.randint(1, floors)
    return source, other_floor(rng, floors, source)


def other_floor(rng: random.Random, floors: int, not_this: int) -> int:
    """A random floor other than not_this."""
    floor = rng.randint(1, floors)
    while floor == not_this:
        floor = rng.randint(1, floors)
    return floor
