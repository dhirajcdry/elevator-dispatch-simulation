import unittest

from passenger import Passenger
from simulation import check_requests, simulate

SAMPLE = [(0, 'passenger1', 1, 51), (0, 'passenger2', 1, 37), (10, 'passenger3', 20, 1)]


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


if __name__ == '__main__':
    unittest.main()
