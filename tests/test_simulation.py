import unittest

from assignment import RoundRobin
from elevator import Elevator
from passenger import Passenger
from service_order import RequestOrder
from simulation import Simulation, check_requests, simulate

SAMPLE = [(0, 'passenger1', 1, 51), (0, 'passenger2', 1, 37), (10, 'passenger3', 20, 1)]


def run(passengers, elevator_count=1, capacity=10):
    """Run a building with round robin and request order. Returns the position log."""
    elevators = [Elevator(id=i, capacity=capacity) for i in range(elevator_count)]
    return Simulation(passengers, elevators, RoundRobin(), RequestOrder()).run()


def floors(positions, elevator=0):
    """One elevator's floor at every tick."""
    return [row[elevator] for row in positions]


class SimulateTest(unittest.TestCase):
    def test_runs_the_sample_requests(self):
        positions, passengers = simulate(SAMPLE)
        self.assertEqual([p.id for p in passengers], ['passenger1', 'passenger2', 'passenger3'])
        self.assertEqual([p.total_time for p in passengers], [50, 36, 38])
        self.assertEqual(len(positions), 51)  # ticks 0 to 50
        self.assertEqual(positions[0], [1, 1, 1, 1])

    def test_the_same_list_can_be_run_again_with_other_methods(self):
        first = [p.total_time for p in simulate(SAMPLE, elevators=1)[1]]
        again = [p.total_time for p in simulate(SAMPLE, elevators=1)[1]]
        forecast = [p.total_time for p in simulate(SAMPLE, elevators=1, assignment='forecast', service_order='forecast')[1]]
        self.assertEqual(first, again)
        self.assertEqual(len(forecast), 3)

    def test_a_late_request_is_served(self):
        # No tick limit: a valid request at any time is served.
        positions, passengers = simulate([(1_000_000, 'late', 1, 2)], elevators=1)
        self.assertEqual(passengers[0].total_time, 1)
        self.assertEqual(len(positions), 1_000_002)

    def test_invalid_settings_are_rejected(self):
        cases = {
            'floors': dict(floors=0),
            'elevators': dict(elevators=0),
            'capacity': dict(capacity=1.5),
            'assignment must be one of': dict(assignment='fastest'),
            'service order must be one of': dict(service_order='random'),
            'allowed delay': dict(service_order='forecast', allowed_delay=-1),
        }
        for message, settings in cases.items():
            with self.subTest(message), self.assertRaisesRegex(ValueError, message):
                simulate(SAMPLE, **settings)

    def test_a_request_must_have_four_fields(self):
        with self.assertRaisesRegex(ValueError, 'request 2: expected'):
            simulate([(0, 'a', 1, 2), (0, 'b', 1)])


class CheckRequestsTest(unittest.TestCase):
    def test_valid_requests_pass(self):
        check_requests([Passenger('a', 0, 1, 10)], floors=10)

    def test_each_rule_is_enforced(self):
        cases = {
            'needs an id': [Passenger('  ', 0, 1, 2)],
            'used more than once': [Passenger('a', 0, 1, 2), Passenger('a', 1, 2, 3)],
            'whole numbers': [Passenger('a', 0.5, 1, 2)],
            'negative': [Passenger('a', -1, 1, 2)],
            'outside floors': [Passenger('a', 0, 1, 11)],
            'same floor': [Passenger('a', 0, 4, 4)],
        }
        for message, passengers in cases.items():
            with self.subTest(message), self.assertRaisesRegex(ValueError, message):
                check_requests(passengers, floors=10)



class RequestOrderTest(unittest.TestCase):
    def test_two_riders_aboard_together_in_request_order(self):
        alice = Passenger('alice', request_time=0, source=3, destination=20)
        bob = Passenger('bob', request_time=0, source=5, destination=10)
        positions = run([alice, bob])

        self.assertEqual(floors(positions), list(range(1, 21)))
        self.assertEqual((alice.pickup_time, alice.drop_off_time), (2, 19))
        self.assertEqual((bob.pickup_time, bob.drop_off_time), (4, 9))

    def test_a_later_passenger_on_the_way_is_not_picked_up_first(self):
        alice = Passenger('alice', request_time=0, source=3, destination=20)
        bob = Passenger('bob', request_time=0, source=2, destination=10)
        positions = run([alice, bob])

        # Passes Bob at 2 (Alice is first), delivers Alice at 20, comes back for Bob.
        self.assertEqual(floors(positions), list(range(1, 21)) + list(range(19, 1, -1)) + list(range(3, 11)))
        self.assertEqual((alice.pickup_time, alice.drop_off_time), (2, 19))
        self.assertEqual((bob.pickup_time, bob.drop_off_time), (37, 45))
        self.assertEqual(bob.total_time, 45)

    def test_walkthrough_from_the_design_discussion(self):
        alice = Passenger('alice', request_time=0, source=3, destination=5)
        bob = Passenger('bob', request_time=1, source=2, destination=1)
        positions = run([alice, bob])

        self.assertEqual(floors(positions), [1, 2, 3, 4, 5, 4, 3, 2, 1])
        self.assertEqual((bob.pickup_time, bob.wait_time, bob.total_time), (7, 6, 7))

    def test_full_elevator_delivers_its_riders_before_coming_back(self):
        alice = Passenger('alice', request_time=0, source=3, destination=20)
        bob = Passenger('bob', request_time=0, source=5, destination=10)
        run([alice, bob], capacity=1)

        # The elevator passes Bob at 5 while full, delivers Alice at 20, then returns.
        self.assertEqual((bob.pickup_time, bob.drop_off_time), (34, 39))

    def test_passengers_at_the_same_floor_board_together(self):
        alice = Passenger('alice', request_time=0, source=1, destination=4)
        bob = Passenger('bob', request_time=0, source=1, destination=6)
        run([alice, bob])
        self.assertEqual((alice.pickup_time, bob.pickup_time), (0, 0))
        self.assertEqual((alice.drop_off_time, bob.drop_off_time), (3, 5))


class ClockTest(unittest.TestCase):
    def test_idle_ticks_are_logged_until_the_first_request(self):
        alice = Passenger('alice', request_time=3, source=1, destination=2)
        positions = run([alice])
        self.assertEqual(floors(positions), [1, 1, 1, 1, 2])
        self.assertEqual((alice.wait_time, alice.total_time), (0, 1))

    def test_no_passengers_logs_only_tick_zero(self):
        self.assertEqual(run([], elevator_count=2), [[1, 1]])

    def test_every_elevator_is_logged_every_tick(self):
        alice = Passenger('alice', request_time=0, source=3, destination=4)
        bob = Passenger('bob', request_time=0, source=2, destination=3)
        positions = run([alice, bob], elevator_count=2)  # round robin: Alice to elevator 0, Bob to elevator 1
        self.assertEqual(positions, [[1, 1], [2, 2], [3, 3], [4, 3]])

    def test_unsorted_input_is_released_by_request_time(self):
        later = Passenger('later', request_time=2, source=1, destination=2)
        first = Passenger('first', request_time=0, source=1, destination=2)
        run([later, first], elevator_count=2)  # round robin: first request goes to elevator 0
        self.assertEqual((first.assigned_elevator, later.assigned_elevator), (0, 1))


if __name__ == '__main__':
    unittest.main()
