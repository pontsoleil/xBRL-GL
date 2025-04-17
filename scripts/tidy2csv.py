#!/usr/bin/env python3
# coding: utf-8

"""
Universal Audit Data Converter: tidy2csv.py

This script converts a hierarchical tidy data CSV back to the proprietary CSV format.
The script processes a tidy CSV file and applies inverse semantic bindings and Logical Hierarchical Model (LHM)
to revert it into the proprietary CSV format.

designed by SAMBUICHI, Nobuyuki (Sambuichi Professional Engineers Office)
written by SAMBUICHI, Nobuyuki (Sambuichi Professional Engineers Office)

MIT License

(c) 2024 SAMBUICHI Nobuyuki (Sambuichi Professional Engineers Office)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import argparse
import sys
import os
import csv
import json
# from collections import defaultdict
import re

SEP = os.sep
TRACE = None
DEBUG = None
encoding = None

LHM_header = [
    "sequence",
    "level",
    "type",
    "identifier",
    "name",
    "datatype",
    "multiplicity",
    "domain_name",
    "definition",
    "module",
    "table",
    "class_term",
    "id",
    "path",
    "semantic_path",
]

binding_header = [
    "column",
    "name",
    "multiplicity",
    "datatype",
    "semSort",
    "id",
    "path",
    "semPath",
    "value",
    "line",
    "fixedValue",
    "term",
    "example",
]

semantic_dict = {}
binding_dict = {}
data_header = None
dimension = None


class ReverseDataProcessor:
    def __init__(self, binding_dict):
        self.binding_dict = binding_dict
        self.data = []
        self.header_row = None
        self.line_row = None
        self.is_candidate = False
        self.sorted_binding = sorted(
            self.binding_dict.values(),
            key=lambda x: x["semSort"] and int(x["semSort"]) or -1,
        )
        self.sorted_binding = [x for x in self.sorted_binding if x["semSort"]]

    def process_tidy_data(self, tidy_data):
        """
        Process the tidy data and store the unflattened records.
        """
        tidy_dict = self.restore_tidy_dict(tidy_data)
        self.data = self.flatten_dict(tidy_dict)

    # 指定されたインデックス階層に従って辞書を更新する関数
    def update_dict(self, d, idxs, key, value):
        # 最後のインデックスを除く階層を辿る
        for idx in idxs[:-1]:
            if idx not in d:
                d[idx] = {}
            d = d[idx]
        # 最終階層でリストが存在しない場合は新たに追加
        final_idx = idxs[-1]
        if final_idx not in d:
            d[final_idx] = {}
        # 最終階層のリストにキーと値のペアを追加
        if final_idx != key:
            if not d[final_idx]:
                d[final_idx] = {key: value}
            else:
                d[final_idx][key] = value

    def restore_tidy_dict(self, tidy_data):
        """
        Restore the tidy data dictionary structure from the tidy data CSV.
        """
        tidy_dict = {} # defaultdict(list)
        header = list(tidy_data[0].keys())
        indexes = [k for k in header if not re.search(r'_[0-9]+$', k)]
        for record in tidy_data:
            index = ''
            for key, value in record.items():
                if not value:
                    continue
                if key in indexes:
                    if value.isdigit() and int(value) > 0:
                        index += f'_{key}={value}'
                else:
                    index = index.strip('_')
                    idxs = index.split('_')
                    self.update_dict(tidy_dict, idxs, key, value)
        return tidy_dict

    # Function to split XPath correctly considering brackets
    def split_xpath(self, xpath):
        # Regular expression to match '/' outside of brackets
        pattern = r'/(?![^\[]*\])'
        parts = re.split(pattern, xpath)
        return parts

    def split_key_value(self, condition):
        if "=" not in condition:
            return condition, None
        key, value = condition.split("=")
        value = value.strip("' \"")
        return key, value

    def fill_row(self, path, id, val, row=None):
        column = [c for c, v in self.binding_dict.items() if path == v['semPath']]
        if column:
            column = column[0]
        if row and not self.is_candidate:
            if path in row:
                if not row[path]:
                    print(f'{column} {path} {id}: {val}')
                    row[path] = val
                else:
                    print(f'{column} {path} {id}: {val} EXISTS')
                    row[path] = val
        else:
            if all(self.line_selectors):
                self.line_row.append(self.header_row)
                self.line_selectors = {key: False for key in self.line_selectors.keys()}
            row = self.line_row[-1]
            if path in row:
                if not row[path]:
                    print(f'{column} {path} {id}: {val}')
                    row[path] = val
                else:
                    print(f'{column} {path} {id}: {val} EXPAND')
                    self.line_row.append(self.header_row)
                    row = self.line_row[-1]
                    row[path] = val
            else:
                print(f'{column} {path} {id}: {val} EXISTS')

    def get_nth_indices(self, selected_candidates):

        def is_non_negative_integer(value):
            return isinstance(value, int) and value >= 0

        key_D = [k for k in selected_candidates.keys() if "D" in k][0]
        key_C = [k for k in selected_candidates.keys() if "C" in k][0]
        key_N = [k for k in selected_candidates.keys() if "not" in k][0]

        D_indices = sorted(selected_candidates[key_D].keys())
        C_indices = sorted(selected_candidates[key_C].keys())
        N_indices = sorted(selected_candidates[key_N].keys())

        nth_indices = {
            "D": [],  # 初期値として空のリスト
            "C": [],  # 初期値として空のリスト
            "N": [],  # 初期値として空のリスト
        }

        next_D = next_C = next_N = None

        while True:

            if next_D and ((
                next_C
                and next_D > next_C
                and len(nth_indices["D"]) < len(nth_indices["C"])
            ) or (
                next_N
                and next_D > next_N
                and len(nth_indices["D"]) < len(nth_indices["N"])
            )):
                nth_indices["D"].insert(len(nth_indices["C"]) - 1, None)
            elif D_indices:
                next_D = D_indices.pop(0)
                nth_indices["D"].append(next_D)

            if next_C and ((
                next_D
                and next_C > next_D
                and len(nth_indices["C"]) < len(nth_indices["D"])
            ) or (
                next_N
                and next_C > next_N
                and len(nth_indices["C"]) < len(nth_indices["N"])
            )):
                nth_indices["C"].insert(len(nth_indices["C"]) - 1, None)
            elif C_indices:
                next_C = C_indices.pop(0)
                nth_indices["C"].append(next_C)

            if next_N and ((
                next_D
                and next_N > next_D
                and len(nth_indices["N"]) < len(nth_indices["D"])
            ) or (
                next_C
                and next_N > next_C
                and len(nth_indices["N"]) < len(nth_indices["C"])
            )):
                nth_indices["N"].insert(len(nth_indices["N"]) - 1, None)
            elif N_indices:
                next_N = N_indices.pop(0)
                nth_indices["N"].append(next_N)

            if not D_indices and not C_indices and not N_indices:
                break

        gap = len(nth_indices["N"]) - len(nth_indices["D"])

        if gap > 0:
            nth_indices["D"] += [None] * gap
        elif gap < 0:
            nth_indices["N"] += [None] * (-gap)

        gap = len(nth_indices["N"]) - len(nth_indices["C"])
        if gap > 0:
            nth_indices["C"] += [None] * gap
        elif gap < 0:
            nth_indices["N"] += [None] * (-gap)

        gap = len(nth_indices["D"]) - len(nth_indices["C"])
        if gap > 0:
            nth_indices["C"] += [None] * gap
        elif gap < 0:
            nth_indices["D"] += [None] * (-gap)

        # 転置処理
        transposed_array = []
        # zipを使って各インデックスのペアを取得し、転置
        for d, c, n in zip(nth_indices["D"], nth_indices["C"], nth_indices["N"]):
            transposed_array.append([d, c, n])

        transposed_candidates = []
        for row in transposed_array:
            record = {}
            if is_non_negative_integer(row[0]):
                data = selected_candidates[key_D][row[0]]
                record[key_D] = data
            if is_non_negative_integer(row[1]):
                data = selected_candidates[key_C][row[1]]
                record[key_C] = data
            if is_non_negative_integer(row[2]):
                data = selected_candidates[key_N][row[2]]
                record[key_N] = data
            transposed_candidates.append(record)

        return transposed_candidates

    # 変換用の関数を定義
    def replace_keys(self, rows, binding_dict):
        new_rows = []
        for row in rows:
            new_row = {c: None for c in binding_dict.keys() if not c.startswith('dColumn')}
            for key, value in row.items():
                for column, binding_value in binding_dict.items():
                    if key == binding_value['semPath']:
                        if not column.startswith('dColumn'):
                            new_row[column] = value
                        break
            new_rows.append(new_row)
        return new_rows

    def fill_record(self, tidy_record, root_id, header_row, rows):
        # Define the regex patterns for ([key=val] or [not(...)]) and [number]
        key_val_pattern = re.compile(r'\[([^\[\]]*?=.*?|not\(.*?\))\]')

        line_id = None
        for i, id in enumerate(tidy_record):
            path = f'/{root_id}/{id}'
            if path in header_row:
                print(f"{i} {path} {id}")
                header_row[path] = tidy_record[id]
                print(f"    {header_row[path]}")
            elif '=' in id and not line_id:
                line_id = id[:id.index('=')]

        line_selectors = [v["value"] for v in self.sorted_binding if v["id"] == line_id]
        if line_selectors:
            line_selectors = line_selectors[0].split()
            line_selectors = {s: False for s in line_selectors}
        selected_candidates = {id: {} for id in line_selectors}

        for i, id in enumerate(line_selectors):
            print(f"{i} {id}")
            key_val_match = key_val_pattern.findall(id)
            if key_val_match:
                key_val = key_val_match[-1]
                condition_key = prohibit_key = None
                if "not" in key_val:
                    prohibit_key = key_val[4:].strip("()").strip()
                else:
                    condition_key, condition_value = self.split_key_value(key_val)
                # Check lines
                candidates = [d for k, d in tidy_record.items() if line_id in k]
                for i, c in enumerate(candidates):
                    if not isinstance(c, dict):
                        continue  # cが辞書でない場合はスキップ
                    # prohibit_keyのチェック
                    if prohibit_key and prohibit_key not in c:
                        index = f"[not({prohibit_key})]"
                        selected_candidates[index][i] = c
                    # condition_keyとcondition_valueのチェック
                    if condition_key in c and c[condition_key] == condition_value:
                        index = f'[{condition_key}="{condition_value}"]'
                        selected_candidates[index][i] = c

        transposed_candidates = self.get_nth_indices(selected_candidates)

        for candidate in transposed_candidates:
            line_row = header_row.copy()
            for path in header_row:
                if re.match(r'', path) and line_id in path:
                    id = path.replace(f'/{root_id}/{line_id}','')
                    id = id.strip('/')
                    if id and re.match(r'.*_[0-9]+$', path):
                        if 1 == id.count('/'):
                            key = id[:id.index('/')]
                            if key in candidate:
                                data = candidate[key]
                                id = path.replace(f'/{root_id}/{line_id}{key}/','')
                                value = data[id]
                                print(f'{path} {value}')
                                line_row[path] = value
                        elif 2 == id.count('/'):
                            key = id[:id.index('/')]
                            if key in candidate:
                                data = candidate[key]
                                id2 = path.replace(f'/{root_id}/{line_id}{key}/','')
                                key2 = id2[:id2.index('/')]
                                data2 = [d for k, d in data.items() if key2 in k]
                                if data2:
                                    data2 = data2[0]
                                    key3 = id2[1+id2.index('/'):]
                                    value = data2[key3]
                                    print(f'{path} {value}')
                                    line_row[path] = value

            rows.append(line_row)

        return rows

    def flatten_dict(self, tidy_dict):
        """
        Perform flattening of the tidy data into proprietary CSV file columns using the binding map.
        """
        self.tidy_dict = tidy_dict
        self.col_header = [v['semPath'] for v in self.sorted_binding][1:]
        rows = []
        for root_key, tidy_record in tidy_dict.items():
            self.header_row = self.line_row =  {k: None for k in self.col_header}
            root_id = root_key[:root_key.index('=')]
            rows = self.fill_record(tidy_record, root_id, self.header_row, rows)

        flatten_data = self.replace_keys(rows, binding_dict)

        return flatten_data

    def get_data(self):
        return self.data


def read_lhm_file(LHM_file, encoding=encoding):
    """
    Reads the Logical Hierarchical Model (LHM) file and returns its structure as a dictionary.
    Parameters:
    - LHM_file: Path to the LHM CSV file.
    Returns:
    - A dictionary representing the hierarchical message definition.
    """
    with open(LHM_file, mode="r", encoding=encoding) as file:
        csv_reader = csv.DictReader(file, fieldnames=LHM_header)
        next(csv_reader)  # Skip the header line
        seq = 1000
        for row in csv_reader:
            id = row['id']
            seq = int(row['sequence']) if row['sequence'].isdigit() else row['sequence']
            row["sequence"] = seq
            semantic_dict[id] = row
    return semantic_dict


def read_binding_file(binding_file, encoding=encoding):
    """
    Reads the binding file and returns its structure as a dictionary, list, and its header.
    Parameters:
    - binding_file: Path to the binding CSV file.
    Returns:
    - A dictionary representing a binding definition.
    - A header of binding list.
    """
    with open(binding_file, mode="r", encoding=encoding) as file:
        csv_reader = csv.DictReader(file, fieldnames=binding_header)
        next(csv_reader)  # Skip the header line
        for row in csv_reader:
            column = row['column']
            seq = int(row['semSort']) if row['semSort'].isdigit() else row['semSort']
            if seq:
                row["sequence"] = seq
                binding_dict[column] = row

    csv_column_names = [
        {x["column"]: x["name"]} for k, x in binding_dict.items() if "d" != k[0]
    ]
    csv_columns = {}
    for d in csv_column_names:
        csv_columns.update(d)
    data_header = list(csv_columns.keys())
    return binding_dict, data_header


def tidy_to_proprietary(tidy_file, out_file, binding_dict):
    """
    Converts tidy CSV to proprietary CSV.
    Parameters:
    - tidy_file: Path to the tidy CSV file.
    - out_file: Path to the output proprietary CSV file.
    - binding_dict: Binding dictionary to map tidy data to proprietary format.
    """
    processor = ReverseDataProcessor(binding_dict)

    with open(tidy_file, mode="r", encoding=encoding) as file:
        csv_reader = csv.DictReader(file)
        tidy_data = list(csv_reader)

    processor.process_tidy_data(tidy_data)
    proprietary_data =  processor.get_data()

    # CSVのヘッダーを作成
    header = [c for c in binding_dict.keys() if not c.startswith('dColumn')]
    # CSVファイルに出力
    with open(out_file, 'w', newline='', encoding=encoding) as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=header)
        writer.writeheader()
        for row in proprietary_data:
            writer.writerow(row)


def file_path(pathname):
    if SEP == pathname[0:1]:
        return pathname
    else:
        pathname = pathname.replace("/", SEP)
        dir = os.path.dirname(__file__)
        new_path = os.path.join(dir, pathname)
        return new_path


def main():
    global DEBUG
    global TRACE
    global encoding
    global binding_dict
    global data_header

    parser = argparse.ArgumentParser(
        prog="tidy2csv.py",
        usage="%(prog)s infile -o outfile -m lhm_file -b binding_file -e encoding [options] ",
        description="Converts hierarchical tidy data CSV to proprietary CSV format.",
    )
    parser.add_argument(
        "inFile", metavar="infile", type=str, help="Input tidy CSV file path"
    )
    parser.add_argument(
        "-o", "--outfile", required=True, help="Output proprietary CSV file path"
    )
    parser.add_argument("-m", "--lhm_file", required=True, help="LHM file path")
    parser.add_argument("-b", "--binding_file", required=True, help="Binding file path")
    parser.add_argument(
        "-e",
        "--encoding",
        required=False,
        default="utf-8-sig",
        help="File encoding, default is utf-8-sig",
    )
    parser.add_argument("-t", "--trace", required=False, action="store_true")
    parser.add_argument("-d", "--debug", required=False, action="store_true")

    args = parser.parse_args()

    in_file = args.inFile.strip()
    in_file = in_file.replace("/", SEP)
    in_file = file_path(args.inFile)
    if not in_file or not os.path.isfile(in_file):
        print("No input tidy CSV file.")
        sys.exit()
    tidy_file = in_file

    if args.outfile:
        out_file = args.outfile.strip()
        out_file = out_file.replace("/", SEP)
        out_file = file_path(out_file)

    if args.lhm_file:
        lhm_file = args.lhm_file.strip()
        lhm_file = lhm_file.replace("/", SEP)
        LHM_file = file_path(lhm_file)
    if not lhm_file or not os.path.isfile(LHM_file):
        print("No hierarchical message definition file.")
        sys.exit()

    if args.binding_file:
        binding_file = args.binding_file.strip()
        binding_file = binding_file.replace("/", SEP)
        binding_file = file_path(binding_file)
    if not binding_file or not os.path.isfile(binding_file):
        print("No binding file.")
        sys.exit()

    encoding = args.encoding.strip()
    TRACE = args.trace
    DEBUG = args.debug

    semantic_dict = read_lhm_file(LHM_file, encoding)

    binding_dict, data_header = read_binding_file(binding_file, encoding)

    tidy_to_proprietary(tidy_file, out_file, binding_dict)

    print(f"** END **\nconverted {tidy_file} \nto {out_file}")


if __name__ == "__main__":
    main()
