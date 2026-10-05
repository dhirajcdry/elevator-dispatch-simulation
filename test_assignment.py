import unittest

from assignment import NearestElevator, RoundRobin, floors_until_pickup
from elevator import Elevator
from passenger import Passenger


def elevator_carrying_up(id: int, floor: int, destination: int) -> Elevator:
    """An elevator at `floor` with one rider aboard, heading up to `destination`."""
    elevator = Elevator(id=id, capacity=10, floor=floor)
    rider = Passenger(f'rider{id}', request_time=0, source=floor, destination=destination)
    elevator.assign(rider)
    elevator.pick_up(rider, time=0)
    return elevator


class RoundRobinTest(unittest.TestCase):
    def test_takes_turns_and_ignores_where_elevators_are(self):
        elevators = [Elevator(id=0, capacity=10, floor=1), Elevator(id=1, capacity=10, floor=25)]
        alice = Passenger('alice', request_time=0, source=30, destination=31)
        bob = Passenger('bob', request_time=0, source=2, destination=5)
        carol = Passenger('carol', request_time=0, source=40, destination=41)
        round_robin = RoundRobin()
        self.assertIs(round_robin.choose(elevators, alice, time=0), elevators[0])
        self.assertIs(round_robin.choose(elevators, bob, time=0), elevators[1])  # elevator 0 is closer, but it is elevator 1's turn
        self.assertIs(round_robin.choose(elevators, carol, time=0), elevators[0])


class NearestElevatorTest(unittest.TestCase):
    def test_empty_elevators_closest_wins(self):
        # Deck slide 7: elevator 0 at 1, elevator 1 at 25, Alice at 30.
        elevators = [Elevator(id=0, capacity=10, floor=1), Elevator(id=1, capacity=10, floor=25)]
        alice = Passenger('alice', request_time=0, source=30, destination=31)
        self.assertIs(NearestElevator().choose(elevators, alice, time=0), elevators[1])

    def test_equally_close_elevators_go_to_the_least_busy(self):
        # Lobby rush: four idle elevators at floor 1, eight people request at tick 0.
        elevators = [Elevator(id=i, capacity=10) for i in range(4)]
        nearest = NearestElevator()
        for i in range(8):
            passenger = Passenger(f'p{i}', request_time=0, source=1, destination=10 + i)
            nearest.choose(elevators, passenger, time=0).assign(passenger)
        self.assertEqual([len(elevator.waiting) for elevator in elevators], [2, 2, 2, 2])

    def test_tie_goes_to_lowest_elevator_number(self):
        elevators = [Elevator(id=0, capacity=10, floor=5), Elevator(id=1, capacity=10, floor=15)]
        alice = Passenger('alice', request_time=0, source=10, destination=12)
        self.assertIs(NearestElevator().choose(elevators, alice, time=0), elevators[0])

    def test_passenger_ahead_and_same_way_is_picked_up_on_the_way(self):
        elevator = elevator_carrying_up(id=0, floor=10, destination=20)
        alice = Passenger('alice', request_time=0, source=15, destination=18)
        self.assertEqual(floors_until_pickup(elevator, alice), 5)

    def test_passenger_behind_waits_for_riders_to_be_delivered(self):
        elevator = elevator_carrying_up(id=0, floor=10, destination=20)
        alice = Passenger('alice', request_time=0, source=8, destination=12)
        self.assertEqual(floors_until_pickup(elevator, alice), 10 + 12)  # up to 20, back down to 8

    def test_passenger_going_the_other_way_waits_for_riders_to_be_delivered(self):
        elevator = elevator_carrying_up(id=0, floor=10, destination=20)
        alice = Passenger('alice', request_time=0, source=15, destination=2)
        self.assertEqual(floors_until_pickup(elevator, alice), 10 + 5)  # up to 20, back down to 15

    def test_a_close_elevator_heading_away_loses_to_a_farther_empty_elevator(self):
        elevators = [elevator_carrying_up(id=0, floor=10, destination=20), Elevator(id=1, capacity=10, floor=3)]
        alice = Passenger('alice', request_time=0, source=8, destination=12)
        # Plain distance would pick elevator 0 (2 floors); it must first go to 20, so 22.
        self.assertIs(NearestElevator().choose(elevators, alice, time=0), elevators[1])  # 5 floors

    def test_an_empty_elevator_heading_to_a_pickup_away_loses_to_a_farther_idle_elevator(self):
        # Elevator 0 at 10 is empty but must first go up to Alice at 30; Bob at 9 is going down.
        elevators = [Elevator(id=0, capacity=10, floor=10), Elevator(id=1, capacity=10, floor=17)]
        elevators[0].assign(Passenger('alice', request_time=0, source=30, destination=31))
        bob = Passenger('bob', request_time=0, source=9, destination=1)
        self.assertEqual(floors_until_pickup(elevators[0], bob), 20 + 21)  # up to 30, back down to 9
        self.assertIs(NearestElevator().choose(elevators, bob, time=0), elevators[1])  # 8 floors


if __name__ == '__main__':
    unittest.main()
