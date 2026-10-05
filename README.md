# Elevator simulation

A discrete-time simulation of a destination-dispatch elevator system. Each passenger gives their origin and destination when they call, the system assigns them an elevator straight away, and time moves one floor of travel per tick.

The elevator system makes two decisions:

- **Elevator assignment:** which elevator takes a new passenger. Made once, when the request arrives, and never changed.
- **Service order:** which waiting passenger an elevator picks up next. Drop-offs are not a choice: riders get off at their floor.

Each decision has three methods, chosen before a run. The default is **forecast** for both.

## How to run

Python 3.10 or later, standard library only.

```
python3 main.py requests.csv
python3 main.py requests.csv --elevators 2 --assignment nearest --service-order direction
python3 main.py requests.csv --allowed-delay 20
python3 -m unittest
```

| Option | Default | Meaning |
| --- | --- | --- |
| `--floors` | 100 | floors are numbered 1 to n |
| `--elevators` | 4 | all start at floor 1 |
| `--capacity` | 10 | passengers per elevator |
| `--assignment` | `forecast` | `round-robin`, `nearest` or `forecast` |
| `--service-order` | `forecast` | `request`, `direction` or `forecast` |
| `--allowed-delay` | 80 | forecast service order only: the fairness limit K in ticks, or `none` |
| `--positions-out` | `positions.csv` | the position log |

The input CSV has the columns `time,id,source,dest`. The position log has one row per tick from 0: `time,elevator_0,elevator_1,...`. The statistics for the sample input, run with the second command:

```
Building: 100 floors, 2 elevators, capacity 10, assignment nearest, service order direction
Passengers: 3   Last tick: 72
Wait time    min     0   median     0.0   average    14.33   95th percentile    43   max    43
Travel time  min    19   median    36.0   average    35.00   95th percentile    50   max    50
Total time   min    36   median    50.0   average    49.33   95th percentile    62   max    62
Longest wait: passenger3 (20 to 1) waited 43 ticks for elevator 1
Elevator 0: 1 passenger, moved 50 floors
Elevator 1: 2 passengers, moved 72 floors
Position log written to positions.csv
```

From Python, the same run is one call on a list of requests:

```python
from simulation import simulate

positions, passengers = simulate(
    [(0, 'passenger1', 1, 51), (0, 'passenger2', 1, 37), (10, 'passenger3', 20, 1)],
    elevators=2, assignment='nearest', service_order='direction',
)
```

## How a tick works

1. **Drop off** riders whose destination is the elevator's floor.
2. **Release** the requests made at this tick, in file order, and assign each to an elevator. Later requests are not looked at.
3. **Pick up** waiting passengers at each elevator's floor, as the service order and capacity allow.
4. **Log** every elevator's floor.
5. **Stop** once every request has been made and every passenger delivered.
6. **Move** each elevator one floor toward its service order's target.

Wait time is pickup minus request, travel time is drop-off minus pickup, and total time is wait plus travel.

## Results

Each cell: the best simple method → forecast for both. "Best simple" is the best of round robin or nearest elevator with request order or direction-based, picked separately for each traffic type. Default building (100 floors, 4 elevators, capacity 10), synthetic seeded traffic, mean of 5 seeds, times in ticks.

| Traffic | What it is | Average total time | Longest wait |
| --- | --- | ---: | ---: |
| up_peak | morning: 90% go from the lobby up | 266 → **222** | 506 → **361** |
| down_peak | evening: 90% go down to the lobby | 215 → **136** | 614 → **236** |
| lunch | both ways through the lobby, some between floors | 132 → **90** | 395 → **123** |
| interfloor | trips between random floors | 108 → **71** | 302 → **137** |
| hot_floor | 70% of trips start or end at the middle floor | 89 → **57** | 291 → **111** |
| bursts | light, plus a lobby burst every 60 ticks | 145 → **145** | 348 → **243** |
| sparse | very light, random trips | 66 → **59** | 123 → **87** |
| stream_long | one long trip among short trips near the lobby | 8 → **7** | 98 → **98** |
| heavy | heavy, random trips | 201 → **150** | 659 → **318** |
| light | light, random trips | 76 → **68** | 159 → **104** |

- **Forecast has the best average on every traffic type**, tying only on bursts, and cuts the longest wait by roughly 30 to 70% everywhere except stream_long.
- **Elevator assignment is the bigger lever.** With direction-based service, switching the assignment from round robin to forecast cuts trips between random floors from 128 to 73; switching the service order to forecast then gives 71.
- **Forecast's service order earns its place on the worst case.** With forecast assignment, it cuts the longest wait from 467 to 318 in heavy traffic and from 490 to 236 in down-peak.
- **Request order collapses under load:** an elevator carries about one rider per trip (heavy traffic: 2,984 with round robin / request order, against 150 with forecast for both).
- **The cost is running time:** the 50 forecast / forecast runs behind this table take about 50 seconds; every simple pair takes under a second.

`python3 experiments/compare.py` (about 2 minutes) reproduces every number, for this building and a 30-floor one, in [`experiments/results.md`](experiments/results.md).

## The methods

"30-floor building" below means 30 floors, 4 elevators, capacity 4.

### Elevator assignment

**Round robin:** elevators take turns.
- Good: simplest; spreads people evenly, so a lobby burst never piles into one elevator.
- Bad: ignores where elevators are and how full they are (30-floor building, interfloor: 36, against 27 for nearest and 20 for forecast).

**Nearest elevator:** the elevator that could pick the passenger up soonest. An elevator heads for its riders' farthest destination, or with nobody aboard its first assigned pickup. If the passenger is on the way, the cost is the distance; otherwise it is the distance to that target and back. Ties go to the least busy elevator, then the lowest number.
- Good: cheap; uses where each elevator already has to go.
- Bad: counts floors, not how busy or full an elevator is.
  - Lobby burst: elevator 0 at the lobby, the other three at floor 6, 20 lobby requests. At capacity 4 it sends all 20 to elevator 0 (average 83, against 31 for round robin).
  - A full elevator 4 floors away beats an idle one 15 floors away. The passenger arrives at tick 99 instead of 20.

**Forecast assignment:** for each elevator, forecast everyone's drop-off times with and without the new passenger, using the same service order the elevators follow. Choose the elevator whose combined total time rises least.
- Good: sees waiting passengers, capacity and detours. Best average on every traffic type. Its forecasts match what then happens, because they run the same code.
- Bad: the slowest method. It also knows only requests already made: in the sample input, splitting the first two passengers costs nothing at tick 0 but leaves no idle elevator for passenger3 (62 instead of 38).

### Service order

**Request order:** first come, first served.
- Good: nobody can be passed over.
- Bad: about one rider per trip under load (30-floor building, heavy: 770, against 81 for direction-based).

**Direction-based:** keep going one way, pick up anyone on the way going that way who fits, and turn only when empty with nothing ahead.
- Good: efficient; free pickups on the way.
- Bad: no memory of who asked first. A passenger can be passed again and again while the elevator arrives full. With capacity 1 and a steady stream, one wait grew by 14 ticks per extra stream passenger.

**Forecast service order:** each elevator keeps a pickup order. A new passenger is tried at every position, and the order with the lowest combined total time is kept, as long as nobody already assigned arrives more than **K** ticks after their first forecast.
- Good: one dial between fairness and efficiency, and K is a guarantee.
- Bad: slower. Only the newcomer's position is chosen, and boarding follows the order strictly, so someone later in the order is not picked up on the way.

**Choosing K.** On the default building (7 traffic types, forecast for both decisions), the average flattens at about K = 80, within about 1% of no limit, and the longest wait is near its lowest there. So K = 80 is the default. It was tuned on this building and these traffic types; for another building or load, the same sweep would find the K that best balances fairness and efficiency there.

### Can anyone wait forever?

- **Request order:** no.
- **Direction-based:** with an endless stream that keeps the elevator full, yes. With a finite input everyone is still served.
- **Forecast:** no, while K is set.

The assignment decides how crowded your elevator gets; only the service order decides whether others can keep going first. Overload is different: if requests arrive faster than the elevators can carry them, everyone waits longer, whatever the methods.

## How I know it's correct

- **70 unit tests** with exact times and positions worked out by hand, including the assignment's sample input.
- **The code refuses to break a rule:** an elevator will not board someone at another floor, over capacity or going the wrong way, or reverse with riders aboard.
- **An outside rule check** (`python3 experiments/check.py`, about 50 seconds). It covers 270 runs: every traffic type, every method pair and 3 buildings. It reads only the position log and each passenger's times, and checks floors, one floor per tick, pickups and drop-offs where the elevator was, capacity and direction. It was tested by corrupting runs on purpose.
- **No peeking:** removing every request after a tick T leaves the log up to T unchanged.
- **K holds:** nobody is dropped off more than K ticks after their first forecast.
- **Independent checks:** separate runs with their own traffic and rule checks. Nothing broke, every forecast matched what happened, and every hand-worked case matched. The data is in [`experiments/data/`](experiments/data/).
- **Refactors changed nothing:** every speed-up was checked against the previous version on 1,490 runs.

## Assumptions

- One tick is one floor. Boarding and leaving take no time.
- Floors start at 1. All elevators start at floor 1 and have the same capacity.
- An elevator never reverses with riders aboard; only passengers going the riders' way may board.
- An idle elevator stays where it is.
- Assignments and destinations never change.
- Same-tick requests are handled in file order; unsorted input is sorted by time.
- Invalid requests are rejected with a clear message: floors out of range, source equal to destination, bad or negative times, blank or repeated ids.
- There is no tick limit, so a request at a huge time means a huge position log.

## Performance

Default building, random traffic between floors, one run at a time on an Apple M4 Pro:

| Passengers | Methods | Seconds | Per passenger |
| --- | --- | ---: | ---: |
| 1,000 spread over time | forecast / forecast | 1.4 | 1.4 ms |
| 20,000 spread over time | forecast / forecast | 33 | 1.6 ms |
| 5,000 spread over time | forecast / request order | 59 | 12 ms |
| 200 all at tick 0 | forecast / forecast | 3.7 | 18 ms |
| 500 all at tick 0 | forecast / forecast | 51 | 100 ms |
| 20,000 spread over time | nearest / direction-based | 0.25 | 0.01 ms |

A real building handles requests one at a time as they arrive, so the time per passenger (the run's seconds divided by its passengers) is roughly what each decision costs. Even the slowest case here is about a tenth of a second.

Delivered passengers drop out of every calculation, so the cost depends on **how many are waiting per elevator**, not on how many have been served. While the elevators keep up, every method grows in step with the number of passengers. Forecast slows down when a queue builds: everyone at tick 0, or more traffic than the elevators can carry. Forecast / request order is slow for the same reason: request order lets the queue grow. The timing runs, with their inputs, are in `experiments/data/`.

**Big O.**

- **n**: passengers one elevator holds now (aboard plus waiting)
- **r**: riders aboard one elevator (at most its capacity)
- **E**: elevators
- **N**: total passengers across all elevators

One forecast plays an elevator forward stop by stop on a copy. It costs O(n²), or O(n³) at worst for direction-based, which can stop at a full elevator's waiting passengers on every sweep.

| Method | Time per new passenger | Time per tick, per elevator | Memory |
| --- | --- | --- | --- |
| Round robin | O(1) | | O(1) |
| Nearest elevator | O(E · r) | | O(1) |
| Forecast assignment | O(E · n²): 2 forecasts per elevator | | O(n) per forecast |
| Request order | O(1) | O(r) | O(1) |
| Direction-based | O(1) | O(n) | O(E) |
| Forecast service order | O(n³): n + 1 forecasts | O(r) | O(N) |
| Forecast for both | O(E · n³) | O(r) | O(N) |

Memory leaves out the output itself: the position log and each passenger's recorded times.

## What I would improve with more time

- **Stop time.** Stops take no time here. A stop-time setting would show whether the ranking of methods holds when stops cost something.
- **Make forecast faster without changing its results.** It is the best method and the slowest. In prototypes with identical results, reusing the placement forecast assignment already worked out, and dropping a position as soon as it breaks K or can no longer win, made it about 2 to 3 times faster. Going below n³ would mean trying fewer positions, which changes the results: a design choice to measure, not a free speed-up.
- **Express elevators** (bonus). Elevators that serve only some floors. They gain nothing while stops are free, so they come after stop time.
- **Smarter forecast pickups.** Let passengers later in the pickup order board on the way, and let each arrival reorder those already waiting, still within K.
- **Zones that share capacity.** Each elevator prefers one part of the building, but a busy zone can borrow from a quiet one, as in Otis's SuperGroup.
- **Parking idle elevators** where requests have recently come from, measuring the shorter waits against the extra empty travel.
- **Energy.** Prefer elevators already running, or add energy as a cost in the forecast.
- **Traffic that changes during the day**, such as a morning up-peak turning into an evening down-peak in one run.
- **Direction-based with the same K**, to bound its wait.
- **More measurement and charts:** queue length and the oldest wait over time, results by floor or direction, and average against longest wait as K changes.

## Time spent

About 1.5 to 2 days.

## Files

| File | Contents |
| --- | --- |
| `main.py` | command line: read the CSV, run, write the log, print statistics |
| `simulation.py` | `simulate()`, input checks and the tick loop |
| `assignment.py` | round robin, nearest elevator, forecast assignment |
| `service_order.py` | request order, direction-based, forecast service order, and the forecast itself |
| `elevator.py`, `passenger.py` | an elevator and a passenger |
| `test_*.py` | unit tests |
| `experiments/traffic.py` | seeded synthetic traffic, 10 types |
| `experiments/compare.py` | every method pair on every traffic type; writes `results.md` |
| `experiments/check.py` | checks every rule from the outputs alone |
| `experiments/data/` | raw data from the independent checks |
| `requests.csv` | the assignment's example input |
