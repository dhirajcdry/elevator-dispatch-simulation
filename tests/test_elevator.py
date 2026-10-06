import unittest

from elevator import Elevator
from passenger import Passenger


class AssignTest(unittest.TestCase):
    def test_assign_adds_to_waiting_and_records_the_elevator(self):
        elevator = Elevator(id=0, capacity=10)
        alice = Passenger('alice', request_time=0, source=3, destination=5)
        elevator.assign(alice)
        self.assertEqual(elevator.waiting, [alice])
        self.assertEqual(alice.assigned_elevator, 0)

    def test_a_passenger_cannot_be_assigned_twice(self):
        alice = Passenger('alice', request_time=0, source=3, destination=5)
        Elevator(id=0, capacity=10).assign(alice)
        with self.assertRaises(ValueError):
            Elevator(id=1, capacity=10).assign(alice)


class PickUpTest(unittest.TestCase):
    def test_pick_up_moves_passenger_aboard_and_records_time(self):
        elevator = Elevator(id=0, capacity=10, floor=3)
        alice = Passenger('alice', request_time=0, source=3, destination=5)
        elevator.assign(alice)
        elevator.pick_up(alice, time=0)
        self.assertEqual(elevator.waiting, [])
        self.assertEqual(elevator.riders, [alice])
        self.assertEqual(alice.pickup_time, 0)  # time 0 is a real time, not "missing"

    def test_cannot_pick_up_someone_on_another_floor(self):
        elevator = Elevator(id=0, capacity=10, floor=1)
        alice = Passenger('alice', request_time=0, source=3, destination=5)
        elevator.assign(alice)
        with self.assertRaises(ValueError):
            elevator.pick_up(alice, time=0)

    def test_cannot_pick_up_someone_assigned_elsewhere(self):
        elevator = Elevator(id=0, capacity=10, floor=3)
        alice = Passenger('alice', request_time=0, source=3, destination=5)
        Elevator(id=1, capacity=10).assign(alice)
        with self.assertRaises(ValueError):
            elevator.pick_up(alice, time=0)

    def test_cannot_board_a_full_elevator(self):
        elevator = Elevator(id=0, capacity=1, floor=3)
        alice = Passenger('alice', request_time=0, source=3, destination=5)
        bob = Passenger('bob', request_time=0, source=3, destination=6)
        elevator.assign(alice)
        elevator.assign(bob)
        elevator.pick_up(alice, time=0)
        with self.assertRaises(ValueError):
            elevator.pick_up(bob, time=0)

    def test_cannot_board_against_the_riders_direction(self):
        elevator = Elevator(id=0, capacity=10, floor=3)
        alice = Passenger('alice', request_time=0, source=3, destination=5)  # up
        bob = Passenger('bob', request_time=0, source=3, destination=1)      # down
        elevator.assign(alice)
        elevator.assign(bob)
        elevator.pick_up(alice, time=0)
        with self.assertRaises(ValueError):
            elevator.pick_up(bob, time=0)


class DropOffTest(unittest.TestCase):
    def test_drop_off_only_riders_whose_destination_is_this_floor(self):
        elevator = Elevator(id=0, capacity=10, floor=3)
        alice = Passenger('alice', request_time=0, source=3, destination=5)
        bob = Passenger('bob', request_time=0, source=3, destination=6)
        for passenger in (alice, bob):
            elevator.assign(passenger)
            elevator.pick_up(passenger, time=0)
        elevator.floor = 5
        self.assertEqual(elevator.drop_off(time=2), [alice])
        self.assertEqual(elevator.riders, [bob])
        self.assertEqual(alice.drop_off_time, 2)
        self.assertEqual(alice.total_time, 2)


class MoveTest(unittest.TestCase):
    def test_moves_one_floor_toward_target_or_stays(self):
        elevator = Elevator(id=0, capacity=10, floor=5)
        elevator.move_one_floor_toward(9)
        self.assertEqual(elevator.floor, 6)
        elevator.move_one_floor_toward(2)
        self.assertEqual(elevator.floor, 5)
        elevator.move_one_floor_toward(5)
        self.assertEqual(elevator.floor, 5)

    def test_cannot_reverse_with_riders_aboard(self):
        elevator = Elevator(id=0, capacity=10, floor=3)
        alice = Passenger('alice', request_time=0, source=3, destination=5)
        elevator.assign(alice)
        elevator.pick_up(alice, time=0)
        self.assertEqual(elevator.direction, 'up')
        with self.assertRaises(ValueError):
            elevator.move_one_floor_toward(1)


class TripTest(unittest.TestCase):
    def test_move_to_goes_straight_there_but_never_reverses_with_riders(self):
        elevator = Elevator(id=0, capacity=10, floor=5)
        elevator.move_to(9)
        self.assertEqual(elevator.floor, 9)
        alice = Passenger('alice', request_time=0, source=9, destination=20)
        elevator.assign(alice)
        elevator.pick_up(alice, time=0)
        with self.assertRaises(ValueError):
            elevator.move_to(3)

    def test_rider_destinations(self):
        elevator = Elevator(id=0, capacity=10, floor=1)
        self.assertEqual(elevator.rider_destinations, [])
        for name, destination in (('alice', 9), ('bob', 4)):
            passenger = Passenger(name, request_time=0, source=1, destination=destination)
            elevator.assign(passenger)
            elevator.pick_up(passenger, time=0)
        self.assertEqual(elevator.rider_destinations, [9, 4])

    def test_passenger_count_is_riders_plus_waiting(self):
        elevator = Elevator(id=0, capacity=10)
        alice = Passenger('alice', request_time=0, source=1, destination=5)
        bob = Passenger('bob', request_time=0, source=3, destination=8)
        elevator.assign(alice)
        elevator.assign(bob)
        elevator.pick_up(alice, time=0)
        self.assertEqual(elevator.passenger_count, 2)

    def test_last_drop_off_is_the_farthest_destination_in_the_elevators_direction(self):
        elevator = Elevator(id=0, capacity=10, floor=10)
        for name, destination in (('alice', 20), ('bob', 15)):
            passenger = Passenger(name, request_time=0, source=10, destination=destination)
            elevator.assign(passenger)
            elevator.pick_up(passenger, time=0)
        self.assertEqual(elevator.last_drop_off, 20)

    def test_is_ahead_depends_on_direction_and_excludes_the_elevators_floor(self):
        elevator = Elevator(id=0, capacity=10, floor=10)
        self.assertTrue(elevator.is_ahead(12, 'up'))
        self.assertFalse(elevator.is_ahead(8, 'up'))
        self.assertTrue(elevator.is_ahead(8, 'down'))
        self.assertFalse(elevator.is_ahead(10, 'up'))


if __name__ == '__main__':
    unittest.main()
