#!/usr/bin/env python3
# coding: utf-8
"""
Universal Audit Data Converter: csv2tidy.py

This script converts a proprietary CSV to the standard hierarchical tidy data
CSV. The script processes a proprietary CSV file, applies semantic bindings
and Logical Hierarchycal Model (LHM) to convert it into a tidy CSV
format that follows a hierarchical structure.

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
import re
import json
from datetime import datetime
from pathlib import Path
from collections import defaultdict

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


class DataProcessor:
    def __init__(self, binding_dict):
        self.current = 0  # column index of sorted_binding
        self.dim_level = {}  # Stores levels of dimensions
        self.dim_line = {}  # Tracks the current line number for each dimension
        self.current_dim_line = {}  # Tracks the previous line number for each dimension
        self.data_line = set()  # Tracks all processed elements
        self.record = {}  # The current record being processed
        self.records = []  # All processed records

        sorted_binding = sorted(
            binding_dict.values(),
            key=lambda x: x["semSort"] and int(x["semSort"]) or -1,
        )
        sorted_binding = [x for x in sorted_binding if x["semSort"]]

        self.dim_data = [
            {x["semPath"].split("/")[-1]: len(x["semPath"].split("/")) - 2}
            for x in sorted_binding
            if "d" == x["column"][0] and x["semPath"]
        ]

        for d in self.dim_data:
            self.dim_level.update(d)

        for k in self.dim_level.keys():
            self.dim_line.update({k: 0})

    def get_dim_line(self):
        return list(self.dim_line)

    def get_data_line(self):
        return list(self.data_line)

    def get_records(self):
        return list(self.records)

    def debug_print(self, message):
        if DEBUG:
            print(message)

    def determine_type(self, value):
        if isinstance(value, dict):
            return "dict"
        elif isinstance(value, list):
            return "list"
        else:
            return "atomic"

    def set_record(self, element, value):
        """Update the record with a new element-value pair and track the dimension line changes."""
        for dim_id, dim_val in self.dim_line.items():
            if dim_id not in self.record or dim_val != self.record[dim_id]:
                self.record[dim_id] = dim_val
        self.record[element] = value
        self.data_line.add(element)

    def atomic_process(self, d, path):
        element = path.strip("/").split("/")[-1]
        value = d
        self.set_record(element, value)

    def list_process(self, d, path):
        self.debug_print(f"- list_process path:{path}")
        for sub in d:
            dim = path.strip("/").split("/")[-1]
            dim = re.sub(r"\[\d+\]$", "", dim)
            changed = False
            d_level = -1
            count = 0
            for d in self.dim_line.keys():
                if d == dim:
                    self.dim_line[d] += 1
                    count = self.dim_line[d]
                    d_level = self.dim_level[d]
                    changed = True
            for d in self.dim_line.keys():
                if changed and self.dim_level[d] >= d_level and dim != d:
                    self.dim_line[d] = 0
                self.record[d] = self.dim_line[d]
            self.debug_print(f"- list_process dim_line:{self.dim_line}")
            path = re.sub(r"\[\d+\]/$", "/", path)
            path = f"/{path.strip('/')}[{count}]/"
            self.flatten_dict(sub, path)

    def dict_process(self, d, path):
        self.debug_print(f"- dict_process path:{path}")
        for k, v in d.items():
            if "atomic" == self.determine_type(v):
                self.atomic_process(v, f"{path}{k}/")
        if len(self.record.keys()) > 0:
            self.debug_print(f"- dict_process append record:{self.record}")
            self.records.append(self.record.copy())
        self.record = {}
        for k, v in d.items():
            if "dict" == self.determine_type(v):
                self.flatten_dict(v, f"{path}{k}/")
        for k, v in d.items():
            if "list" == self.determine_type(v):
                self.list_process(v, f"{path}{k}/")

    def flatten_dict(self, d, path="/"):
        self.debug_print(f"\nflatten_dict path:{path}")
        if "atomic" == self.determine_type(d):
            self.atomic_process(d, path)
        elif "dict" == self.determine_type(d):
            self.dict_process(d, path)
        elif "list" == self.determine_type(d):
            self.list_process(d, path)


class StructuredCSV:
    def __init__(self, binding_dict, semantic_dict):
        self.binding_dict = binding_dict
        self.semantic_dict = semantic_dict
        self.tidy_data = {}

        self.dimension = self.initialize_hierarchy(binding_dict)

    def debug_print(self, message):
        if DEBUG:
            print(message)

    def trace_print(self, message):
        if TRACE:
            print(message)

    def escape(self, string):
        if not string:
            return ''
        escaped = string
        if 0 == len(escaped):
            escaped = '&blank;'
        else:
            escaped = escaped.replace('/','&slash;')
        return escaped

    def isblank(self, string):
        return '&blank;' == string

    def unescape(self, string):
        unescaped = string
        if '&blank;' == unescaped:
            unescaped = ''
        else:
            unescaped = unescaped.replace('&slash;','/')
        return unescaped

    def is_multiple(self, id):
        multiplicity = [
            x["multiplicity"] for x in self.binding_dict.values() if id == x["id"]
        ]
        if multiplicity:
            multiplicity = multiplicity[0][-1]
            if "*" == multiplicity:
                return True
        return False

    def initialize_hierarchy(self, binding_dict):
        sorted_binding = sorted(
            binding_dict.values(),
            key=lambda x: x["semSort"] and int(x["semSort"]) or -1,
        )
        self.sorted_binding = [x for x in sorted_binding if x["semSort"]]
        paths = [
            x["path"] for x in self.binding_dict.values() if x["column"].startswith("d")
        ]
        dimension = {
            x[1 + x.rindex("/") :]: {
                "element": x[1 + x.rindex("/") :],
                "path": x,
                "counter": -1,
                "value": None,
                "ditto": False,
                "parent": None,
                "descendant": [],
                "semantic_path": None,
            }
            for x in paths
        }

        def is_descendant(parent, child):
            if child.startswith(parent) and parent != child:
                return True
            return False

        for parent_path in paths:
            for child_path in paths:
                if is_descendant(parent_path, child_path):
                    child_id = child_path[1 + child_path.rindex("/") :]
                    parent_id = parent_path[1 + parent_path.rindex("/") :]
                    dimension[parent_id]["descendant"].append(child_id)

        for parent_path in paths:
            for child_path in paths:
                if is_descendant(parent_path, child_path):
                    child_id = child_path[1 + child_path.rindex("/") :]
                    parent_id = parent_path[1 + parent_path.rindex("/") :]
                    dimension[child_id]["parent"] = parent_id

        for id, value in dimension.items():
            value["semantic_path"] = [
                x["term"] for x in binding_dict.values() if value["path"] == x["path"]
            ][0]

        return dimension

    def extract_key(self, condition):
        # This function extracts the key from the condition.
        # The regular expression pattern `([^\[\]]+)` matches one or more characters that are not brackets.
        # The key is the first part of the condition before any brackets.
        match = re.match(r"([^\[\]]+)", condition)
        key = (match.group(1) if match else "")  # Extracts the matched key or returns an empty string if no match.
        return key

    def extract_bracket_content(self, condition):
        # Find all content within brackets
        matches = re.findall(r"\[(.*?)\]", condition)
        if matches:
            return matches
        else:
            return [""]

    def is_numeric_condition(self, condition):
        # Check if the condition is numeric
        if not condition:
            return False
        return condition.isdigit()

    def extract_key_value_from_node(self, d):
        if not isinstance(d, dict):  # or len(d) != 1:
            raise ValueError(
                "Input node must be a dictionary with a single key-value pair."
            )
        key = self.extract_key(d)  # list(d.keys())[0]
        value = d[key].strip("' \"")
        value = self.unescape(value)
        return key, value

    def split_query(self, query):
        # Regular expression to find all conditions within [ ]
        pattern = re.compile(r"\[.*?\]")
        conditions = pattern.findall(query)
        # Extract the key by removing all conditions from the original query
        key = pattern.sub("", query).strip()
        # Clean up the conditions by removing the [ ] characters
        conditions = [condition.strip("[]") for condition in conditions]
        return key, conditions

    def split_path_ignoring_brackets(self, path):
        elements = []
        current = ""
        bracket_level = 0
        for char in path:
            if char == "/" and bracket_level == 0:
                if current:
                    elements.append(current)
                    current = ""
            else:
                current += char
                if char == "[":
                    bracket_level += 1
                elif char == "]":
                    bracket_level -= 1
        if current:
            elements.append(current)
        return elements

    def check_date_format(self, value, datatype):
        if "Date" == datatype:
            value = self.unescape(value)
            if re.match(r"\d{1,2}/\d{1,2}/\d{4} \d{2}:\d{2}", value):
                date_obj = datetime.strptime(value, "%m/%d/%Y %H:%M")
                value = date_obj.strftime("%Y-%m-%d")
            elif re.match(r"\d{4}\d{2}\d{2}", value):
                date_obj = datetime.strptime(value, "%Y%m%d")
                value = date_obj.strftime("%Y-%m-%d")
            elif re.match(r"\d{1,2}/\d{1,2}/\d{4}", value):
                date_obj = datetime.strptime(value, "%m/%d/%Y")
                value = date_obj.strftime("%Y-%m-%d")
            return value          
        elif "DateTime" == datatype:            
            value = self.unescape(value)
            date_pattern = r"\d{4}-\d{2}-\d{2}"
            time_pattern = r"\d{2}:\d{2}:\d{2}"
            date_match = re.search(date_pattern, value)
            time_match = re.search(time_pattern, value)
            if date_match and time_match:
                value = f"{date_match.group()}T{time_match.group()}"
        return value

    def check_column_condition(self, record, column, semPath, columnValue, value):
        value_num = None
        if 'd'==column[0]:
            column = column[1:]
            value_num = int(value) if str(value).isdigit() else value
        else:
            if not columnValue:
                return True
            semPath = semPath[:semPath.rindex('/')]
        columnPath = self.binding_dict[column]['semPath']
        if '>' in columnValue:
            value_condition = columnValue.split('>')
            value_path = value_condition[0]
            condition = value_condition[1] if len(value_condition) > 1 else None
            if columnPath != f"{semPath}/{value_path}":
                columnPath = f"{semPath}/{value_path}"
            try:
                if 'd'!=column[0]:
                    value_num = 0
                    value_columns = [k for k,v in self.binding_dict.items() if value_path==v['id']]
                    if len(value_columns) > 0:
                        value_column = value_columns[0]
                        value_num = record[value_column]
                        if re.match('[0-9]+', value_num):
                            value_num = int(value_num)
                if condition is not None and value_num > int(condition):
                    trace_print(f"Condition met: {columnPath} : {value_num} > {condition}")
                    return True
                else:
                    trace_print(f"Condition not met: {columnPath} : {value_num} <= {condition}")
            except ValueError:
                trace_print("Invalid column value; not a number.")
            return False
        return True

    def update_dimension(self, record, semPath, column, columnValue, whichLine, value, n, index):
        id = semPath[1 + semPath.rindex("/") :]
        self.dimension[id]["whichLine"] = whichLine
        ditto = False
        if index > 0 or ("*" in columnValue and value == self.dimension[id]["value"]):
            ditto = True
        if whichLine == '[+]':
            ditto = False
        self.dimension[id]["ditto"] = ditto
        if 0 == list(self.dimension.keys()).index(id):
            if not self.dimension[id]["ditto"]:
                self.dimension[id]["counter"] += 1
                for child in self.dimension[id]["descendant"]:
                    self.dimension[child]["counter"] = -1
                    self.dimension[child]["value"] = None
        else:
            parent_id = self.dimension[id]["parent"]
            if whichLine == '[+]':
                self.dimension[id]["counter"] += 1
            else:
                if self.dimension[parent_id]["ditto"]:
                    if '*' in self.dimension[id]['whichLine'] and 0 == index:
                        self.dimension[id]["counter"] += 1
                else:
                    self.dimension[id]["counter"] = 0
            for child in self.dimension[id]["descendant"]:
                self.dimension[child]["counter"] = -1
                self.dimension[child]["value"] = None
        if not value and '[*]' == whichLine:
            self.dimension[id]["value"] = ''
        elif '>' in value:
            self.dimension[id]["value"] = ''
        else:
            self.dimension[id]["value"] = value

        elements = self.split_path_ignoring_brackets(semPath)
        for i, element in enumerate(elements):
            if element not in self.dimension:
                continue
            extracted = self.extract_key(element)
            if id != extracted:
                continue
            counter = self.dimension[element]["counter"]
            value_selector = ""
            line_selector = ""
            if value:
                if "*" in whichLine:
                    line_selector = f"{whichLine.replace('*', str(counter))}"
                elif whichLine == '[+]':
                    line_selector = f"[{counter}]"
                if value:
                    if "*" in value:
                        value_selector = f"[{value.replace('*', columnValue)}]"
                    elif '>0' in value:
                        value_selector = f"[{value.replace('>0', f'={columnValue}')}]"
                    else:
                        if '[' in value:
                            value_ = value.strip("[]")
                            if '../' in value_:
                                # Extract all conditions of parent within brackets using regex
                                parent_dimension = self.dimension[elements[i-1]]
                                parent_element = parent_dimension['element']
                                parent_conditions = re.findall(r'\[(.*?)\]', parent_element)
                                # Extract the condition inside the child condition
                                new_condition = re.search(r'../(.*)', value_).group(1)                                
                                # Extract the element name from the new condition
                                element_name = re.match(r'([^=]+)', new_condition).group(1).strip()                                
                                # Extract conditions in the parent element
                                parent_conditions = re.findall(r'\[(.*?)\]', parent_element)                                
                                # Iterate over the parent conditions and replace as needed
                                new_conditions = []
                                for condition in parent_conditions:
                                    if element_name in condition:
                                        new_conditions.append(new_condition)
                                    else:
                                        new_conditions.append(condition)                                
                                # Reconstruct the parent element with the new conditions
                                element_base = re.match(r'^[^\[]*', parent_element).group(0)
                                new_parent_element = element_base + ''.join([f'[{cond}]' for cond in new_conditions])                                
                                # Update the dimension dictionary
                                parent_dimension['element'] = new_parent_element
                                value_selector = value
                        else:
                            value_selector = '' # f"[{value}]"
            path = f"{element}{line_selector}{value_selector}"
            self.dimension[id]["element"] = path
        return path

    def process_record(self, record, n):
        self.trace_print(f"\n** {n} {record['Column1']} {record['Column2']} {record['Column3'] if 'Column3' in record else ''} **")
        for item in self.sorted_binding:
            for cell, val in record.items():
                if cell:
                    record[cell] = self.escape(val)           
            column = item["column"]
            columnValue = item["value"].replace(' ','')
            datatype = item["datatype"]
            semPath = item["semPath"]
            whichLine = item["line"]
            # Analyze dimension bindongs
            if ',' in column:
                # Split the columns and columnValues
                column_names = [c.strip() for c in column.split(',')]
                # Pattern to match the parts within square brackets
                pattern = r'\[.*?\]'
                # Find all matches
                columnValues = re.findall(pattern, columnValue)
                # Create the dictionary
                columns = [{column_names[i]: columnValues[i]} for i in range(len(column_names)) if columnValues[i]]
            else:
                columns = [{column:columnValue}]
            # Iterate through the list of dictionaries
            for index, column_dict in enumerate(columns):
                for column, columnValue in column_dict.items():            
                    if self.isblank(columnValue) and '[*]' != whichLine:
                        self.trace_print(f"\nprocess_record {n} {column} is BLANK. '{item['name']}' {semPath} {columnValue and 'columnValue:' + columnValue or ''} {whichLine and 'line:' + whichLine or ''}")
                    else:
                        self.trace_print(f"\nprocess_record {n} {column}:{columnValue} '{item['name']}' {semPath} {columnValue and 'columnValue:' + columnValue or ''} {whichLine and 'line:' + whichLine or ''}")
                        value = record[column[1:]] if "d" == column[:1] else record[column]
                        if not self.check_column_condition(record, column, semPath, columnValue, value):
                            continue
                        if "d" == column[:1]:
                            if value and not self.isblank(value):
                                self.process_dimension_column(record, column, semPath, columnValue, whichLine, value, n, index)
                        else:
                            if value and not self.isblank(value):
                                self.process_element_column(record, column, datatype, semPath, value)

    def reflect_column_value(self, path, semPath):
        # Split the paths into segments
        path_segments = path.strip('/').split('/')
        semPath_segments = semPath.strip('/').split('/')
        # Create a dictionary to hold the segments and their conditions
        segment_conditions = {}
        for segment in semPath_segments:
            match = re.match(r'([^\[]+)(\[[^\]]+\])?', segment)
            if match:
                key = match.group(1)
                condition = match.group(2) if match.group(2) else ''
                segment_conditions[key] = condition
        # Construct the new path with conditions
        new_path = []
        for segment in path_segments:
            condition = segment_conditions.get(segment, '')
            new_path.append(f'{segment}{condition}')
        return '/' + '/'.join(new_path)

    def prepare_dimension_column(self, record, column, semPath, columnValue, whichLine, value, n, index):
        column = column[1:] if column.startswith("dColumn") else column
        column_sem_path = self.binding_dict[column]['semPath']
        revised_path = self.reflect_column_value(semPath, column_sem_path)
        revised_path_elements = revised_path.strip('/').split('/')
        path_elements = []
        for dimension_path in revised_path_elements:
            dimension_id = self.extract_key(dimension_path)
            if dimension_id not in self.dimension:
                path_elements.append(dimension_id)
                continue
            if dimension_id == self.extract_key(revised_path_elements[-1]):
                element = self.update_dimension(record, semPath, column, columnValue, whichLine, value, n, index)
                if not element:
                    return None
                path_elements.append(element)
            else:
                dimension = self.dimension[dimension_id]
                counter = dimension['counter']
                if counter < 0:
                    counter = 0
                    # Fix *** ERROR node with specified leading_part ['JP07a[1839]', 'JP08a[-1]'] condition BS04c6 must exists.
                dimension_path += f"[{counter}]"
                dimension_path = self.swap_patterns(dimension_path)
                path_elements.append(dimension_path)
        path = "/" + "/".join(path_elements)
        path = path.replace("//", "/")
        return path

    # Function to split XPath correctly considering brackets
    def split_xpath(self, xpath):
        # Regular expression to match '/' outside of brackets
        pattern = r'/(?![^\[]*\])'
        parts = re.split(pattern, xpath)
        return parts

    # Function to remove redundant parent conditions in XPath
    def remove_redundant_conditions(self, xpath):
        # Split the XPath into parts considering brackets
        parts = self.split_xpath(xpath.strip('/'))        
        # Iterate over each part of the XPath
        for i, part in enumerate(parts):
            # Check if the current part contains a condition (indicated by '[')
            if part and '[' in part:
                # Extract all conditions within brackets using regex
                current_conditions = re.findall(r'\[(.*?)\]', part)
                for condition in current_conditions:
                    # Check if the condition is about the parent element (indicated by '..')
                    if condition.startswith('../'):
                        # Determine the index of the parent part
                        parent_index = i - 1
                        # Get the parent part of the XPath
                        parent_part = parts[parent_index]
                        # Check if the parent part already contains the condition (without the '..' prefix)
                        if condition[3:condition.index('=')] in parent_part:
                            # Remove the redundant condition from the current part
                            part = part.replace(f'[{condition}]', '')
                # Update the current part in the list
                parts[i] = part
        # Join the parts back into a single XPath expression
        new_xpath = '/'.join(parts)        
        # Remove any empty brackets that may have been left behind
        new_xpath = re.sub(r'\[\]', '', new_xpath)        
        return new_xpath

    def process_dimension(self, path):
        elements = self.split_path_ignoring_brackets(path)
        revised_paths = self.refrect_dimension(elements)
        path = "/" + "/".join(revised_paths)
        self.set_dimension_value(path)

    def process_dimension_column(self, record, column, semPath, columnValue, whichLine, value, n, index):
        path = self.prepare_dimension_column(record, column, semPath, columnValue, whichLine, value, n, index)
        if path:
            if '../' in path:
                path = self.remove_redundant_conditions(path)
            self.trace_print(f"- process_dimension_column {column[1:]} {path}")
            self.process_dimension(path)

    def combine_queries(self, query1, query2):
        # Extract the base key from the first query
        base_key1 = query1.split("[")[0]
        base_key2 = query2.split("[")[0]
        # Check if both base keys are the same
        if base_key1 != base_key2:
            raise ValueError("The base keys of the two queries do not match.")
        # Extract the conditions from both queries
        conditions1 = re.findall(r"\[.*?\]", query1[len(base_key1) :])
        conditions2 = re.findall(r"\[.*?\]", query2[len(base_key2) :])
        # Separate numeric and non-numeric conditions
        non_numeric_conditions_dict = {}
        numeric_conditions = []
        for condition in conditions1 + conditions2:
            if re.search(r"^\[\d+\]$", condition):
                numeric_conditions.append(condition)
            else:
                key, value = self.split_key_value(re.findall(r"\[(.*?)\]", condition)[0])
                non_numeric_conditions_dict[key] = value
        # Give priority to query2 for non-numeric conditions
        for condition in conditions2:
            key, value = self.split_key_value(re.findall(r"\[(.*?)\]", condition)[0])
            if key in non_numeric_conditions_dict:
                non_numeric_conditions_dict[key] = value
        # Reconstruct non-numeric conditions
        non_numeric_conditions = [
            f"[{key}={value}]" for key, value in non_numeric_conditions_dict.items()
        ]
        # Combine the base key with both sets of conditions
        combined_query = (
            base_key1 + "".join(non_numeric_conditions) + "".join(numeric_conditions)
        )
        return combined_query

    def swap_patterns(self, input_string):
        # Define the regex patterns for ([key=val] or [not(...)]) and [number]
        key_val_pattern = re.compile(r'\[([^\[\]]*?=.*?|not\(.*?\))\]')
        number_pattern = re.compile(r'\[\d+\]')
        # Search for the patterns
        key_val_match = key_val_pattern.findall(input_string)
        number_match = number_pattern.search(input_string)
        if key_val_match and number_match:
            # Extract the matched patterns
            key_val = f"[{key_val_match[-1]}]"
            number = number_match.group()
            # Check if the number pattern comes before the key_val pattern
            number_index = input_string.index(number)
            key_val_index = input_string.index(key_val)
            if number_index < key_val_index:
                # Number pattern is before key_val pattern, return the original string
                return input_string
            # Replace the patterns in the original string
            result_string = input_string.replace(key_val, "PLACEHOLDER_KEY_VAL").replace(number, "PLACEHOLDER_NUMBER")
            # Swap the placeholders with the actual patterns
            result_string = result_string.replace("PLACEHOLDER_KEY_VAL", number).replace("PLACEHOLDER_NUMBER", key_val)
            return result_string
        else:
            return input_string  # Return the original string if patterns are not found

    # def is_object_defined(self, data, leading_part):
    #     try:
    #         current_level = data  # Start at the top-level dictionary
    #         for part in leading_part:
    #             # Split the key and index
    #             key, index = part.split('[')
    #             index = int(index[:-1])  # Remove the closing bracket and convert to int
    #             # Check if the key exists and navigate further
    #             if key not in current_level or index not in current_level[key]:
    #                 return False  # If key or index doesn't exist, return False
    #             # Descend into the next level
    #             current_level = current_level[key][index]
    #         return True  # If all levels exist, the object is defined
    #     except (KeyError, IndexError, ValueError, TypeError):
    #         return False  # Any error implies the object is not defined
        
    def refrect_dimension(self, leading_part):
        # Define the regex patterns for ([key=val] or [not(..)]) and [number]
        key_val_pattern = re.compile(r'\[([^\[\]]*?=.*?|not\(.*?\))\]')
        number_pattern = re.compile(r'\[\d+\]')
        new_leading_part = []
        for path in leading_part:
            new_path = path
            dim_id = self.extract_key(path)
            bindings = [x for x in self.binding_dict.values() if dim_id == x['id']]
            if not bindings:
                continue
            binding = bindings[0]
            value = binding['value']
            binding_value = '*' in value
            multiple_value_binding = len(self.extract_bracket_content(value)) > 1
            if dim_id not in self.dimension:
                continue
            dim = self.dimension[dim_id]
            match_key_val = key_val_pattern.findall(path)
            match_number = number_pattern.findall(path)
            if binding_value or ('whichLine' in dim and '*' in dim['whichLine']):
                num = int(match_number[-1].strip('[]')) if match_number else None
                counter = dim['counter']
                if num and int(num) != counter:
                    self.debug_print(f"** {num} {counter}")
                elif counter < 0:
                    match_element_number = number_pattern.findall(dim['element'])
                    element_num = int(match_element_number[-1].strip('[]')) if match_element_number else None
                    if None != element_num and int(element_num) != counter:
                        self.debug_print(f"** {element_num} {counter}")
                        counter = element_num
                new_path = f"{dim_id}[{counter}]"
            element = dim['element']
            if match_key_val and '[[' in element:
                pattern = re.compile(r"\[.*?\]")
                conditions = pattern.findall(element)
                for condition in conditions:
                    if re.match(key_val_pattern, condition):
                        if condition not in new_path:
                            new_path += condition
                        break
            elif multiple_value_binding:
                key_vals = self.extract_bracket_content(element)
                if len(key_vals) > 1:
                    if match_key_val:
                        new_path += f"[{match_key_val[-1]}]"
            if '][' in new_path:
                new_path = self.swap_patterns(new_path)
            new_leading_part.append(new_path)
        # if self.is_object_defined(self.tidy_data, new_leading_part):
        #     # Regular expression to find the last index in the path
        #     match = re.search(r'\[([0-9]+)\]$', new_leading_part)
        #     if match:
        #         # Extract the current index
        #         current_index = int(match.group(1))
        #         # Increment the index
        #         new_index = current_index + 1
        #         # Replace the last index with the incremented one
        #         new_leading_part = re.sub(r'\[([0-9]+)\]$', f'[{new_index}]', new_leading_part)
        #         self.debug_print(f"** incremented counter {new_leading_part}")
        #     else:
        #         self.debug_print("No index found in the last segment of the path")
        return new_leading_part

    def process_element_column(self, record, column, datatype, semPath, value):
        value = record[column]
        value = re.sub("\s+", " ", value).strip()
        value = self.check_date_format(value, datatype)
        if datatype not in [
            "Amount",
            "Monetary Amount",
            "Unit Price Amount",
            "Quantity",
            "Integer",
            "Numeric",
        ]:
            value = f"'{value}'"
        elements = self.split_path_ignoring_brackets(semPath)
        leading_part = elements[:-1]
        leaf_element = elements[-1]
        path_elements = self.refrect_dimension(leading_part)
        path_elements.append(f'{leaf_element}={value}')
        path = "/" + "/".join(path_elements)
        self.trace_print(f"- process_element_column {column} {path}")
        if '../' in path:
            path = self.remove_redundant_conditions(path)
        self.set_element_value(path)

    def split_key_value(self, condition):
        if "=" not in condition:
            return condition, None
        key, value = condition.split("=")
        value = value.strip("' \"")
        value = self.unescape(value)
        return key, value

    def check_node_condition(self, node, condition):
        match = re.search(r"\[.*?\]", condition)
        if match:
            query = match.group(0)
        else:
            query = condition
        if '[-1]' == query:
            return None
        k, v = self.split_key_value(query)
        if not v:
            return None
        v = self.unescape(v)
        if "&" not in v:
            if not node:
                found_node = {k: v}
                if isinstance(node, list):
                    node.append(found_node)
            else:
                found_node[k] = v
            return found_node
        else:
            if len(node) > 0 and isinstance(node[-1], list):
                node = node[-1]
            values = v.split('"&"')
            for value in values:
                if "__not__" == value:
                    new_node = {}
                else:
                    new_node = {k: value}
                # Check if the new element already exists in the list
                if new_node not in node:
                    node.append(new_node)
            return [node]

    def update_list_based_on_condition(self, lst, condition):
        if '=' not in condition:
            return None
        # Extract the key and value from the condition
        key, value = self.split_key_value(condition.strip("[]"))
        # Find the matching element in the list
        matching_items = [item for item in lst if item.get(key) == value]
        condition_exists = len(matching_items) > 0
        added = False
        if not condition_exists:
            if lst == [{}]:
                # If the list is [{}], assign new condition key, value
                lst[0][key] = value
            else:
                # Append the new condition to the list
                lst.append({key: value})
            added = True
            matching_item = lst[-1]
        else:
            # If the condition exists, return the matching item
            matching_item = matching_items[0]
        # Return the updated list and the matching or new condition
        return matching_item, added

    def set_dimension_value(self, path):
        node = self.tidy_data
        if not path:
            return
        query_elements = self.split_path_ignoring_brackets(path)
        self.debug_print(f"- set_dimension_value('{path}') query_elements:{query_elements})")
        if 1 == len(query_elements):
            key, conditions = self.split_query(query_elements[0])
            if key not in node:
                node[key] = []
            selected_node = node[key]
            if 1 == len(conditions):
                condition = conditions[0]
                if self.is_numeric_condition(condition):
                    num = int(condition)
                    while len(selected_node) <= num:
                        selected_node.append({})
                    return selected_node[num]
                else:
                    key_, value_ = self.split_key_value(condition)
                    if not isinstance(selected_node, list):
                        print(f"*** ERROR selected_node node[{key}] must be a list.")
                        return None
                    if 0 == len(selected_node) or value_ != selected_node[-1][key_]:
                        selected_node.append({key_: value_})
                    else:
                        pass
            else:
                print("*** ERROR condition must not multiple.")
                return None
        else:
            leading_part = query_elements[:-1]
            condition = query_elements[-1]
            if "&" in leading_part[-1]:
                pattern = r'\[\w+="[^"]*?"&"[^"]*?"\]'
                leading_part[-1] = re.sub(pattern, "", leading_part[-1])
            found_node = self.lookup(node, leading_part)
            if None == found_node:
                print(f"*** ERROR node with specified path {path} must exists.")
                return None
            if isinstance(found_node, dict):
                key_, conditions_ = self.split_query(condition)
                if key_ not in found_node:
                    if 2 == len(conditions_):
                        num = conditions_[0]
                        num = int(num)
                        k, v = self.split_key_value(conditions_[1])
                        found_node[key_] = [[{k: v}]]
                    elif 1 == len(conditions_):
                        found_node[key_] = [{}]
                    elif 0 == len(conditions_):
                        found_node[key_] = [{}]
                        return found_node[key_]
                    else:                        
                        self.trace_print(f"** NOTSUPPORTED set_dimension_value key:{key_} conditions:{ conditions_}")
                        return None
                else:
                    if 2 == len(conditions_):
                        num = conditions_[0]
                        num = int(num)
                        while len(found_node[key_]) <= num:
                            found_node[key_].append([])
                        if 'not' in conditions_[1]:
                            found_node[key_][num].append({})
                        else:
                            k, v = self.split_key_value(conditions_[1])
                            v = v.strip("'\"")
                            found_node[key_][num].append({k: v})
                selected_node_ = found_node[key_]
                if not isinstance(selected_node_, list):
                    print("*** ERROR node with specified condition must be a list.")
                    return None
                condition_ = conditions_[0] if conditions_ else ""
                query = condition_
                if '-1' == query:
                    return selected_node_[-1]
                if self.is_numeric_condition(query):
                    num = int(query)
                    if num > len(selected_node_) - 1:
                        selected_node_.append({})
                        found_node_ = selected_node_[-1]
                    else:
                        found_node_ = selected_node_[num]
                    if len(conditions_) > 1 and conditions_[1:]:
                        found_node_ = self.lookup(found_node_, conditions_[1:])
                    return found_node_
                elif '=' in query:
                    new_element, added = self.update_list_based_on_condition(
                        selected_node_, query
                    )
                    # Check if an empty dictionary {} exists in the list found_node[key_]
                    if {} in found_node[key_]:
                        # If an empty dictionary is found, replace it with the new_element
                        found_node[key_][found_node[key_].index({})] = new_element
                    else:
                        # If no empty dictionary is found
                        # Check if new_element is not already in the list found_node[key_]
                        if new_element not in found_node[key_]:
                            # If new_element is not in the list, append it to the list
                            found_node[key_].append(new_element)
                    self.debug_print(f"- set_dimension_value({path}) {new_element} added:{added}")
                    return new_element
                else:
                    pass
            elif isinstance(found_node, list):
                found_node = self.check_node_condition(found_node, condition)
                return found_node[-1] if isinstance(found_node, list) else None

    def set_element_value(self, path):
        if not path:
            return
        query_elements = self.split_path_ignoring_brackets(path)
        leading_part = query_elements[:-1]
        condition = query_elements[-1]
        key, value = self.split_key_value(condition)
        node = self.tidy_data
        found_node = self.lookup(node, leading_part)
        self.debug_print(f"- set_element_value path:{path} {query_elements} {found_node}")
        if isinstance(found_node, dict):
            found_node[key] = value
        else:
            pass

    def lookup(self, node, query_elements):
        self.debug_print(f"lookup query_elements:{query_elements}")
        first, *rest = query_elements
        if ('__any__' == first or '*' == first) and not rest:
            return node[-1]
        found_node = None
        if isinstance(node, dict):
            key = self.extract_key(first)
            search_condition = self.extract_bracket_content(first)
            if not search_condition[0]:
                if '*' == key:
                    node.append([])
                    selected_node = found_node = node[-1]
                elif key not in node:
                    node[key] = [{}]
                else:
                    selected_node = found_node = node[key]
                key = None
            else:
                for query in search_condition:
                    condition = query.strip("[]")
                    if key and key not in node:
                        node[key] = []
                        if self.is_numeric_condition(condition):
                            if len(search_condition) > 1:
                                num = int(condition)
                                while len(node[key]) <= num:
                                    node[key].append({})
                                value_condition = search_condition[1]
                                self.check_node_condition(node[key][num], value_condition)
                            if len(node[key]) == 0:
                                node[key].append({})
                            return node[key][-1]
                        else:
                            if '=' in condition:
                                key_, value_ = self.split_key_value(condition)
                                node[key].append({key_: value_})
                            else:
                                pass
                    if key:
                        if key not in node:
                            node[key] = {}
                        if 1==len(search_condition):
                            query = search_condition[0]
                            if query.isdigit():
                                num = int(query)
                                while len(node[key]) <= num:
                                    node[key].append({})
                                found_node = node[key][num]
                            else:
                                if '=' in query:
                                    key_, value_ = self.split_key_value(query)
                                    node[key][-1][key_] = value_
                                    found_node = node[key][-1]
                                else:
                                    pass
                        else:
                            found_node = node[key]
                        key = None
                    elif "not" in condition:
                        pattern = r"not\((.*?)\)"
                        match = re.search(pattern, condition)
                        if match:
                            extract_key = match.group(1)
                            # Check if selected_node is a list of lists
                            if isinstance(selected_node[0], list):
                                # If it's a list of lists, look at the last list
                                last_list = selected_node[-1]
                                found_node = next(
                                    (item for item in last_list if extract_key not in item),
                                    None,
                                )
                                if not found_node and {} != found_node:
                                    found_node = {}
                                    last_list.append(found_node)
                            else:
                                # Otherwise, look directly in the list
                                found_node = next(
                                    (item for item in selected_node if extract_key not in item),
                                    None,
                                )
                                if not found_node and {} != found_node:
                                    found_node = {}
                                    selected_node.append(found_node)
                    elif self.is_numeric_condition(condition):
                        num = int(condition)
                        while len(selected_node) <= num:
                            found_node = {}
                            selected_node.append(found_node)
                    else:
                        key, value = self.split_key_value(condition)
                        if selected_node == [{}]:
                            found_node[key] = value
                        else:
                            if key=='__any__':
                                found_node = selected_node[-1]
                            elif isinstance(selected_node, list) and isinstance(
                                selected_node[-1], list
                            ):
                                """
                                In the following case
                                [
                                    [
                                        {'JP05a_GL03_04': 'D', 'CC05gK_01': '20392404', 'JP13a_BS16_01': '150', 'JP13a_BS16_02': '受取手形'},
                                        {'JP05a_GL03_04': 'C', 'CC05gK_01': '20392404', 'JP13a_BS16_01': '152', 'JP13a_BS16_02': '売掛金'},
                                        {'JP05a_GL03_03': '4月25日伝票No201今井百貨店'}
                                    ]
                                ]
                                """
                                selected_node = selected_node[-1]
                                found_node = next(
                                    (
                                        item
                                        for item in selected_node
                                        if item.get(key) == value
                                    ),
                                    None,
                                )
                                # If the element is not found, add a new element with the key and value
                                if not found_node:
                                    found_node = {key: value}
                                    selected_node.append(found_node)
                    selected_node = found_node
            if not rest:
                return found_node
            return self.lookup(found_node, rest)
        elif isinstance(node, list):
            key, conditions = self.split_query(first)
            node_ = node
            if len(conditions) > 0:
                for condition in conditions:
                    search_condition = self.extract_bracket_content(condition)
                    if len(search_condition) > 1:
                        pass
                    if search_condition[0]:
                        query = search_condition[0]
                    else:
                        query = condition
                    if self.is_numeric_condition(query):
                        node_ = node_[int(query)]
                    else:
                        key, value = self.split_key_value(query)
                        node_ = [x for x in node_ if value == x[key]]
            else:
                if '=' in first:
                    key, value = self.split_key_value(first)
                    node_ = [x for x in node_ if value == x[key]]
                else:
                    # Define the regular expression pattern
                    pattern = r'not\((.*?)\)'
                    # Search for the pattern in the string
                    match = re.search(pattern, first)
                    # Extract the content inside the parentheses if a match is found
                    if match:
                        key = match.group(1)
                        node_ = [d for d in node_ if key not in d]
                    else:
                        print("- lookup query_elements doesn't match not\((.*?)\)")
                        return None
            found_node = node_[-1]
            if not rest:
                return found_node
            return self.lookup(found_node, rest)


def debug_print(message):
    if DEBUG:
        print(message)


def trace_print(message):
    if TRACE:
        print(message)


def file_path(pathname):
    if SEP == pathname[0:1]:
        return pathname
    else:
        pathname = pathname.replace("/", SEP)
        dir = os.path.dirname(__file__)
        new_path = os.path.join(dir, pathname)
        return new_path


def read_lhm_file(LHM_file, encoding=encoding):
    """
    Reads the Logical Hierarchical Model (LHM) file and returns its structure as a dictionaries.
    Parameters:
    - LHM_file: Path to the LHM CSV file.
    Returns:
    - A dictionary represents a hierarchical message definition.
    """
    with open(LHM_file, mode="r", encoding=encoding) as file:
        csv_reader = csv.DictReader(file, fieldnames=LHM_header)
        next(csv_reader)  # Skip the header line
        seq = 1000
        for row in csv_reader:
            seq += 1
            row["sequence"] = seq
            if None in row:
                del row[None]
            semantic_dict[seq] = row
    return semantic_dict


def read_binding_file(binding_file, encoding=encoding):
    """
    Reads the binding file and returns its structure as a dictionaries, list, and its header.
    Parameters:
    - binding_file: Path to the binding CSV file.
    Returns:
    - A dictionary represents a binding definition.
    - A header of binding list
    """
    with open(binding_file, mode="r", encoding=encoding) as file:
        csv_reader = csv.DictReader(file, fieldnames=binding_header)
        next(csv_reader)  # Skip the header line
        for row in csv_reader:
            # if row['column'] and row['semPath']:
            binding_dict[row["column"]] = row

    if '' in binding_dict:
        del binding_dict['']

    if None in binding_dict:
        del binding_dict[None]

    csv_column_names = [
        {x["column"]: x["name"]} for k, x in binding_dict.items()  if k and "d" != k[0]
    ]
    csv_columns = {}
    for d in csv_column_names:
        csv_columns.update(d)
    data_header = list(csv_columns.keys())
    return binding_dict, data_header


def sort_headers_by_semSort(header, semantic_dict):
    # Dictionary to store the semSort value for each header
    header_sort_values = {}
    for h in header:
        for key, value in binding_dict.items():
            if value["semPath"].endswith(h):
                header_sort_values[h] = int(value["semSort"])
                break
    sorted_headers = sorted(
        header, key=lambda x: header_sort_values.get(x, float("inf"))
    )
    return sorted_headers


def transform_id(id):
    if "_" in id:
        prefix, suffix = id.split("_", 1)
        # Use regex to extract the uppercase letters and numbers part
        match = re.match(r"^[A-Z0-9]+", prefix)
        if match:
            new_prefix = match.group(0)
            return f"{new_prefix}_{suffix}"
    # For IDs without an underscore or if no match is found, return the original ID
    match = re.match(r"^[A-Z0-9]+", id)
    if match:
        new_id = match.group(0)
        return new_id
    return id


def tidy_to_csv(data, filename, encoding="utf-8-sig"):
    global dim_level
    global dim_line

    processor = DataProcessor(binding_dict)
    trace_print("Converts a tidy_data dictionary to flattened CSV.")
    # debug_print(f"{json.dumps(data)}\n")

    processor.flatten_dict(data)
    data_line = processor.get_data_line()

    # Get the sorted headers
    dim_header = list(dim_line.keys())
    data_header = list(data_line)
    semantic_sort_dict = {x["id"]: x["sequence"] for x in semantic_dict.values()}
    sorted_header = sorted(data_header, key=lambda item: semantic_sort_dict[item])
    header = dim_header + sorted_header

    records = processor.get_records()
    with open(filename, "w", newline="", encoding=encoding) as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        for record in records:
            row = {}
            data_exists = False
            for id, d in record.items():
                if id in dim_line:
                    id_ = re.sub(r"\[.*?\]", "", id)
                    if d and "0" != str(d):
                        row[id_] = d
                else:
                    data_exists = True
                    row[id] = d
            if data_exists:
                writer.writerow(row)

    return header


def fill_json_meta(out_csv, out_json, header):
    document_info = {
        "documentType": "https://xbrl.org/2021/xbrl-csv",
        "namespaces": {
            "cor": "http://www.iso.org/iso21926",
            "ns0": "http://www.example.com",
            "link": "http://www.xbrl.org/2003/linkbase",
            "iso4217": "http://www.xbrl.org/2003/iso4217",
            "xsi": "http://www.w3.org/2001/XMLSchema-instance",
            "xbrli": "http://www.xbrl.org/2003/instance",
            "xbrldi": "http://xbrl.org/2006/xbrldi",
            "xlink": "http://www.w3.org/1999/xlink",
        },
        "taxonomy": ["../../taxonomy/core.xsd"],
    }

    table_templates = {}
    cor_template = {"columns": {}, "dimensions": {}}
    dimensions = []
    sorted_columns = {}

    for column_path in header:
        binding = None
        datatype = None
        is_monetary = False
        for x in binding_dict.values():
            path = x["path"]
            if len(path) > 0 and column_path == path[1 + path.rindex("/") :]:
                binding = x
                datatype = binding["datatype"]
                term = binding["term"]
                if 'Decimal' == datatype and 'Amount' in term:
                    is_monetary = True
                break

        if binding is None:
            data = [
                x
                for x in semantic_dict.values()
                if x["path"] is not None and x["path"].endswith(column_path)
            ]
            if len(data) > 0 and "representation" in data[0]:
                datatype = data[0]["representation"]

        if not re.match("^.*_[0-9]+$", column_path):
            cor_template["columns"][column_path] = {}
            dimensions.append(column_path)
            sorted_columns[column_path] = cor_template["columns"][column_path]
        else:
            concept_name = column_path
            dimensions_obj = {"concept": f"cor:{concept_name}"}
            if is_monetary:
                dimensions_obj["unit"] = "iso4217:JPY"
            sorted_columns[column_path] = {"dimensions": dimensions_obj}
    sorted_columns_keys = sorted(sorted_columns.keys())
    for key in sorted_columns_keys:
        cor_template["columns"][key] = sorted_columns[key]
    for dimension in dimensions:
        cor_template["dimensions"][f"cor:d_{dimension}"] = f"${dimension}"
    cor_template["dimensions"]["period"] = "2024-03-01T00:00:00"
    cor_template["dimensions"]["entity"] = "ns0:Example co."

    table_templates["iso21926_template"] = cor_template

    tables = {}
    cor_table = {
        "template": "iso21926_template",
        "url": out_csv[1 + out_csv.rindex(SEP) :],
    }
    tables["iso21926_table"] = cor_table

    json_obj = {
        "documentInfo": document_info,
        "tableTemplates": table_templates,
        "tables": tables,
    }

    if DEBUG:
        json_string = json.dumps(json_obj, indent=4)
        print(json_string)

    with open(out_json, "w") as file:
        json.dump(json_obj, file, indent=4)
        trace_print(f"JSON object written to {out_json}")


def main():
    global DEBUG
    global TRACE
    global encoding
    global binding_dict
    global dim_level
    global dim_line
    global dimension

    parser = argparse.ArgumentParser(
        prog="csv2tidy.py",
        usage="%(prog)s infile -o outfile -m lhm_file -b binding_file -e encoding [options] ",
        description="Converts proprietary CSV to hierarchical tidy data CSV format.",
    )
    parser.add_argument(
        "inFile", metavar="infile", type=str, help="Input proprietary CSV file path"
    )
    parser.add_argument(
        "-o", "--outfile", required=True, help="Output proprietary CSV file path"
    )
    parser.add_argument("-m", "--lhm_file", required=True, help="LHM file path")
    parser.add_argument("-b", "--binding_file", required=True, help="Binding file path")
    parser.add_argument("-e", "--encoding", required=False, default="utf-8-sig", help="File encoding, default is utf-8-sig")
    parser.add_argument("-t", "--trace", required=False, action="store_true")
    parser.add_argument("-d", "--debug", required=False, action="store_true")

    args = parser.parse_args()

    in_file = args.inFile.strip()
    in_file = in_file.replace("/", SEP)
    in_file = file_path(args.inFile)
    if not in_file or not os.path.isfile(in_file):
        print("No input CSV file.")
        sys.exit()
    data_file = in_file

    if args.outfile:
        out_file = args.outfile.strip()
        out_file = out_file.replace("/", SEP)
        out_file = file_path(out_file)
        out_json = f"{out_file[:-3]}json"

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

    dataList = []
    with open(data_file, mode="r", encoding="utf-8-sig") as file:
        csv_reader = csv.DictReader(file, fieldnames=data_header)
        pattern = r"^(\/|-|\d)+$" # スラッシュ、ハイフン、および数字のみで構成されており、他の文字が含まれていない
        for row in csv_reader:
            # Noneキーが存在する場合、それを削除
            if None in row:
                del row[None]
            if bool(re.match(pattern, list(row.values())[0])):
                dataList.append(row)

    converter = StructuredCSV(binding_dict, semantic_dict)

    # Find keys starting with 'dColumn' and having line: '[*]'
    line_key = [
        key[1:] for key, value in binding_dict.items()
        if key.startswith('dColumn') and value.get('line') == '[*]'
    ]
    # Update dataList
    for row in dataList:
        for key in line_key:
            if key in row and row[key] == '':
                row[key] = '\u3000'  # Replace empty string with full-width space

    for n, record in enumerate(dataList):
        converter.process_record(record, n)

    dim_data = [
        {x["semPath"].split("/")[-1]: len(x["semPath"].split("/")) - 2}
        for k, x in binding_dict.items()
        if k and "d" == k[0]
    ]
    dim_level = {}
    for d in dim_data:
        dim_level.update(d)
    dim_line = {}
    for k in dim_level.keys():
        dim_line.update({k: 0})

    print(f"\n** tidy data to {out_file}")

    header = tidy_to_csv(converter.tidy_data, out_file, encoding)

    fill_json_meta(out_file, out_json, header)

    print(f"** END converted {data_file} to {out_file}")

if __name__ == "__main__":
    main()
