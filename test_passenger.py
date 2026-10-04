import unittest

from passenger import Passenger


class DirectionTest(unittest.TestCase):
    def test_direction_comes_from_source_and_destination(self):
        self.assertEqual(Passenger('alice', request_time=0, source=3, destination=5).direction, 'up')
        self.assertEqual(Passenger('bob', request_time=0, source=5, destination=2).direction, 'down')


if __name__ == '__main__':
    unittest.main()
