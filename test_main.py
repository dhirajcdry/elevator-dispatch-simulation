import csv
import os
import tempfile
import unittest

from main import check_output_path, read_requests, write_positions


def write_file(folder: str, text: str) -> str:
    path = os.path.join(folder, 'requests.csv')
    with open(path, 'w', encoding='utf-8') as file:
        file.write(text)
    return path


class ReadRequestsTest(unittest.TestCase):
    def test_reads_rows_in_file_order(self):
        with tempfile.TemporaryDirectory() as folder:
            path = write_file(folder, 'time,id,source,dest\n0,passenger1,1,51\n10,passenger3,20,1\n')
            requests = read_requests(path)
        self.assertEqual(requests, [(0, 'passenger1', 1, 51), (10, 'passenger3', 20, 1)])

    def test_missing_column_is_reported(self):
        with tempfile.TemporaryDirectory() as folder:
            path = write_file(folder, 'time,id,source\n0,passenger1,1\n')
            with self.assertRaisesRegex(ValueError, 'dest'):
                read_requests(path)

    def test_non_number_names_the_row(self):
        with tempfile.TemporaryDirectory() as folder:
            path = write_file(folder, 'time,id,source,dest\n0,passenger1,1,51\nsoon,passenger2,1,37\n')
            with self.assertRaisesRegex(ValueError, 'line 3'):
                read_requests(path)

    def test_loose_headers_excel_marker_and_blank_lines(self):
        text = '\ufeffTime, ID , Source,DEST,note\n\n0,passenger1,1,51,hi\n\n10,passenger3,20,1,\n'
        with tempfile.TemporaryDirectory() as folder:
            requests = read_requests(write_file(folder, text))
        self.assertEqual(requests, [(0, 'passenger1', 1, 51), (10, 'passenger3', 20, 1)])

    def test_line_numbers_count_blank_lines(self):
        with tempfile.TemporaryDirectory() as folder:
            path = write_file(folder, 'time,id,source,dest\n0,a,1,5\n\n\n1,b,x,6\n')
            with self.assertRaisesRegex(ValueError, 'line 5'):
                read_requests(path)

    def test_rejected_files_and_rows(self):
        cases = {
            'empty': '',
            'appears more than once': 'time,id,source,dest,time\n0,a,1,5,9\n',
            'expected 4 values, found 5': 'time,id,source,dest\n0,a,1,5,\n',
            'expected 4 values, found 3': 'time,id,source,dest\n0,a,1\n',
            'every column needs a value': 'time,id,source,dest\n0,  ,1,5\n',
            'time must be a whole number': 'time,id,source,dest\n1_0,a,1,5\n',
            'source must be a whole number': 'time,id,source,dest\n0,a,\u0663,5\n',
            'dest must be a whole number': 'time,id,source,dest\n0,a,1,5.0\n',
        }
        for message, text in cases.items():
            with self.subTest(message), tempfile.TemporaryDirectory() as folder:
                with self.assertRaisesRegex(ValueError, message):
                    read_requests(write_file(folder, text))

    def test_unreadable_files_are_reported_cleanly(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, 'No such file'):
                read_requests(os.path.join(folder, 'missing.csv'))
            with self.assertRaisesRegex(ValueError, 'directory'):
                read_requests(folder)
            path = os.path.join(folder, 'latin1.csv')
            with open(path, 'wb') as file:
                file.write('time,id,source,dest\n0,caf\u00e9,1,5\n'.encode('latin-1'))
            with self.assertRaisesRegex(ValueError, 'not a UTF-8 text file'):
                read_requests(path)


class CheckOutputPathTest(unittest.TestCase):
    def test_bad_output_paths_are_rejected_before_the_run(self):
        with tempfile.TemporaryDirectory() as folder:
            input_path = write_file(folder, 'time,id,source,dest\n')
            check_output_path(os.path.join(folder, 'positions.csv'), input_path)  # fine
            cases = {
                'is a folder': folder,
                'does not exist': os.path.join(folder, 'missing', 'positions.csv'),
                'overwrite the input': input_path,
            }
            for message, path in cases.items():
                with self.subTest(message), self.assertRaisesRegex(ValueError, message):
                    check_output_path(path, input_path)


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
