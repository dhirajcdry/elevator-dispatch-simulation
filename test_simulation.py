import unittest

from assignment import RoundRobin
from elevator import Elevator
from passenger import Passenger
from service_order import RequestOrder
from simulation import Simulation


def run(passengers, cars=1, capacity=10):
    """Run a building with round robin and request order. Returns the position log."""
    elevators = [Elevator(id=i, capacity=capacity) for i in range(cars)]
    return Simulation(passengers, elevators, RoundRobin(), RequestOrder()).run()


def floors(positions, car=0):
    """One car's floor at every tick."""
    return [row[car] for row in positions]


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

    def test_full_car_delivers_its_riders_before_coming_back(self):
        alice = Passenger('alice', request_time=0, source=3, destination=20)
        bob = Passenger('bob', request_time=0, source=5, destination=10)
        run([alice, bob], capacity=1)

        # The car passes Bob at 5 while full, delivers Alice at 20, then returns.
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
        self.assertEqual(run([], cars=2), [[1, 1]])

    def test_every_car_is_logged_every_tick(self):
        alice = Passenger('alice', request_time=0, source=3, destination=4)
        bob = Passenger('bob', request_time=0, source=2, destination=3)
        positions = run([alice, bob], cars=2)  # round robin: Alice to car 0, Bob to car 1
        self.assertEqual(positions, [[1, 1], [2, 2], [3, 3], [4, 3]])

    def test_a_service_order_that_never_finishes_hits_the_safety_limit(self):
        class NeverBoards:
            def assigned(self, car, passenger, time):
                pass

            def who_boards(self, car):
                return []

            def next_target(self, car):
                return None

        alice = Passenger('alice', request_time=0, source=3, destination=5)
        simulation = Simulation([alice], [Elevator(id=0, capacity=10)], RoundRobin(), NeverBoards(), max_ticks=50)
        with self.assertRaises(RuntimeError):
            simulation.run()

    def test_unsorted_input_is_released_by_request_time(self):
        later = Passenger('later', request_time=2, source=1, destination=2)
        first = Passenger('first', request_time=0, source=1, destination=2)
        run([later, first], cars=2)  # round robin: first request goes to car 0
        self.assertEqual((first.assigned_elevator, later.assigned_elevator), (0, 1))


if __name__ == '__main__':
    unittest.main()
