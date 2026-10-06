import unittest

from assignment import ForecastAssignment
from elevator import Elevator
from passenger import Passenger
from service_order import DirectionBased, Forecast, RequestOrder, forecast_drop_off_times


def choose_for_bob(bob_destination, service_order):
    """Scenarios 10 and 11: elevator A at 1 already has Alice (30 -> 31); elevator B is idle at 50.
    Capacity 1. Bob asks at 5 at tick 0. Returns the chosen elevator and its forecast drop-off times."""
    elevators = [Elevator(id=0, capacity=1, floor=1), Elevator(id=1, capacity=1, floor=50)]
    alice = Passenger('alice', request_time=0, source=30, destination=31)
    elevators[0].assign(alice)
    service_order.plan_pickup(elevators[0], alice, time=0)

    bob = Passenger('bob', request_time=0, source=5, destination=bob_destination)
    elevator = ForecastAssignment(service_order).choose(elevators, bob, time=0)
    return elevator.id, forecast_drop_off_times(elevator, service_order, time=0, newcomer=bob)


class ForecastAssignmentTest(unittest.TestCase):
    def test_the_best_elevator_depends_on_the_service_order(self):
        # Scenario 10: Bob 5 -> 10.
        for service_order, expected_elevator, expected_drop_offs in [
            (RequestOrder(), 1, {'bob': 50}),                # in A he would wait for Alice's trip
            (DirectionBased(), 0, {'bob': 9, 'alice': 30}),  # A picks him up on the way
            (Forecast(), 0, {'bob': 9, 'alice': 30}),        # same, and it costs Alice nothing
        ]:
            name = type(service_order).__name__
            self.assertEqual(choose_for_bob(10, service_order), (expected_elevator, expected_drop_offs), name)

    def test_allowed_delay_decides_the_elevator(self):
        # Scenario 11: Bob 5 -> 35 would still be aboard when elevator A reaches Alice.
        # K = 0: taking Bob in A would delay Alice by 10, so B.
        self.assertEqual(choose_for_bob(35, Forecast(allowed_delay=0)), (1, {'bob': 75}))
        # K = 10: Bob first in A, Alice 10 later. Combined 74 instead of 105.
        self.assertEqual(choose_for_bob(35, Forecast(allowed_delay=10)), (0, {'bob': 34, 'alice': 40}))

    def test_equally_good_elevators_go_to_the_least_busy(self):
        # Lobby rush: sharing an elevator costs nothing, so every elevator ties.
        elevators = [Elevator(id=i, capacity=10) for i in range(4)]
        service_order = RequestOrder()
        forecast = ForecastAssignment(service_order)
        for i in range(8):
            passenger = Passenger(f'p{i}', request_time=0, source=1, destination=10 + i)
            elevator = forecast.choose(elevators, passenger, time=0)
            elevator.assign(passenger)
            service_order.plan_pickup(elevator, passenger, time=0)
        self.assertEqual([len(elevator.waiting) for elevator in elevators], [2, 2, 2, 2])

    def test_forecasts_leave_the_real_elevator_and_service_order_unchanged(self):
        elevator = Elevator(id=0, capacity=10)
        alice = Passenger('alice', request_time=0, source=20, destination=1)
        bob = Passenger('bob', request_time=0, source=2, destination=1)
        service_order = Forecast()
        elevator.assign(alice)
        service_order.plan_pickup(elevator, alice, time=0)

        drop_off_times = forecast_drop_off_times(elevator, service_order, time=0, newcomer=bob)
        self.assertEqual(drop_off_times, {'bob': 2, 'alice': 40})  # scenario 13
        self.assertEqual((elevator.floor, elevator.waiting), (1, [alice]))
        self.assertIsNone(bob.assigned_elevator)
        self.assertEqual(service_order.pickup_orders[0], [alice])


if __name__ == '__main__':
    unittest.main()
