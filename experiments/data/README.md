# Check data

Raw results from independent checks of this repo, one row per run. All traffic is synthetic and seeded.

| File | Rows | What it is |
| --- | ---: | --- |
| `perf_runs.csv` | 736 | Performance: wall time, peak memory and results for every method pair, 100 to 20,000 passengers, 20 to 500 floors, 1 to 10 elevators, spread out or all at tick 0 |
| `perf_inputs/` | 65 files | The exact request CSVs behind `perf_runs.csv` (run any of them with `python3 main.py`) |
| `perf_gen.py` | | The generator for those inputs: `python3 perf_gen.py interfloor 2000 spread 100 1 out.csv` |
| `fuzz_runs.csv` | 3,888 | Rule checks: 18 traffic shapes, floors 2 to 100, 1 to 10 elevators, capacity 1 to 1,000, K = 0, 5, 80 and none. Every run passed every check |
| `quality_runs.csv` | 2,304 | Method comparison: average, median, 95th percentile and longest wait and total, rule and K checks, forecast against actual, no-peeking check |
| `starvation.csv` | 269 | A long trip among a stream of short trips, by stream length: how long the long trip waits under each method |
| `charts.json` | | The data behind the README charts, written by `python3 experiments/chart_data.py`: every method pair and every allowed delay on every traffic type (5 seeds), and each passenger's times in heavy traffic |

## Timing

Measured on an Apple M4 Pro (24 GB, Python 3.13.1), before the faster passenger copy that came next, which makes every forecast pair about 1.6 times faster with identical results. Results do not change; only `wall_s` would be smaller now.

In `perf_runs.csv`, `concurrent_workers` = 4 means four runs shared the machine, which made slow runs up to 3.4 times slower. The rows with experiment `growth_spread_seq`, `growth_tick0_seq` and `fixes` ran alone; use those for timings. The `fixes` rows also time three speed-up prototypes (`impl` = `fast_a`, `fast_b`, `fast_c`), not part of this repo.

## perf_runs.csv columns

| Column | Meaning |
| --- | --- |
| experiment | which sweep the run belongs to |
| impl | `repo`, or a speed-up prototype (only in `fixes`) |
| workload | `{pattern}_n{passengers}_{arrival}_f{floors}_s{seed}`; the input is `perf_inputs/{workload}.csv` |
| passengers, arrival, pattern, floors, seed | the traffic: `spread` is a gap of 1 to 3 ticks between requests, `tick0` is everyone at tick 0 |
| elevators, capacity, assignment, service_order, allowed_delay | the building and the method pair |
| ticks | rows in the position log |
| wall_s | seconds inside `simulate()`; `>N` if it did not finish |
| read_s, write_s, log_bytes | reading the input, and writing the position log (only the long idle runs) |
| peak_mb | peak memory of the process, including about 20 MB for Python itself |
| finished, timeout_s | `yes` or `timed out`, and the time limit |
| avg/p95/max wait and total | in ticks |
| result_hash | a hash of the whole position log and every passenger's elevator, pickup and drop-off: equal hash, identical run |
