# Elevator simulation

A discrete-time simulation of a destination-dispatch elevator system. Each passenger gives their origin and destination when they call; the system immediately assigns them an elevator, and the simulation ticks forward one floor of travel at a time.

The elevator system makes two separate decisions:

- **Elevator assignment:** which elevator takes a new passenger. Made once, when the request arrives, and never changed (the hall panel has already told the passenger which elevator to use).
- **Service order:** which waiting passenger an elevator picks up next. Drop-offs are not a choice: riders get off when the elevator reaches their floor.

Each decision has three methods, chosen before a run. The default is forecast for both.

## Results in short

Forecast for both decisions (the default) beats the best simple method's average total time on every traffic type tried, tying only on bursts, and cuts the longest wait by roughly 30 to 70% on every type but one (stream_long, unchanged). Default building (100 floors, 4 elevators, capacity 10), 5 seeds each, times in ticks:

| Traffic | Simplest method: round robin / request, average | Best simple method, average | Forecast / forecast, average | Longest wait: best simple → forecast |
| --- | ---: | ---: | ---: | ---: |
| up_peak | 440 | 266 (round robin / direction) | **222** | 506 → **361** |
| down_peak | 1,176 | 215 (nearest / direction) | **136** | 614 → **236** |
| lunch | 914 | 132 (nearest / direction) | **90** | 395 → **123** |
| interfloor | 909 | 108 (nearest / direction) | **71** | 302 → **137** |
| hot_floor | 736 | 89 (nearest / direction) | **57** | 291 → **111** |
| bursts | 293 | 145 (round robin / direction) | **145** | 348 → **243** |
| sparse | 113 | 66 (nearest / direction) | **59** | 123 → **87** |
| stream_long | 99 | 8 (nearest / direction) | **7** | 98 → **98** |
| heavy | 2,984 | 201 (round robin / direction) | **150** | 659 → **318** |
| light | 214 | 76 (nearest / direction) | **68** | 159 → **104** |

"Best simple method" is the best of round robin or nearest elevator with request order or direction-based, chosen separately for each traffic type, so forecast is compared with the strongest simple choice each time. The traffic is synthetic and seeded (`experiments/traffic.py` describes each type).

- **Elevator assignment is the bigger lever.** With direction-based service, switching the assignment from round robin to forecast cuts the interfloor average from 128 to 73; switching the service order from direction-based to forecast then moves it only to 71.
- **Forecast's service order earns its place on the worst case.** With forecast assignment, moving from direction-based to forecast service cuts the longest wait in heavy traffic from 467 to 318 and in down-peak from 490 to 236, because K stops anyone being passed over again and again.
- **Request order collapses under load** (heavy traffic: average 2,984 against 150): an elevator carries about one rider per trip.
- **Where forecast helps least:** lobby bursts (a tie with round robin / direction-based, since spreading people evenly is already about as good as it gets) and very light traffic, where elevators are rarely shared (sparse: 59 against 66; stream_long: 7 against 8).
- **The cost is running time:** the 50 forecast / forecast runs behind the table take about 80 seconds, against under a second for any simple pair (see Performance).

Reproduce every number: `python3 experiments/compare.py` (about 3 minutes) writes all tables, for this building and the 30-floor building used below, to [`experiments/results.md`](experiments/results.md).

## How I know it's correct

- **Unit tests** (`python3 -m unittest`, 70 tests): every rule and every method on small examples worked out by hand, with exact expected times and positions, including the assignment's sample input.
- **The rules are enforced in the code.** An elevator refuses to board someone at another floor, over capacity, or going against its riders, and refuses to reverse with riders aboard. Any method that tried would stop the run with an error.
- **An outside check of every rule** (`python3 experiments/check.py`, about 80 seconds): 270 runs (10 traffic types, all 9 method pairs, 3 buildings including capacity 1), checked using only what a run outputs: the position log and each passenger's times. In every run: every elevator starts at floor 1, stays in the building and moves at most one floor per tick; every passenger is delivered, never picked up before asking, and picked up and dropped off exactly where their elevator was logged at those ticks; no elevator carries more than its capacity or moves against a rider aboard. The checker was itself tested by corrupting runs on purpose (a jump of 3 floors, an early pickup, a lower capacity, a reversed rider), and it caught each one.
- **No peeking ahead:** for every run, the check reruns with all requests after a midpoint T removed; the position log up to T must be identical, and is, so no decision depends on a request that has not been made yet.
- **The fairness limit holds:** in every forecast service-order run, nobody is dropped off more than K = 80 ticks after their first forecast. The check fails, as it should, when the limit is switched off underneath it.
- **Forecasts match what happens:** with no later requests, every first forecast equals the actual drop-off time (`test_forecast.py`), because forecasts run the same code as the simulation on a copy.
- **Refactors changed nothing:** every simplification and speed-up was checked against the previous version on 1,490 runs, comparing each passenger's elevator, pickup and drop-off time and the whole position log.

## How to run

Python 3.10 or later, standard library only.

```
python3 main.py requests.csv
python3 main.py requests.csv --elevators 2 --assignment nearest --service-order direction
python3 main.py requests.csv --service-order forecast --allowed-delay 20
python3 -m unittest
```

| Option | Default | Meaning |
| --- | --- | --- |
| `--floors` | 100 | floors are numbered 1 to n |
| `--elevators` | 4 | number of elevators; all start at floor 1 |
| `--capacity` | 10 | passengers per elevator |
| `--assignment` | `forecast` | `round-robin`, `nearest` or `forecast` |
| `--service-order` | `forecast` | `request`, `direction` or `forecast` |
| `--allowed-delay` | 80 | forecast service order only: the fairness limit K in ticks, or `none` |
| `--positions-out` | `positions.csv` | position log file |

The input CSV has the columns `time,id,source,dest` (spaces around names and any case are accepted). Output:

- **Position log** (`positions.csv`): one row per tick from 0, `time,elevator_0,elevator_1,...`, every elevator's floor.
- **Statistics** printed at the end: minimum, median, average, 95th percentile and maximum wait, travel and total time; who waited longest, for which elevator; and how many passengers each elevator served and how many floors it moved. For the sample input with 2 elevators:

```
Wait time    min     0   median     0.0   average    14.33   95th percentile    43   max    43
Travel time  min    19   median    36.0   average    35.00   95th percentile    50   max    50
Total time   min    36   median    50.0   average    49.33   95th percentile    62   max    62
Longest wait: passenger3 (20 to 1) waited 43 ticks for elevator 1
Elevator 0: 1 passenger, moved 50 floors
Elevator 1: 2 passengers, moved 72 floors
```

From Python, the same run is one call on a list of requests:

```python
from simulation import simulate

positions, passengers = simulate(
    [(0, 'passenger1', 1, 51), (0, 'passenger2', 1, 37), (10, 'passenger3', 20, 1)],
    elevators=2, assignment='nearest', service_order='direction',
)
```

`simulate` checks every request and setting, builds fresh passengers and elevators on each call (so one list can be run with every method), and returns the positions and the passengers with their times.

## How a tick works

Each tick, in this order:

1. **Drop off** riders whose destination is the elevator's floor.
2. **Release** the requests made at this tick, in file order, and assign each one to an elevator straight away. Requests from later ticks are not looked at.
3. **Pick up** waiting passengers at each elevator's floor, as the service order and capacity allow.
4. **Log** every elevator's floor.
5. **Stop** once every request has been made and every passenger delivered.
6. **Move** each elevator one floor toward the target its service order chose.

Wait time is pickup minus request, travel time is drop-off minus pickup, total time is wait plus travel.

## The methods, with pros and cons

Numbers below are measured on synthetic traffic (seeded, reproducible), not real building data. "30-floor building" means 30 floors, 4 elevators, capacity 4; "default building" means 100 floors, 4 elevators, capacity 10.

### Elevator assignment

**Round robin.** Elevators take turns: 0, 1, 2, 3, 0, ...

- Pros: simplest possible; spreads passengers evenly, so a lobby burst never piles into one elevator (20 lobby requests: 5 / 5 / 5 / 5, average total 31).
- Cons: ignores where the elevators are and what they are doing; an elevator at the far end can be sent while another is next door, and a full elevator gets its turn like any other. On spread-out traffic it is clearly worse than the other two (30-floor building, interfloor with direction-based: average total 36, against 27 for nearest elevator and 20 for forecast).

**Nearest elevator.** The elevator that could pick the passenger up soonest. An elevator's target is its riders' farthest destination, or, with nobody aboard, its first assigned pickup; an elevator with neither is idle. Plain distance if the elevator is idle, or if the passenger is ahead and going the way the elevator is going; otherwise the distance to its target and back. Equally close elevators: the least busy, then the lowest number.

- Pros: cheap; uses each elevator's position and the way it is already committed to go, as real nearest-elevator dispatching does. Better than round robin on spread-out traffic (30-floor building, interfloor with direction-based: average total 27 against 36).
- Cons: counts distance only, not the passengers already waiting for an elevator or its capacity. In a lobby burst every elevator at the lobby is 0 floors away, so it keeps choosing the same elevator: 20 / 0 / 0 / 0, average total 83 against round robin's 31. So it loses to round robin on lobby-heavy and bursty traffic (up-peak with direction-based: 110 against 86; bursts: 143 against 54). Being on the way says nothing about how busy an elevator already is: in bursts the chosen elevator already held about 12 passengers, aboard or waiting, at capacity 4. A full elevator still counts as "on the way" (a full elevator 4 floors away beat an idle elevator 15 floors away; the passenger then arrived at tick 99 instead of 20). Under request order its "on the way" estimate is also wrong, because the elevator will not pick up a later passenger before earlier ones: in one case it estimated 3 floors and the passenger waited 73 ticks.

**Forecast assignment.** For each elevator, forecast everyone's drop-off times with and without the new passenger, playing the elevator forward with the same service order the elevators follow, and choose the elevator whose combined total time goes up the least.

- Pros: sees what distance cannot (waiting passengers, capacity, detours, the service order's own choices); best average in every traffic type measured (30-floor building, interfloor: about 20 against 36 for round robin; the lobby burst: 8 / 4 / 4 / 4, average 26). Forecasts match what actually happens, because they use the same rules.
- Cons: the slowest method: two forecasts per elevator for every request, and with the forecast service order each forecast also tries every position (see Performance). It only knows requests already made, so a choice that is best now can be worse later: in the sample input, splitting passenger1 and passenger2 across two elevators costs nothing at tick 0 but leaves no idle elevator for passenger3 at tick 10 (62 instead of 38). Its result is only as good as the service order it forecasts with: under request order it can only pick the least bad elevator for a slow rule.

### Service order

**Request order.** First come, first served: an elevator picks people up strictly in the order they asked. Several riders can share the elevator, but nobody who asked later boards first.

- Pros: the simplest notion of fair; nobody can be passed over, so nobody waits forever.
- Cons: under load it carries about one rider per trip, because the next person in line is rarely at the same floor going the same way. Heavy traffic on the 30-floor building: average total 770, against 81 for direction-based; more capacity barely helps (capacity 1, 4, 10: 877, 770, 767). Fair in order, but people wait longer on average than under any other rule.

**Direction-based.** Keep going one way, pick up anyone on the way who is going that way and fits, and turn around only when the elevator is empty with nothing left ahead.

- Pros: efficient and easy to picture; picks people up on the way for free (one elevator, Alice 3 → 20, Bob 2 → 10, Carol 15 → 4: combined total 63 against 125 for request order).
- Cons: no memory of who asked first. A passenger can be passed again and again, but only because the elevator arrives full, never because of direction: anyone waiting counts as someone ahead, so the elevator always comes back past them going their way. With one elevator of capacity 1 and a steady stream filling it below her floor, one passenger's wait grew by 14 ticks per extra stream passenger (350, 700, 1,400, 2,800); with capacity 10 the same passenger waited 4 ticks however long the stream ran. Under heavy traffic it has the worst longest wait of the efficient rules (30-floor building with round robin: 389 ticks, against 282 for forecast with K = 0).

**Forecast service order.** Each elevator keeps a pickup order. When a passenger is assigned, they are tried at every position in it; each version is played forward, and the one with the lowest combined total time is kept, as long as nobody already assigned arrives more than **K** ticks after their first forecast (the allowed delay). Passengers already in the order keep their order among themselves.

- Pros: one dial for fairness against efficiency. K = 0 never delays anyone already waiting but still allows free pickups on the way; larger K trades a bounded delay for a better average. The limit is a guarantee: in about 5,000 stress runs nobody arrived later than first forecast + K. Its main win over direction-based is the worst case (heavy traffic with forecast assignment: longest wait 118 at K = 0 against 238).
- Cons: slower than the simple orders. Only the newcomer's position is chosen (n + 1 tries instead of every order), so it is the best of the positions tried, not the best possible order, and on average it is roughly level with direction-based (with round robin and K = 0 it can even be a little worse: interfloor 43 against 36). Boarding follows the pickup order strictly, so someone later in the order is not picked up on the way. A larger K is not always better on average (up-peak with forecast assignment: 26.6 at K = 0, 27.2 at K = 20). K is in ticks, so the best value depends on the building.

### Why forecast, and not a patched simple method

The simple methods are kept as they are, on purpose: each has one clear flaw, and each flaw has an obvious patch. Every patch is a guess about the future of an elevator; forecast replaces the guess with a forecast made by the same rules the elevator will follow.

| Method | Its flaw | The obvious patch | Why the patch is still a guess |
| --- | --- | --- | --- |
| Round robin | ignores where elevators are | skip elevators that are far or full | then it is no longer taking turns, and "far" and "full" are judged only from now |
| Nearest elevator | ignores waiting passengers and capacity | skip an elevator whose riders plus waiting passengers fill it | counts say how full an elevator is now, not when it reaches you: riders may get off first, and some waiting passengers are behind the elevator or going the other way |
| Request order | about one rider per trip under load | let people on the way board too | that is direction-based, which can pass someone again and again |
| Direction-based | can pass someone again and again when the elevator arrives full | keep a place free for anyone who has waited too long | it bounds the wait, but still cannot see the cost of each choice |

Forecast answers each one by playing the elevator forward: it sees when an elevator will actually reach you, who will be aboard, and what each choice costs everyone, and K limits how much any one passenger can be made to pay. The price is computing time, which is why making forecast fast without changing its results is the main improvement listed below.

### Choosing K

Trying many values on the default building (7 traffic types, K from 0 to 320 and no limit, round robin and forecast assignment) showed:

- the average improves with K and flattens at about 80, within about 1% of no limit;
- the longest wait is lowest around 80 and rises beyond it (a long trip among short trips: about 192 ticks up to K = 80, 401 with no limit).

So the default is **K = 80**. `--allowed-delay none` removes the limit, and with it the guarantee.

### Can anyone wait forever?

- **Request order:** no. Your wait depends only on the finite number of passengers ahead of you.
- **Direction-based:** there is no upper bound while a stream keeps filling the elevator before it reaches you. With a finite input everyone is still served.
- **Forecast:** no, while K is set: nobody arrives more than K ticks after their first forecast. K = 80 by default.

### Starvation, capacity and overload: which decision is responsible

| Question | Decided by |
| --- | --- |
| Which elevator a passenger waits for, and how crowded it gets | elevator assignment |
| Whether people who asked later can keep being picked up first | service order |
| How many can ride at once | capacity, a building setting |

Starvation needs both: competition in your elevator (assignment controls how much) and a rule that lets others go ahead of you (only the service order controls this). Capacity is the mechanism, not a separate cause: direction-based passes someone only when the elevator arrives full. A good assignment can keep a stream away from you (a long trip among short trips: longest wait 28 with nearest elevator or forecast assignment, against 326 with round robin and forecast with no limit), but it cannot guarantee it, because your elevator is fixed and later requests are unknown. Only the service order, with K, can.

Overload is different: when requests arrive faster than the elevators can carry them, everyone's wait grows, whatever the methods. Better methods slow the backlog; more elevators or more capacity fix it.

### Does the elevator assignment check whether an elevator has room?

| Elevator assignment | Checks room? | How |
| --- | --- | --- |
| Round robin | no | takes turns whatever the elevators hold |
| Nearest elevator | no | distance only; a full elevator still counts as picking you up on the way, and the passenger count only breaks ties |
| Forecast | yes, along the whole route | it plays each elevator forward with the service order, which boards people only if there is room, so an elevator that will be full when it reaches you looks worse |

Example: elevator 0 at floor 1 is full (capacity 2, two riders to floor 50), elevator 1 is idle at floor 20, and a passenger asks for 5 → 10. Nearest elevator picks elevator 0 (4 floors, "on the way"); it passes her full, and she arrives at tick 99. Forecast gives 99 in elevator 0 and 20 in elevator 1, and picks elevator 1.

Capacity limits how many ride at once, not how many can be assigned: every passenger always gets an elevator; a full elevator only means waiting until it has room.

## Assumptions and simplifications

- One tick is one floor of travel. Boarding and leaving take no time (stop time 0).
- Floors are numbered from 1. All elevators start at floor 1 and have the same capacity.
- An elevator never reverses with riders aboard, and only passengers going the riders' way may board.
- An elevator with nothing to do stays where it is.
- The assigned elevator never changes, and a destination cannot change.
- Requests in the same tick are handled in file order. Unsorted input is sorted by time.
- Requests are rejected with a clear message if a floor is out of range, source equals destination, a time is negative or not a whole number, or an id is blank or repeated.
- There is no tick limit: the clock runs one tick at a time until everyone is delivered, as required. A request at tick 1,000,000,000 means a log of about a billion rows (roughly 16 GB) and hours of running.

## Performance

The simple methods are fast: 20,000 passengers in under a second. Forecast costs more, because every new passenger is tried at every position in an elevator's pickup order and every elevator is played forward. Forecasts copy only the elevator being forecast, and jump straight to the next floor where something can happen, since no new requests arrive during a forecast; the results are identical to playing every tick, checked on 1,490 cases.

Measured on the default building (100 floors, 4 elevators, capacity 10), random traffic:

| Passengers | Methods | Seconds |
| --- | --- | --- |
| 1,000 spread over time | forecast / forecast | 1.1 |
| 5,000 spread over time | forecast / forecast | 7.2 |
| 20,000 spread over time | forecast / forecast | 26 |
| 5,000 spread over time | forecast / request order | 34 |
| 500 all at tick 0 | forecast / forecast | 40 |
| 20,000 spread over time | nearest / direction-based | 0.4 |

Forecast slows down when many passengers wait for the same elevator at once (everyone at tick 0), because trying every position grows with the square of the number waiting.

## What I would improve with more time

Most important first.

- **Stop time.** Stops take no time here, following the assignment's model of one tick per floor. In real buildings every stop costs time, which is exactly where grouping passengers by destination pays off. A stop-time setting (0 by default) would show whether the ranking of methods still holds when stops cost something.
- **Express elevators** (from the bonus list). Some elevators would serve only certain floors, for example the lobby and the top third. With stops taking no time, skipping floors saves nothing on its own; any gain comes from keeping long trips out of the local elevators. So it belongs together with stop time, and should be measured both for the passengers it serves and for those left to the local elevators.
- **Smarter forecast pickups.** Each new passenger is tried at every position in the pickup order, but passengers already waiting keep their order among themselves, and boarding follows the order strictly, so someone later in the order is not picked up when the elevator passes them. Letting passengers board on the way, and letting each arrival reorder those already waiting (still within K), could lower the average further.
- **Zones that share capacity.** Prefer each elevator for one part of the building, but let a busy zone borrow an elevator from a quiet one, as Otis describes for its SuperGroup system. Measure the passengers in the lending zone as well as those helped.
- **Parking idle elevators.** Send an idle elevator toward where requests have recently come from (the lobby in the morning, upper floors in the evening). It shortens waits but adds empty travel, so measure both.
- **A running elevator or an idle one, and energy.** On a tie, sending an elevator that is already running instead of starting an idle one helped lobby bursts with forecast assignment, but hurt nearest elevator, which cannot see the cost; it was not adopted. Fewer elevators moving also means fewer starts, stops and empty trips, so less energy: an energy-aware rule, or energy as a cost in the forecast, would be the next step.
- **Traffic that changes during the day.** A morning up-peak turning into an evening down-peak in one run, to see how each method copes with the shift, still without letting any method see requests before they are made.
- **Direction-based with the same K.** Once someone has waited K ticks, keep a place free for them on the way. Since capacity is its only way to pass someone over, this would bound its wait.
- **More measurement.** Queue length and the oldest wait over the course of a run, empty against loaded travel, and results by group (by floor or by direction) so an average cannot hide a group that does badly; and charts: average against longest wait as K changes, and the spread of wait times.
- **Idle stretches.** When every elevator is idle until the next request, log those ticks in bulk and store unchanged rows compactly; the clock still ticks one at a time.

## Time spent

To be filled in.

## Files

| File | Contents |
| --- | --- |
| `main.py` | command line: read the CSV, run, write the log, print statistics |
| `simulation.py` | `simulate()`, input checks, and the tick loop |
| `assignment.py` | round robin, nearest elevator, forecast assignment |
| `service_order.py` | request order, direction-based, forecast service order, and the shared forecast |
| `elevator.py`, `passenger.py` | an elevator and a passenger |
| `test_*.py` | unit tests (`python3 -m unittest`) |
| `experiments/traffic.py` | seeded synthetic traffic: 10 types |
| `experiments/compare.py` | every method pair on every traffic type; writes `experiments/results.md` |
| `experiments/check.py` | checks every rule from the outputs alone, on 270 runs |
| `requests.csv` | the assignment's example input |
