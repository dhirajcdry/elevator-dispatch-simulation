import csv
import os
import tempfile
import unittest

from main import check_requests, read_requests, write_positions
from passenger import Passenger


def write_file(folder: str, text: str) -> str:
    path = os.path.join(folder, 'requests.csv')
    with open(path, 'w') as file:
        file.write(text)
    return path


class ReadRequestsTest(unittest.TestCase):
    def test_reads_rows_in_file_order(self):
        with tempfile.TemporaryDirectory() as folder:
            path = write_file(folder, 'time,id,source,dest\n0,passenger1,1,51\n10,passenger3,20,1\n')
            passengers = read_requests(path)
        self.assertEqual([p.id for p in passengers], ['passenger1', 'passenger3'])
        self.assertEqual((passengers[1].request_time, passengers[1].source, passengers[1].destination), (10, 20, 1))

    def test_missing_column_is_reported(self):
        with tempfile.TemporaryDirectory() as folder:
            path = write_file(folder, 'time,id,source\n0,passenger1,1\n')
            with self.assertRaisesRegex(ValueError, 'dest'):
                read_requests(path)

    def test_non_number_names_the_row(self):
        with tempfile.TemporaryDirectory() as folder:
            path = write_file(folder, 'time,id,source,dest\n0,passenger1,1,51\nsoon,passenger2,1,37\n')
            with self.assertRaisesRegex(ValueError, 'row 3'):
                read_requests(path)


class CheckRequestsTest(unittest.TestCase):
    def test_valid_requests_pass(self):
        check_requests([Passenger('a', 0, 1, 10)], floors=10)

    def test_each_rule_is_enforced(self):
        cases = {
            'used more than once': [Passenger('a', 0, 1, 2), Passenger('a', 1, 2, 3)],
            'negative': [Passenger('a', -1, 1, 2)],
            'outside floors': [Passenger('a', 0, 1, 11)],
            'same floor': [Passenger('a', 0, 4, 4)],
        }
        for message, passengers in cases.items():
            with self.subTest(message), self.assertRaisesRegex(ValueError, message):
                check_requests(passengers, floors=10)


class WritePositionsTest(unittest.TestCase):
    def test_one_row_per_tick_with_a_header(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, 'positions.csv')
            write_positions(path, [[1, 1], [2, 1]])
            with open(path, newline='') as file:
                rows = list(csv.reader(file))
        self.assertEqual(rows, [['time', 'elevator_0', 'elevator_1'], ['0', '1', '1'], ['1', '2', '1']])


if __name__ == '__main__':
    unittest.main()
