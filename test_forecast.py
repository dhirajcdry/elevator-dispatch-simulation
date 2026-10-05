import unittest

from assignment import RoundRobin
from elevator import Elevator
from passenger import Passenger
from service_order import Forecast, RequestOrder, predict_finish_times
from simulation import Simulation


def run(passengers, service_order, capacity=10):
    """One elevator at floor 1."""
    Simulation(passengers, [Elevator(id=0, capacity=capacity)], RoundRobin(), service_order).run()


def alice_and_bob():
    # Scenario 13: Alice asks first for a long trip down; Bob's 1-floor trip is near the elevator.
    alice = Passenger('alice', request_time=0, source=20, destination=1)
    bob = Passenger('bob', request_time=0, source=2, destination=1)
    return alice, bob


class ForecastTest(unittest.TestCase):
    def test_no_limit_serves_the_short_trip_first(self):
        alice, bob = alice_and_bob()
        run([alice, bob], Forecast(allowed_delay=None))
        self.assertEqual((alice.total_time, bob.total_time), (40, 2))  # combined 42

    def test_default_allowed_delay_is_80(self):
        self.assertEqual(Forecast().allowed_delay, 80)

    def test_allowed_delay_zero_keeps_alice_on_time(self):
        alice, bob = alice_and_bob()
        run([alice, bob], Forecast(allowed_delay=0))
        self.assertEqual((alice.total_time, bob.total_time), (38, 38))  # Bob picked up on the way down

    def test_bob_goes_first_once_the_allowed_delay_covers_alices_two_ticks(self):
        for allowed_delay, expected in [(1, (38, 38)), (2, (40, 2))]:
            alice, bob = alice_and_bob()
            run([alice, bob], Forecast(allowed_delay=allowed_delay))
            self.assertEqual((alice.total_time, bob.total_time), expected, f'allowed delay {allowed_delay}')

    def test_on_the_way_pickup_is_allowed_at_zero(self):
        # Bob 5 -> 10 is on Alice's way: picking him up costs her nothing.
        alice = Passenger('alice', request_time=0, source=3, destination=20)
        bob = Passenger('bob', request_time=0, source=5, destination=10)
        run([alice, bob], Forecast(allowed_delay=0))
        self.assertEqual((alice.pickup_time, alice.drop_off_time), (2, 19))
        self.assertEqual((bob.pickup_time, bob.drop_off_time), (4, 9))

    def test_predictions_match_what_happens(self):
        # With nobody pushed back, every first prediction is the actual finish.
        alice, bob = alice_and_bob()
        forecast = Forecast(allowed_delay=0)
        run([alice, bob], forecast)
        self.assertEqual(forecast.first_predicted_finish, {'alice': alice.drop_off_time, 'bob': bob.drop_off_time})

    def test_first_prediction_is_kept_when_a_newcomer_pushes_back(self):
        alice, bob = alice_and_bob()
        forecast = Forecast(allowed_delay=None)
        run([alice, bob], forecast)
        self.assertEqual(forecast.first_predicted_finish['alice'], 38)
        self.assertEqual(alice.drop_off_time, 40)

    def test_predict_finish_times_leaves_the_real_elevator_unchanged(self):
        elevator = Elevator(id=0, capacity=10)
        alice, bob = alice_and_bob()
        # Bob assigned first, so request order serves Bob, then Alice.
        elevator.assign(bob)
        elevator.assign(alice)
        predicted_finish = predict_finish_times(elevator, RequestOrder(), time=0)
        self.assertEqual(predicted_finish, {'bob': 2, 'alice': 40})
        self.assertEqual((elevator.floor, elevator.waiting, elevator.riders), (1, [bob, alice], []))
        self.assertIsNone(alice.pickup_time)


if __name__ == '__main__':
    unittest.main()
