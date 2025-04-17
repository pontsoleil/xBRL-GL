#!/usr/bin/env python3
# coding: utf-8
"""
awi21926specialization.py
Generates ADC Business Semantic Model (BSM) CSV file from Foundational Semantic Model (FSM) CSV file with Specialization

Designed by SAMBUICHI, Nobuyuki (Sambuichi Professional Engineers Office)
Written by SAMBUICHI, Nobuyuki (Sambuichi Professional Engineers Office)

Creation Date: 2025-01-17

MIT License

(c) 2023-2025 SAMBUICHI, Nobuyuki (Sambuichi Professional Engineers Office)

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

ABOUT THIS SCRIPT
These Python scripts are specifically designed for handling the ADS graph walk in two distinct steps, namely `awi21926specialization.py` and `awi21926graphwalk.py`.

This first program, `awi21926specialization.py`, has a primary focus on specialization and property extension within the Foundational Semantic Model (FSM), efficiently processing these aspects to generate a Business Semantic Model (BSM) suitable for further usage or analysis. Specialization allows adding, changing, or removing properties defined in the superclass. Removing a property involves defining its multiplicity as "0..0" or "0" for attributes or associations in the subclass.

Key Features:
1. Initial Setup:
   - Imports necessary modules and sets up debugging flags and file path separators.
   - Defines directories and filenames for both FSM and BSM CSV files.

2. Utility Functions:
   - parse_class(class_term, SP_ID=''): Function to parse class terms and handle specializations.
   - file_path(pathname): Creates full file paths from given pathnames, considering relative and absolute paths.
   - is_file_in_use(file_path): Checks if a file is currently in use.
   - getproperty_term(record): Forms a property term from the record, appending 'associated_class' if it exists.
   - populate_record(row, seq): Transforms a CSV row into a record, updating module and class identifiers accordingly.
   - check_csv_row(row): Validates the CSV row against mandatory and conditional checks.

3. Specialization Handling:
   - Read the Foundational Semantic Model (FSM) CSV and construct an object class dictionary with class terms and their properties.
   - Parse each class term, focusing on handling specializations with parse_class().
   - Process subclass properties and handle the hierarchy of properties and associations.

4. Business Semantic Model Generation and Output:
   - After processing the specialization and extensions, the script generates the Business Semantic Model (BSM).
   - The BSM is then written to a CSV file, capturing the updated class hierarchy and property details.

5. Debugging and Tracing:
   - Uses DEBUG and TRACE flags to print diagnostic messages, aiding in understanding the flow and for troubleshooting purposes.

Example Usage:
Python awi21926specialization.py AWI21926_FSM.csv AWI21926_BSM.csv -s JP_FSM.csv -l JP_BSM.csv

Where:
- The first parameter is the input FSM file.
- The second parameter is the output BSM file.
- `-s` option specifies the input extension FSM file.
- `-l` option specifies the output extension BSM file.

This script is tailored to handle complex relationships in the Foundational Semantic Model (FSM), focusing on class specialization and property extension. It efficiently processes these aspects to generate a Business Semantic Model (BSM) suitable for further usage or analysis.
"""
import os
import argparse
import sys
import csv
import re
import copy

from common.utils import (
    LC3,
    file_path,
    is_file_in_use,
    split_camel_case,
    abbreviate_term,
    normalize_text
)

class Specialization:
    def __init__(
            self,
            fsm_file,
            bsm_file,
            fsm_file_extension,
            bsm_file_extension,
            encoding,
            trace,
            debug
        ):
        self.fsm_file = fsm_file.replace('/', os.sep)
        self.fsm_file = file_path(self.fsm_file)
        if not self.fsm_file or not os.path.isfile(self.fsm_file):
            print(f'[INFO] No input Semantic file {self.fsm_file}.')
            sys.exit()

        self.bsm_file = bsm_file.replace('/', os.sep)
        self.bsm_file = file_path(self.bsm_file)
        if 'IN_USE' == is_file_in_use(self.bsm_file):
            print(f'[INFO] Semantic file {self.bsm_file} is in use.')
            sys.exit()

        self.fsm_file_extension = None
        if fsm_file_extension:
            self.fsm_file_extension = fsm_file_extension.replace('/', os.sep)
            self.fsm_file_extension = file_path(self.fsm_file_extension)
            if not self.fsm_file_extension or not os.path.isfile(self.fsm_file_extension):
                print('[INFO] No input Semantic extension file.')

        self.bsm_file_extension = None
        if bsm_file_extension:
            self.bsm_file_extension = bsm_file_extension.strip()
            self.bsm_file_extension = self.bsm_file_extension.replace('/', os.sep)
            self.bsm_file_extension = file_path(self.bsm_file_extension)
            if self.bsm_file_extension and (not self.fsm_file_extension or not os.path.isfile(self.fsm_file_extension)):
                print('[INFO] No input Semantic extension file.')
                sys.exit()
            elif self.fsm_file_extension:
                print('[INFO] Input Semantic extension file exists')
            if 'IN_USE' == is_file_in_use(self.bsm_file_extension):
                sys.exit()

        self.encoding = encoding if encoding else "utf-8-sig"
        self.TRACE = trace
        self.DEBUG = debug

        # Define CSV headers
        self.header  = ['sequence', 'level', 'property_type', 'identifier', 'class_term', 'property_term', 'representation_term', 'associated_class', 'multiplicity', 'definition', 'module', 'element', 'label_local', 'definition_local', 'xpath', 'table', 'domain_name']
        self.header2 = ['sequence', 'level', 'property_type', 'identifier', 'class_term', 'property_term', 'representation_term', 'associated_class', 'multiplicity', 'definition', 'module', 'table', 'domain_name', 'element', 'label_local', 'definition_local', 'xpath', 'id']

        # Initialize dictionaries and lists
        self.domain_dict = None
        self.object_class_dict = None
        self.current_module = None
        self.current_class = None
        self.module_num = {}
        self.class_num = None
        self.specialized_class = set()
        self.LIFO_list = []
        self.BSM_list = []

        # Define module dictionary for mapping module names to codes
        self.module_dict = {
            'Unit Type Registry': 'UT',
            'Core': 'CO',
            'General': 'GE',
            'Base': 'BS',
            'GL': 'GL',
            'General Ledger': 'GL',
            'AP': 'AP',
            'Accounts Payable': 'AP',
            'Purchase': 'PR',
            'AR': 'AR',
            'Accounts Receivable': 'AR',
            'Sales': 'SL',
            'Inventory': 'IV',
            'PPE': 'PE',
            'Property Plant Equipment': 'PE',
            'gl-gen': 'GE',
            'gl-cor': 'CO',
            'gl-bus': 'BU',
            'gl-ehm': 'EH',
            'gl-muc': 'MC',
            'gl-srcd': 'SR',
            'gl-taf': 'TA',
            'gl-usk': 'UK',
            'gl-jpn': 'JP',
        }

        self.module_dict['JP'] = 'JP'

    def debug_print(self, text):
        if self.DEBUG:
            print(text)

    def trace_print(self, text):
        if self.TRACE or self.DEBUG:
            print(text)

    def merge_class_term_with_element(self, class_term, element):
        if not element:
            return ""
        prefix, localname = element.split(':')
        class_words = re.split(r'\s+', class_term.strip())
        local_words = split_camel_case(localname)
        # Remove duplicate words (case-insensitive)
        remaining_words = [w for w in local_words if w.lower() not in [cw.lower() for cw in class_words]]
        # If all words are removed and the result is empty, keep the last word of the local name
        if not remaining_words and local_words:
            remaining_words = [local_words[-1]]
        # LC3 conversion
        class_prefix = LC3(class_term)
        if remaining_words:
            suffix = remaining_words[0].capitalize() + ''.join(w.title() for w in remaining_words[1:])
            new_localname = class_prefix + suffix
        else:
            new_localname = class_prefix
        return f"{prefix}:{new_localname}"

    def getproperty_term(self, record):
        property_type = record['property_type']
        if len(record['associated_class']) > 0:
            if record['property_term']:
                return property_type, f"({record['property_term']}) {record['associated_class']}"
            else:
                return property_type, record['associated_class']
        else:
            return property_type, record['property_term']

    # Utility function to transform a CSV row into a record
    def populate_record(self, row, seq):
        record = {}
        property_type = row['property_type']
        class_term = row['class_term'].replace('  ', ' ').strip()
        module = row['module']
        module_id = None
        if module in self.module_dict:
            module_id = self.module_dict[module]
        if self.current_class != class_term:
            if module_id not in self.module_num:
                self.module_num[module_id] = []
            if not class_term in self.module_num[module_id]:
                self.module_num[module_id].append(class_term)
            self.class_num = 1 + self.module_num[module_id].index(class_term)
        if 'Specialization' == property_type:
            id = f"{module_id}{str(self.class_num).zfill(2)}_00"
        else:
            if property_type.lower().endswith('class'):
                seq = 0
                id = f"{module_id}{str(self.class_num).zfill(2)}"
            else:
                id = f"{module_id}{str(self.class_num).zfill(2)}_{str(seq).zfill(2)}"
            seq += 1
        record['id'] = id
        record['sequence'] = row['sequence']
        record['identifier'] = row['identifier']
        module = row['module']
        record['module'] = module
        if row['table'] and row['table'].isdigit():
            table = int(row['table'])
        else:
            table = 0
        record['table'] = int(table)
        record['property_type'] = property_type
        if 'class' in property_type.lower():
            record['level'] = 1
        else:
            record['level'] = 2
        record['class_term'] = class_term
        property_term = row['property_term']
        property_term = property_term and property_term.replace('  ', ' ').strip() or ''
        record['property_term'] = property_term
        associated_class = row['associated_class']
        record['associated_class'] = associated_class and associated_class.replace('  ', ' ').strip() or ''
        record['representation_term'] = row['representation_term']
        definition = row['definition']
        record['definition'] = definition
        record['multiplicity'] = row['multiplicity']
        record['domain_name'] = row['domain_name']
        record['label_local'] = row['label_local']
        record['definition_local'] = row['definition_local']
        element = row['element']
        # if not element and 'Attribute'==property_type:
        #     local_name = LC3(' '.join([x for x in property_term.split()]))
        #     element = f"{module}:{local_name}"
        record['element'] = element
        record['xpath'] = row['xpath']
        # self.current_class = module
        self.current_class = class_term
        if self.DEBUG:
            if associated_class:
                print(f"{seq} module:{module} class_term:'{class_term}' id:{id} {property_type} associated_class:'{associated_class}'")
            elif property_term:
                print(f"{seq} module:{module} class_term:'{class_term}' id:{id} property_term:'{property_term}'")
            else:
                print(f"{seq} module:{module} class_term:'{class_term}' id:{id}")
        return seq, record

    # Function to parse class terms and handle specializations
    def parse_class(self, class_term, SP_ID=''):
        self.debug_print(f"\nparse_class('{class_term}')")
        """
        Step 1: Copy a class to the logical data model and place it on the top of 
        the LIFO list.
        """
        if class_term not in self.object_class_dict:
            self.trace_print(f"#### '{class_term}' not in object_class_dict")
            return
        object_class = self.object_class_dict[class_term]
        classID = object_class['id']
        property_type = object_class['property_type']
        if SP_ID:
            self.LIFO_list[-1] += f".{class_term}"
            classID = f"{SP_ID[:4]}{classID}"
            self.trace_print(f"  '{class_term}' type:'{property_type}' SP_ID:{SP_ID}\t{self.LIFO_list}")
        else:
            self.LIFO_list.append(class_term)
            self.trace_print(f"  '{class_term}' type:'{property_type}'\t{self.LIFO_list}")
        level = len(self.LIFO_list)
        properties = object_class['properties']
        object_class_ = {k: v for k, v in object_class.items() if k != 'properties'} # drop 'properties' from dict
        if 'Abstract Class' == object_class_['property_type']:
            if '.' in self.LIFO_list[0]:
                object_class_['property_type'] = 'Specialized Class'
                current_class_term = self.LIFO_list[0]
                class_term_ = current_class_term[:current_class_term.index('.')]
                if class_term_ not in self.object_class_dict:
                    object_class_ = None
                    print(f"ERROR: {class_term_} is not defined.")
                else:
                    self.current_class = self.object_class_dict[class_term_]
                    object_class_['associated_class'] = object_class_['class_term']
                    object_class_['class_term'] = current_class_term
                    object_class_['id'] = f"{self.current_class['id']}_{object_class_['id']}"
                    object_class_['module'] = self.current_class['module']
            else:
                pass
        if object_class_:
            # if 'Specialization' != object_class_['property_type']:
            if not SP_ID:
                self.BSM_list.append(object_class_)
        """
        A. Specialization. 
        if it at least one of its specializations contains information that will be in the
        message format or is on a path of associations toward a class that contains such 
        information, then choose the specialized class.
        """
        subClasses = [property for property in properties.values() if 'Specialization' == property['property_type'] and 1 == level]
        for property in subClasses:
            self.specialized_class.add(class_term)
            superclass_term = property['associated_class']
            if not superclass_term in self.LIFO_list:
                self.parse_class(superclass_term, classID)
        """
        B. Copy the class to the logical data model. 
        Copy all properties and associations to the logical data model. 
        Conventionally, properties not related to the associated object class should be placed 
        before them, but this is not a requirement.
        """
        for property in [property for property in properties.values() if 'Specialization' != property['property_type']]:# or level > 1]:
            _property = copy.deepcopy(property)
            if SP_ID:
                current_class_term = self.LIFO_list[0]
                _property['class_term'] = current_class_term
                self.current_class = self.object_class_dict[current_class_term[:current_class_term.index('.')]]
            else:
                self.current_class = object_class
            current_class_id = self.current_class['id']
            if current_class_id not in _property['id']:
                _property['id'] = f"{current_class_id}_{_property['id']}"
            _property['module'] = self.current_class['module']
            """
            1. Searches for elements in BSM_list where:
                "class_term" start with _property["class_term"]
                "property_term" is _property["property_term"]
            2. If a match is found and its "multiplicity" is "0", the element is removed.
            3. If the "multiplicity" is not "0", the matching element is replaced with _property.
            4. If no matching element is found, the script adds _property to BSM_list.
            """
            # Check if there are any matching elements
            match_index = None
            for index, element in enumerate(self.BSM_list):
                if (
                    element["property_type"] == _property["property_type"]
                    and element["class_term"]==_property["class_term"]
                    and (
                        (
                            "Attribute" == _property["property_type"]
                            and element["property_term"] == _property["property_term"]
                        )
                        or (
                            _property["property_type"] in ["Reference Association", "Composition", "Aggregation"]
                            and element["property_term"] == _property["property_term"]
                            and element["associated_class"] == _property["associated_class"]
                        )
                    )
                ):
                    match_index = index
                    break
            if match_index is not None:
                # If match found, check the multiplicity
                if "0" == _property["multiplicity"]:
                    # Remove element if multiplicity is "0"
                    del self.BSM_list[match_index]
                else:
                    # Replace element with _property
                    self.BSM_list[match_index] = _property
            else:
                # If no match is found, add _property
                if "0" != _property["multiplicity"]:
                    self.BSM_list.append(_property)
            if self.DEBUG:
                if _property['property_term']:
                    if _property['associated_class']:
                        print(f"  {_property['class_term']} | {_property['property_type']}: {_property['property_term']}.{_property['associated_class']}")
                    else:
                        print(f"  {_property['class_term']} | {_property['property_type']}: {_property['property_term']}")
                else:
                    print(f"  {_property['class_term']} | {_property['property_type']}: {_property['associated_class']}")
        self.debug_print(f"-- Done {self.LIFO_list[-1]}")
        if SP_ID:
            self.debug_print(f"Specialised Class: {class_term} type is '{property_type}'\t{self.LIFO_list}")
        else:
            self.LIFO_list.pop(-1)
            self.debug_print(f"POP LIFO_list: '{class_term} type is '{property_type}'\t{self.LIFO_list}")

    # Function to check the validity of CSV rows
    def check_csv_row(self, row):
        """
        1. Check Mandatory Fields: Ensure that each row contains 'module', 'property_type',
        'class_term'.
        2. Conditional Checks Based on 'property_type':
        - If 'property_type' contains 'Class', then 'property_term', 'representation_term', and 
            'associated_class', should be empty.
        - If 'property_type' contains 'Attribute', then 'property_term' and 
            'representation_term' should not be empty.
        - Additional checking can be added for other types like 'Reference', 
            'Aggregation', 'Composition', 'Specialization' then 'associated_class', 
            should not be empty.
        """
        status = False
        property_type = row['property_type']
        multiplicity = row['multiplicity']
        if 'Class' not in property_type:
            if not multiplicity or multiplicity not in ['1', '1..1', '1..*', '0..1', '0..*', '0..0', '0']:
                return status, f"Multiplicity '{multiplicity}' is WRONG."
        # Check for mandatory fields
        for field in ['module', 'property_type', 'class_term']:
            if not row.get(field):
                return status, f"Missing mandatory field '{field}'."
        # Conditional checks based on 'property_type'
        if 'Class' in property_type:
            for field in ['property_term', 'representation_term', 'associated_class']:
                if row.get(field):
                    return status, f"Field '{field}' must be empty for type {property_type}."
        elif 'Attribute' in property_type:
            if multiplicity not in ['0..0', '0']:
                for field in ['property_term', 'representation_term']:
                    if not row.get(field):
                        return status, f"Field '{field}' cannot be empty for type {property_type}."
        elif property_type in ['Reference Association', 'Aggregation', 'Composition', 'Specialization']:
            for field in ['associated_class']:
                if not row.get(field):
                    return status, f"Field '{field}' cannot be empty for type {property_type}'."
        else:
            return status, f"Property type {property_type} is WRONG."
        if None in row:
            del row[None]
        status = True
        return status, "Row is valid."

    # Function to sort rows between 'Class' entries
    def sort_records(self, data):
        property_type_order = ['Class', 'Attribute', 'Reference Association', 'Aggregation', 'Composition']
        # Pre-sorting by 'module' and 'table'
        data_sorted_pre = sorted(data, key=lambda x: (x['module'])) #, int(x['table'])))
        # Extract base class terms and add sorting order for 'property_type' again
        for row in data_sorted_pre:
            class_term = row.get("class_term", "")
            row["base_class_term"] = (
                class_term.split(".")[0] if "." in class_term else class_term
            )
            row["property_type_order"] = (
                property_type_order.index(row["property_type"])
                if row["property_type"] in property_type_order
                else float("inf")
            )
        # Perform the second sorting by 'base_class_term', 'property_type_order', and 'sequence'
        for item in data_sorted_pre:
            try:
                seq_int = int(item['sequence'])
            except ValueError:
                print(f"Invalid sequence value: {item['sequence']} in item with id {item['id']}")

        data_sorted_final = sorted(data_sorted_pre, key=lambda x: (x['base_class_term'], x['property_type_order'], int(x['sequence'])))
        # Remove helper fields used for sorting
        for row in data_sorted_final:
            row.pop('base_class_term', None)
            row.pop('property_type_order', None)
        return data_sorted_final

    def specialization(self):
        self.object_class_dict = {}
        with open(self.fsm_file, encoding=self.encoding, newline='') as f:
            reader = csv.DictReader(f, fieldnames=self.header)
            h = next(reader)
            self.current_class = ''
            seq = 0
            # First pass: Register Abstract Classes and Classes
            for row_number, row in enumerate(reader, start=1):
                if not row['sequence'] and not row['level']:
                    continue
                if '' == row['module']:
                    print(f"** ERROR no module defined. {row_number}: {row}")
                    continue
                record = {}
                for key in self.header:
                    if key in row:
                        record[key] = row[key]
                    else:
                        record[key] = ''
                _, result = self.check_csv_row(row)
                if result != "Row is valid.":
                    print(f"** ERROR Row is invalid. {row_number}: {result} {row}")
                    break
                seq, record = self.populate_record(record, seq)
                property_type = record['property_type'].strip()
                class_term = record['class_term'].strip()
                if property_type in ['Abstract Class', 'Class']:
                    if class_term not in self.object_class_dict:
                        self.object_class_dict[class_term] = record
                        self.object_class_dict[class_term]['properties'] = {}
                        
            # Reset reader to process properties
            f.seek(0)
            next(reader) # Skip header row
            # Second pass: Register Properties
            for row_number, row in enumerate(reader, start=1):
                if not row['sequence'] and not row['level']:
                    continue
                if '' == row['module']:
                    print(f"** ERROR Row {row_number}: {row}")
                    continue
                record = {}
                for key in self.header:
                    if key in row:
                        record[key] = row[key]
                    else:
                        record[key] = ''
                _, result = self.check_csv_row(row)
                if result != "Row is valid.":
                    print(f"** ERROR Row {row_number}: {result} {row}")
                    break
                seq, record = self.populate_record(record, seq)
                property_type = record['property_type'].strip()
                class_term = record['class_term'].strip()
                property_type, property_term = self.getproperty_term(record)
                if property_type in ['Abstract Class', 'Class']:
                    self.current_class = class_term
                    current_class_id = record['id'].strip()
                elif 'Specialization'==property_type:
                    superclass_term = record['associated_class']
                    if superclass_term not in self.object_class_dict:
                        print(f"ERROR: {superclass_term} is not defined.")
                        continue
                    super_class = self.object_class_dict[superclass_term]
                    record['id'] = f"{current_class_id}_{record['id'][1 + record['id'].rindex('_'):]}"
                    _class_term = f"{class_term}.{superclass_term}"
                    record['class_term'] = _class_term
                    _properties = copy.deepcopy(super_class['properties'])
                    for _property_term, _property in _properties.items():
                        _propertyID = _property['id']
                        _property['id'] = f"{current_class_id}_{_propertyID}"
                        _property['module'] = self.current_class
                        _property['class_term'] = _class_term
                        if 'Attribute'==_property['property_type']:
                            element = _property['element']
                            new_name = self.merge_class_term_with_element(class_term, element)
                            _property['element'] = new_name
                        self.object_class_dict[class_term]['properties'][_property_term] = _property
                elif property_type not in ['Abstract Class', 'Class']:
                    if class_term not in self.object_class_dict:
                        print(f"** ERROR NOT REGISTERED {class_term} in object_class_dict\n{record}")
                    else:
                        multiplicity = record['multiplicity']
                        if multiplicity in ['0..0', '0']:
                            if property_term in self.object_class_dict[class_term]['properties']:
                                del self.object_class_dict[class_term]['properties'][property_term]
                        else:
                            self.object_class_dict[class_term]['properties'][property_term] = record

        self.BSM_list = []
        selected_classes = self.object_class_dict.keys()
        sorted_classes = sorted(selected_classes, key = lambda x: self.object_class_dict[x]['table'] if self.object_class_dict[x]['table'] else 0)
        for class_term in sorted_classes:
            self.parse_class(class_term)

        records = [{k: v for k, v in d.items() if k in self.header2} for d in self.BSM_list]

        is_abstract_class = False
        out_records = []
        for record in records:
            property_type = record['property_type'].strip()
            if 1 == record['level']:
                if 'Abstract Class' == property_type:
                    is_abstract_class = True
                elif 'Class' == property_type:
                    is_abstract_class = False
            if not is_abstract_class:
                out_records.append(record)

        # Apply the sorting function
        sorted_out_records = self.sort_records(out_records)

        BSM_file = file_path(self.bsm_file)
        with open(BSM_file, 'w', encoding = self.encoding, newline='') as f:
            writer = csv.DictWriter(f, fieldnames = self.header2)
            writer.writeheader()
            writer.writerows(sorted_out_records)

        print(f'-- END {BSM_file}')

        selected_class = []
        if self.fsm_file_extension:
            FSM_file_extension = file_path(self.fsm_file_extension)
            with open(FSM_file_extension, encoding = self.encoding, newline='') as f:
                reader = csv.DictReader(f, fieldnames = self.header)
                next(reader)
                self.current_class = ''
                self.current_class = ''
                current_class_id = ''
                seq = 0
                for row in reader:
                    if '' == row['module']:
                        continue
                    record = {}
                    for key in self.header:
                        if key in row:
                            record[key] = row[key]
                        else:
                            record[key] = ''

                    _, result = self.check_csv_row(row)
                    if result != "Row is valid.":
                        print(f"** ERROR Row {row_number}: {result} {row}")
                        break

                    seq, record = self.populate_record(row, seq)

                    # self.debug_print(f"{record['module']} {record['property_type']} {record['class_term']} {record['property_term']}  {record['associated_class']}")
                    module = record['module'].strip()
                    id = record['id'].strip()
                    property_type = record['property_type'].strip()
                    class_term = record['class_term'].strip()
                    if property_type in ['Abstract Class', 'Class']:
                        if not class_term in self.object_class_dict:
                            selected_class.append(class_term)
                            self.object_class_dict[class_term] = record
                            self.object_class_dict[class_term]['properties'] = {}
                            self.current_class = module
                            self.current_class = class_term
                            current_class_id = record['id'].strip()
                    elif 'Specialization' == property_type:
                        superclass_term = record['associated_class']
                        if superclass_term not in self.object_class_dict:
                            print(f"ERROR: {superclass_term} is not defined.")
                            continue
                        super_class = self.object_class_dict[superclass_term]
                        record['id'] = f"{current_class_id}_{record['id'][1 + record['id'].rindex('_'):]}"
                        _class_term = class_term
                        record['class_term'] = _class_term
                        _properties = copy.deepcopy(super_class['properties'])
                        for _property_term, _property in _properties.items():
                            _propertyID = _property['id']
                            _property['id'] = f"{current_class_id}_{_propertyID}"
                            _property['module'] = self.current_class
                            _property['class_term'] = _class_term
                            self.object_class_dict[class_term]['properties'][_property_term] = _property
                    else:
                        _class_term = class_term
                        record['class_term'] = _class_term
                        property_type, property_term = self.getproperty_term(record)
                        multiplicity = record['multiplicity']
                        if multiplicity in ['0..0', '0']:
                            if property_term in self.object_class_dict[class_term]['properties'].keys():
                                del self.object_class_dict[class_term]['properties'][property_term]
                            else:
                                self.object_class_dict[class_term]['properties'][property_term] = record
                        else:
                            self.object_class_dict[class_term]['properties'][property_term] = record

            self.BSM_list = []
            selected_classes = self.object_class_dict.keys()
            sorted_classes = sorted(selected_classes, key = lambda x: self.object_class_dict[x]['table'] if self.object_class_dict[x]['table'] else 0)
            for class_term in sorted_classes:
                self.parse_class(class_term)

            records = [{k: v for k, v in d.items() if k != 'properties'} for d in self.BSM_list] # drop 'properties' from dict

            is_abstract_class = False
            out_records = []
            for record in records:
                property_type = record['property_type'].strip()
                if 1 == record['level']:
                    if 'Abstract Class' == property_type:
                        is_abstract_class = True
                    elif 'Class' == property_type:
                        is_abstract_class = False
                if not is_abstract_class:
                    out_records.append(record)

            # Apply the sorting function
            sorted_out_records = self.sort_records(out_records)

            BSM_file_extension = file_path(self.bsm_file_extension)
            with open(BSM_file_extension, 'w', encoding = self.encoding, newline='') as f:
                writer = csv.DictWriter(f, fieldnames = self.header2)
                writer.writeheader()
                writer.writerows(out_records)

            print(f'** END {BSM_file_extension}')

# Main function to execute the script
def main():
    # Create the parser
    parser = argparse.ArgumentParser(
        prog='specialization.py',
        usage='%(prog)s FSM_file BSM_file -s FSM_file_extension -l BSM_file_extension -e encoding [options] ',
        description='Converts Foundational Semantic Model (FSM) to Business Semantic Model (BSM) with specialization.'
    )
    parser.add_argument('FSM_file', metavar='FSM_file', type = str, help='Foundational Foundational Semantic Model (FSM) file path')
    parser.add_argument('BSM_file', metavar='BSM_file', type = str, help='Business Semantic Model (BSM) file path')
    parser.add_argument('-s', '--FSM_file_extension', required = False, help='Foundational Foundational Semantic Model (FSM) extension file path')
    parser.add_argument('-l', '--BSM_file_extension', required = False, help='Business Semantic Model (BSM) extension file path')
    parser.add_argument('-e', '--encoding', required = False, default='utf-8-sig', help='File encoding, default is utf-8-sig')
    parser.add_argument('-t', '--trace', required = False, action='store_true')
    parser.add_argument('-d', '--debug', required = False, action='store_true')

    args = parser.parse_args()

    processor = Specialization(
        fsm_file = args.FSM_file.strip(),
        bsm_file = args.BSM_file.strip(),
        fsm_file_extension = args.FSM_file_extension.strip() if args.FSM_file_extension else None,
        bsm_file_extension = args.BSM_file_extension.strip() if args.BSM_file_extension else None,
        encoding = args.encoding.strip() if args.encoding else None,
        trace = args.trace,
        debug = args.debug
    )
   
    processor.specialization()


if __name__ == '__main__':
    main()
