import unittest

from assignment import RoundRobin
from elevator import Elevator
from passenger import Passenger
from service_order import DirectionBased, RequestOrder
from simulation import Simulation


def run(passengers, service_order, capacity=10):
    """One car at floor 1. Returns its floor at every tick."""
    positions = Simulation(passengers, [Elevator(id=0, capacity=capacity)], RoundRobin(), service_order).run()
    return [row[0] for row in positions]


def three_passengers():
    return [
        Passenger('alice', request_time=0, source=3, destination=20),
        Passenger('bob', request_time=0, source=2, destination=10),
        Passenger('carol', request_time=0, source=15, destination=4),
    ]


class DirectionBasedTest(unittest.TestCase):
    def test_picks_up_on_the_way_then_reverses_for_the_other_direction(self):
        alice, bob, carol = three_passengers()
        floors = run([alice, bob, carol], DirectionBased())

        self.assertEqual(bob.pickup_time, 1)  # on the way up, though Alice asked first
        self.assertEqual((alice.total_time, bob.total_time, carol.total_time), (19, 9, 35))
        self.assertEqual(carol.pickup_time, 24)  # passed going up at 14, collected after reversing at 20
        self.assertEqual(floors[19:21], [20, 19])

    def test_same_passengers_under_request_order_for_comparison(self):
        alice, bob, carol = three_passengers()
        run([alice, bob, carol], RequestOrder())
        self.assertEqual((alice.total_time, bob.total_time, carol.total_time), (19, 45, 61))

    def test_takes_whoever_fits_now_even_if_an_earlier_passenger_waits(self):
        # Deck capacity slide: capacity 1, Alice 30 -> 31 asked first, Bob 5 -> 50.
        alice = Passenger('alice', request_time=0, source=30, destination=31)
        bob = Passenger('bob', request_time=0, source=5, destination=50)
        run([alice, bob], DirectionBased(), capacity=1)
        self.assertEqual((bob.pickup_time, bob.drop_off_time), (4, 49))
        self.assertEqual((alice.pickup_time, alice.drop_off_time), (69, 70))

    def test_does_not_pick_up_someone_going_the_other_way(self):
        # Deck direction slide: Bob 5 -> 2 is near but going down; the car is sweeping up for Alice.
        alice = Passenger('alice', request_time=0, source=30, destination=31)
        bob = Passenger('bob', request_time=0, source=5, destination=2)
        run([alice, bob], DirectionBased(), capacity=1)
        self.assertEqual(alice.total_time, 30)
        self.assertEqual(bob.total_time, 59)

    def test_an_early_request_can_be_passed_again_and_again(self):
        # Finding 3: capacity 1, Alice asks first (10 -> 12); a stream of 2 -> 20 trips keeps filling the car.
        alice = Passenger('alice', request_time=0, source=10, destination=12)
        stream = [Passenger('p1', 0, 2, 20)] + [Passenger(f'p{k}', 20 + 36 * (k - 2), 2, 20) for k in range(2, 7)]
        run([alice] + stream, DirectionBased(), capacity=1)
        self.assertEqual(alice.total_time, 211)  # served only once the stream ends

        alice = Passenger('alice', request_time=0, source=10, destination=12)
        stream = [Passenger('p1', 0, 2, 20)] + [Passenger(f'p{k}', 20 + 36 * (k - 2), 2, 20) for k in range(2, 7)]
        run([alice] + stream, RequestOrder(), capacity=1)
        self.assertEqual(alice.total_time, 11)

    def test_idle_car_stays_put(self):
        alice = Passenger('alice', request_time=0, source=1, destination=3)
        later = Passenger('later', request_time=6, source=3, destination=1)
        floors = run([alice, later], DirectionBased())
        self.assertEqual(floors[2:7], [3, 3, 3, 3, 3])  # delivered at tick 2, waits for tick 6
        self.assertEqual(later.drop_off_time, 8)


if __name__ == '__main__':
    unittest.main()
