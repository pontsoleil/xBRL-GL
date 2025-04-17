#!/usr/bin/env python3
# coding: utf-8
"""
awi21926graphwalk.py
Generates ADC Logical Hierarchical (LHM)  Model from Business Semantic Model (BSM) CSV with Graph Walk

Designed by SAMBUICHI, Nobuyuki (Sambuichi Professional Engineers Office)
Written by SAMBUICHI, Nobuyuki (Sambuichi Professional Engineers Office)

Creation Date: 2025-01-17
Last Modified: 2025-04-16

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
"""

"""
ABOUT THIS SCRIPT
This second Python script complements the first by further processing the Business Semantic Model (BSM),
specifically focusing on hierarchical relationships and generating a Logical Hierarchical Model (LHM) CSV 
from a BSM CSV. Here’s a detailed procedure description:

1. Initial Setup:
   - Imports necessary modules and sets up debugging flags and file path separators.
   - Defines directories and filenames for logical and hierarchical model CSV files.

2. Utility Functions and utility class:
   - parse_class(class_term, SP_ID=''): Processes each class term and its properties, focusing on handling hierarchical relationships and associations.
   - file_path(pathname): Constructs full file paths from given pathnames.
   - update_class_term(row): Processes each row to construct an object class term.
   - model2record(LHM_model): Transforms the hierarchical model into a format suitable for CSV output.
   - set_path(data, aggregates): Set path for hierarchical model
   - get_semantic_path(record):Get semantic path
   - update_class_term(row): Update class term
   - update_name(hierarchy_records): Update the name field in the hierarchical records

   - IndexManager class to manage class and property indexing.

3. Building Hierarchical Model:
   - Reads the BSM CSV file and populate object_class_dict.
   - Iterates through each class in object_class_dict uses parse_class() to to build a hierarchical model.

4. Hierarchy Generation Logic:
   - Uses a Last-In-First-Out (LIFO) list to track the hierarchy of classes and their associations.
   - Applies rules for selecting classes and associations based on graph walk principles, such as handling specializations, mandatory associations, and navigating through class hierarchies.
   - Constructs the hierarchical model by recursively processing class terms and their associations.

5. Decoupled Navigation Mode (DNM):
   - Graph walk supports Decoupled Navigation Mode, allowing both header and line classes to serve as root classes and be traversed independently in the graph walk.

6. Output Hierarchical Model to CSV:
   - Converts the hierarchical model into records suitable for LHM CSV output using model2record().
   - Writes these records to a CSV file in the specified directory.

7. Extension Handling (If BSM_file_extension is provided):
   - Reads an extended BSM CSV file.
   - Processes each record and updates object_class_dict and exception_class.
   - Repeats the hierarchical model generation process for the extended model.
   - Outputs the extended hierarchical model to a CSV file.

8. Debugging and Tracing:
   - Uses DEBUG and TRACE flags to control the output of diagnostic messages, aiding in understanding the process flow and troubleshooting.

   Example Usage:
python awi21926graphWalk.py AWI21926_BSM.csv AWI21926_DNM_LHM.csv -l BIS_BSM.csv -m BIS_DNM_LHM.csv -o

Where:
- The first parameter is the input BSM file.
- The second parameter is the output LHM file.
- `-l` option specifies the input extension BSM file.
- `-m` option specifies the output extension LHM file.

This script specializes in constructing a hierarchical representation of the BSM, adhering to standards. It efficiently manages the complexities of class hierarchies, associations, and specializations to produce a structured Hierarchical Message Definition (HMD).
"""

import os
import sys
import argparse
import csv
import copy
import re
from collections import OrderedDict, Counter

from common.utils import (
    LC3,
    file_path,
    is_file_in_use,
    split_camel_case,
    abbreviate_term,
    normalize_text,
)

class Graphwalk:
    def __init__ (
            self,
            bsm_file,
            lhm_file,
            bsm_file_extension,
            lhm_file_extension,
            root_terms,
            option,
            encoding,
            trace,
            debug
        ):

        self.bsm_file = bsm_file.replace('/', os.sep)
        self.bsm_file = file_path(self.bsm_file)
        if not self.bsm_file or not os.path.isfile(self.bsm_file):
            print(f'[INFO] No input Semantic file {self.bsm_file}.')
            sys.exit()

        self.lhm_file = lhm_file.replace('/', os.sep)
        self.lhm_file = file_path(self.lhm_file)
        if 'IN_USE' == is_file_in_use(self.lhm_file):
            print(f'[INFO] Semantic file {self.lhm_file} is in use.')
            sys.exit()

        self.bsm_file_extension = None
        if bsm_file_extension:
            self.bsm_file_extension = bsm_file_extension.replace('/', os.sep)
            self.bsm_file_extension = file_path(self.bsm_file_extension)
            if not self.bsm_file_extension or not os.path.isfile(self.bsm_file_extension):
                print('[INFO] No input Business semantic model extension file.')

        self.lhm_file_extension = None
        if lhm_file_extension:
            self.lhm_file_extension = lhm_file_extension.replace('/', os.sep)
            self.lhm_file_extension = file_path(self.lhm_file_extension)
            if self.lhm_file_extension and (not self.bsm_file_extension or not os.path.isfile(self.bsm_file_extension)):
                print('[INFO] No input Business semantic model extension file.')
                sys.exit()
            elif self.bsm_file_extension:
                print('[INFO] Input Business semantic model extension file specified.')
            if 'IN_USE' == is_file_in_use(self.lhm_file_extension):
                sys.exit()

        self.encoding = encoding.strip() if encoding else 'utf-8-sig'

        # Set debug and trace flags, and file path separator
        self.root_terms = root_terms
        self.DNM = True if option else False
        self.TRACE = trace
        self.DEBUG = debug

        # Initialize dictionaries and lists
        self.object_class_dict = {}
        self.LIFO_list = []
        self.LHM_model = []
        self.is_singular_association = False
        self.exception_class = set()
        self.selected_class = None
        self.sequence = 1
        self.elementnames = set()

        # self.abbreviation_generator = AbbreviationGenerator()
        self.index_manager = IndexManager()

    def debug_print(self, text):
        if self.DEBUG:
            print(text)

    def trace_print(self, text):
        if self.TRACE or self.DEBUG:
            print(text)

    # Utility function to update class term
    def update_class_term(self, row):
        id = row['id']
        if not id:
            return None
        _type = row['property_type']
        class_term = row['class_term']
        if '.' in class_term:
            class_term = class_term[:class_term.index('.')]
        # associated_class_term = row['associated_class']
        if _type in ['Class','Specialized Class']:
            if not class_term in self.object_class_dict:
                self.object_class_dict[class_term] = row
                self.object_class_dict[class_term]['properties'] = {}
            if 'level' in row and int(row['level']) > 1:
                associated_class = self.object_class_dict[class_term]
                if 'Base' != associated_class['module']:
                    self.exception_class.add(class_term)
        else:
            if not class_term in self.object_class_dict:
                self.object_class_dict[class_term] = row
                self.object_class_dict[class_term]['properties'] = {}
            self.object_class_dict[class_term]['properties'][id] = row
            self.object_class_dict[class_term]['properties'][id]['class_term'] = class_term
        return class_term

    def extract_uppercase_and_digits(self, string):
        # Regular expression to match consecutive uppercase letters followed by consecutive digits
        match = re.match(r'([A-Z]+)(\d+)', string)
        if match:
            uppercase_part = match.group(1)
            digit_part = match.group(2)
            return uppercase_part + digit_part
        else:
            return None

    # Function to set path for hierarchical model
    def set_path(self, data, aggregates):
        id = data['id']
        level = data['level']
        _type = data['type']
        multiplicity = data['multiplicity']
        if _type in ['C', 'R', 'DNM']:
            if level > 1 and '1' == multiplicity[-1]:
                self.is_singular_association = True
            else:
                self.is_singular_association = False
        id_ = self.index_manager.generate_indexed_code(id)
        if 1 == level:
            aggregates[level - 1] = {'id':id_, 'multiplicity': '0..*'}
        else:
            aggregates[level - 1] = {'id':id_, 'multiplicity': multiplicity}
        for i in range(level, 11 - level):
            aggregates[i] = None
        path = ''
        for i in range(len(aggregates)):
            aggregate = aggregates[i]
            if aggregate and '*' == aggregate['multiplicity'][-1]:
                _id = aggregates[i]['id']
                path += f"/{_id}"
        if not path or id_ not in path:
            path += f"/{id_}"
        return path

    # Function to get semantic path
    def get_semantic_path(self, record):
        _type = record['property_type']
        class_term = record['class_term']
        class_list = class_term.split('-')
        class_list = [f"({x[:x.index('_')]}) {x[1 + x.index('_'):]}" if "_" in x else x for x in class_list]
        # dimension_list = [
        #     next((x['class_term'] for x in self.LHM_model if x['class_term'] == class_term and "*"==x['multiplicity'][-1]), None)
        #     for class_term in class_list
        # ]
        # filtered_list = [x for x in dimension_list if x is not None]
        _class_term = ".".join(class_list)
        if "Class"==_type or "Reference Association"==_type:
            if class_list[-1] not in _class_term:
                semantic_path = f"$.{_class_term}.{class_list[-1]}"
            else:
                semantic_path = f"$.{_class_term}"
        elif "Attribute"==_type:
            property_term = record['property_term']
            semantic_path = f"$.{_class_term}.{property_term}"
        elif _type in ["Composition", "Aggregation"]:
            associated_class = record["associated_lass"]
            semantic_path = f"$.{_class_term}.{associated_class}"
        return semantic_path

    # Function to get abbreviate path
    def get_abbreviate_path(self, record):
        semantic_path = record['semantic_path']
        semantic_path_list = semantic_path[2:].split('.')
        # Generate abbreviations for the transformed list
        abbreviated_list = [
            re.sub(r"[\s]", "", abbreviate_term(term)) for term in semantic_path_list
        ]
        _abbreviated_term = ".".join(abbreviated_list)
        return _abbreviated_term

    # Function to transform hierarchical model to records suitable for CSV output
    def model2record(self):
        hierarchy_records = []
        aggregates = [''] * 10
        current_module = ''
        used_localnames = set()

        i = 0
        for data in self.LHM_model:
            level = int(data['level'])
            record = copy.deepcopy(data)
            current_module = record['module']
            _type = data['type']
            identifier = data['identifier']
            class_term = data["class_term"]

            # Generate semantic path and assign it to the record
            semantic_path = self.get_semantic_path(record)
            record['semantic_path'] = semantic_path

             # Split the semantic path into components
            semantic_path_splitted = semantic_path[2:].split(".")[1:]

            # Debug: Print short paths that may cause index errors
            if len(semantic_path_splitted) < 2:
                # self.debug_print(f"Short semantic path may cause index errors detected: {semantic_path} → {semantic_path_splitted}")
                semantic_path_splitted = semantic_path[2:].split(".")

            # Determine which part of the semantic path to use for generating the local name
            if semantic_path != "$.Accounting Entries":
                if (
                    _type == "C"
                    or (len(semantic_path_splitted) >= 2 and "Entry Header" in semantic_path_splitted[-2])
                    or (len(semantic_path_splitted) >= 2 and "Entry Detail" == semantic_path_splitted[-2])
                ):
                    start = -1
                elif identifier == "REF":
                    start = -3
                else:
                    start = -2 if len(semantic_path_splitted) >= 2 else -1

                _semantic_path_splitted = semantic_path_splitted[start:]
            else:
                _semantic_path_splitted = ["Accounting Entries"]

            # Normalize and convert the selected path segments into a local name using LC3
            local_name = LC3((" ").join([normalize_text(x) for x in _semantic_path_splitted]))

            # Skip if local_name is empty and log debug information
            if not local_name:
                local_name = semantic_path[2:]
                # self.debug_print(f"Empty local_name for semantic path: {semantic_path} local_name: {local_name}")
                continue

            if local_name not in used_localnames:
                used_localnames.add(local_name)
            elif _type == "C":
                # Avoid duplicate local names for classes
                if local_name != "accountingEntries":
                    if local_name not in used_localnames:
                        used_localnames.add(local_name)
                    else:
                        # Try suffixes from class_term to resolve conflict
                        for n in (1, 2, 3, 4):
                            _suffix = class_term.split("-")[-n:]
                            local_name = LC3(" ".join(normalize_text(x) for x in _suffix))
                            if local_name not in used_localnames:
                                used_localnames.add(local_name)
                                break
                        else:
                            continue  # All suffix attempts failed; skip this record
            else:
                # For non-class elements, extend the semantic path further up to resolve duplicates
                # Try suffixes from class_term to resolve conflict
                for n in (1, 2, 3):
                    _suffix = semantic_path_splitted[start-n:]
                    local_name = LC3(" ".join(normalize_text(x) for x in _suffix))
                    if local_name not in used_localnames:
                        used_localnames.add(local_name)
                        break
                else:
                    continue  # All suffix attempts failed; skip this record

            # Set the final element name
            record["element"] = f"{current_module}:{local_name}"

            i += 1
            
            if "REF"==identifier:
                index = semantic_path.rfind(".")
                if index != -1:
                    semantic_path = semantic_path[:index] + " " + semantic_path[index+1:]
                    record["semantic_path"] = semantic_path
                    class_term = class_term.split("-")[-2]
            elif 'R' == _type or 'C'==_type:
                class_term = semantic_path.split('.')[-1]
            elif 'A' == _type:
                class_term = semantic_path.split('.')[-2]
            else:
                self.debug_print(f"Wrong data for {semantic_path}")
            record['class_term'] = class_term
            if "REF"==identifier:
                record['property_term'] = " ".join(_semantic_path_splitted[1:])
            abbreviation_path = self.get_abbreviate_path(record)
            record['abbreviation_path'] = abbreviation_path
            path = self.set_path(data, aggregates)
            record['path'] = path
            id = path.split('/')[-1]
            record['id'] = id
            property_term = record['property_term']
            if 'Active Indicator' == property_term and not self.DNM:
                continue
            if class_term.endswith('Business Segment'):
                if level > 4: 
                    continue
                elif level > 3 and record['type'] in ['C', 'R']:
                    continue
            level = str(level)
            record['level'] = level
            if 'properties' in record:
                del record['properties']
            record['sequence'] = self.sequence
            self.sequence += 1
            if not record['element']: # and "R"!=_type:
                continue
            hierarchy_records.append(record)
        
        if not hierarchy_records[0]['xpath']:
            records = []
            for record in hierarchy_records:
                semantic_path = record['semantic_path']
                path_list = semantic_path[2:].split('.')
                if len(path_list) > 1:
                    xpath = self.build_xpath_from_semantic_path(semantic_path, hierarchy_records)
                    if not xpath:
                        self.debug_print(f"Empty xpath for {semantic_path}")
                        continue
                    element = xpath[1+xpath.rindex("/"):]
                    record["element"] = element
                else:
                    xpath = f"/{path_list[0]}"
                record['xpath'] = xpath
                records.append(record)
        else:
            records = hierarchy_records

        return records

    def build_xpath_from_semantic_path(self, target_path, hierarchy_records):
        # Abbreviation mapping for known suffixes
        # Predefined abbreviation mapping (extend as needed)
        abbreviations = {
            "Information": "Info",
            "Description": "Desc",
            "Detail": "Dtl",
            "Structure": "Struct",
            "Number": "Num"
        }
        suffixes = {
            "Identifier": "ID",
            "Identification": "ID"
        }
        # Function to shorten element values by replacing known suffixes
        def shorten_element(element_value):
            if ":" in element_value:
                prefix, term = element_value.split(":", 1)
                for long, short in abbreviations.items():
                    term = term.replace(long, short)
                for suffix in suffixes:
                    if term.endswith(suffix):
                        term = term.replace(suffix, suffixes[suffix])
                        break
                return f"{prefix}:{term}"
            return element_value
        # Extract the top-level path from the semantic_path (e.g., '$.Accounting Entries')
        leading_path = '.'.join(target_path.split('.')[:2])
        # Check if the target_path starts with the expected leading path
        if not target_path.startswith(leading_path):
            return None
        # Extract the remaining parts of the path after the leading path
        path_suffix = target_path.replace(leading_path + '.', '').split('.')
        current_path = leading_path
        xpath_parts = []
        # Find the root element corresponding to the top-level path
        root_record = next((r for r in hierarchy_records if r['semantic_path'] == current_path), None)
        if not root_record:
            return None
        xpath_parts.append(root_record['element'])
        # Traverse through each level of the semantic path to collect element names
        for part in path_suffix:
            current_path += f'.{part}'
            record = next((r for r in hierarchy_records if r['semantic_path'] == current_path), None)
            if not record:
                return None        
            xpath_part = shorten_element(record['element'])
            xpath_parts.append(xpath_part)
        return '/' + '/'.join(xpath_parts)

    # Function to update the name field in the hierarchical records
    def update_name(self, hierarchy_records):
        records = []
        parent_class = [''] * 7
        for record in hierarchy_records:
            property_type = record['property_type']
            level = int(record['level'])
            class_term = record['class_term']
            representation_term = record['representation_term']
            property_term = record['property_term']
            name = ''
            datatype = ''
            if 'Class' == property_type:
                name = class_term.split('-')[-1]
                parent_class[level] = name
                for i in range(level, 7):
                    parent_class[i] = ''
            elif 'Attribute' == property_type:
                name = property_term
                datatype = representation_term
            elif 'Reference Association' == property_type:
                record['identifier'] = ''
                name = class_term
                datatype = representation_term
            else:
                continue
            if '_' in name:
                name = f"({name[:name.index('_')]}) {name[1 + name.index('_'):]}"
            record['name'] = name
            record['datatype'] = datatype
            records.append(record)
        return records

    # Function to parse class terms and handle specializations
    def parse_class(self, class_term, REFERENCE_OF = False):
        global current_multiplicity
        """
        Step 1: Copy a class to the Hierarchical Message Definition and place it on the top of
        the LIFO list.
        """
        _class_term = class_term
        if '_' in _class_term: # romove originating class name for this associated class
            _class_term = _class_term[1+_class_term.index('_'):]
        if _class_term not in self.object_class_dict:
            print(f"[ERROR] '{_class_term}' not in object_class_dict")
            return
        object_class = copy.deepcopy(self.object_class_dict[_class_term])
        if REFERENCE_OF:
            object_class['property_type'] = 'Reference Association'
        _type = object_class['property_type']
        self.trace_print(f"{_type in ['Subclass','Specialized Class'] and '-' or ' '} {_type}: parse_class('{class_term}') check  '{_class_term}'\t{self.LIFO_list}")
        """
        A. Copy the class to the hierarchical logical data model.
        Copy all properties and associations to the hierarchical logical data model.
        Conventionally, properties not related to the associated object class should be placed
        before them, but this is not a requirement.

        B. Place the selected class on the top of the LIFO list if not Reference Association.
        """
        if REFERENCE_OF:
            level = 1 + len(self.LIFO_list)
        else:
            self.LIFO_list.append(class_term)
            level = len(self.LIFO_list)
        self.debug_print(f'  Update LIFO_list {self.LIFO_list}\n')
        object_class['level'] = level
        if level > 1:
            LIFO_term = '-'.join(self.LIFO_list)
            object_class['class_term'] = LIFO_term
        if REFERENCE_OF:
            """
            iii)	Reference Associations
            •	Copy associated class with adding it to the LIFO (Last In, First Out) list.
            For copying reference association's associated class, the new entry in the LHM should include:
                - Level: n
                - Type: 'R' (Relation)
                - Identifier: Empty
                - Name:
                - If an association role for the reference association is defined, format as "{association role}_{associated class}".
                - If no association role is defined, use "{associated class}".
                - Datatype: Leave empty as datatype is not applicable for reference association's associated class.
            """
            object_class['class_term'] += f"-{class_term}"
            self.debug_print(f"class_term:{class_term} _class_term:{_class_term} object_class['class_term']:{object_class['class_term']}")
            definition = object_class['definition']
            definition = definition.replace('A class', f"The reference association to the {class_term.replace('_', ' ')} class, which is a class")
            object_class['definition'] = definition
            object_class['type'] = 'R'
            properties_list = {}
            for key in self.object_class_dict:
                if key.startswith(_class_term):
                    properties = self.object_class_dict[_class_term].get('properties', [])
                    for key, prop in properties.items():
                        properties_list[key] = prop
            for key, prop in properties_list.items():
                object_class['properties'][key] = prop
            hasPK = any(property.get('identifier', '') == 'PK' for property in properties_list.values())
            if '-' not in object_class['class_term'] and not hasPK:
                print(f"[ERROR] Referenced class {object_class['class_term']} has no PK(primary Key).")
            else:
                pass
        else:
            object_class['type'] = 'C'
        if level > 1 and not object_class['multiplicity'] and current_multiplicity:
            object_class['multiplicity'] = current_multiplicity
        self.LHM_model.append(object_class)
        self.debug_print(f"  {level} {object_class['class_term']}")
        properties = copy.deepcopy(object_class['properties'])
        level += 1
        for id, property_ in properties.items():
            property = property_.copy()
            if not id:
                pass
            # element = self.extend_element_name(property)
            # property['element'] = element
            if property['property_type'] in ['Attribute(PK)','Attribute']:
                """
                a) Step 1: Copy a class from the BSM to the LHM.
                Procedure:
                In this step, all attributes and associations relevant to the class are incorporated, with 
                the 'level' of attribute entries incremented by 1. Let the resulting value of 'level' be n
                after the increment.
                Attributes and reference associations are prioritized over composition/aggregation associations
                to maintain clarity and order. The copying logic is detailed as follows:
                """
                if 'Active' in  property['property_term']:
                    # Skip 'xxActive' attribute, which indicates that the master record is active and not usable for LHM.
                    continue
                property['level'] = level
                property['type'] = 'A'
                propertyclass_term = property['class_term']
                LIFO_term = '-'.join(self.LIFO_list)
                if propertyclass_term != LIFO_term:
                    property['class_term'] = LIFO_term
                if REFERENCE_OF:
                    LIFO_term += f"-{class_term}"
                    """
                    iii) Reference Associations
                    •	Copy the unique identifier of the associated class.
                    Additionally, check for reference associations to identify the unique identifier of the associated class. If found, copy this identifier to the LHM as:
                        - Level: n + 1
                        - Type: 'A' (Attribute)
                        - Identifier: 'REF' (Reference Identifier)
                        - Name: The property term of the found unique identifier.
                        - Datatype: The representation term of the found unique identifier.
                    Note: This entry in the LHM is a reference identifier, serving as a foreign key to the reference association class.
                    """
                    if 'PK'==property['identifier']:                    
                        property['identifier'] = 'REF'
                        property['class_term'] = LIFO_term
                        definition = property['definition']
                        definition = definition.replace('unique identifier', 'reference identifier')
                        property['definition'] = definition
                        self.LHM_model.append(property)
                        self.debug_print(f"  {level} {property['class_term']} {property['property_type']} {property['identifier']} [{property['multiplicity']}] {property['property_term']}{property['associated_class']}")
                else:                    
                    self.LHM_model.append(property)
                    self.debug_print(f"  {level} {property['class_term']} {property['property_type']} [{property['multiplicity']}] {property['property_term']}{property['associated_class']}")

        if REFERENCE_OF:
            # When dealing with Reference Association, no additional checks are required for Properties, including Associations.
            return
        """
        Step 2: Find the next class.
        The following rules provide guidance on choosing the association,
        which is a property that has the associated object class defined,
        to use for stepping from the current class to the next in a "walk".
        Once an association has been used to step from the current class to a new class,
        do not re-use it unless the current class itself has been reached again by a different
        association.
        All selections of associations must be consistent with the intended semantics of the
        data.
        The following rules should be applied in the order they are listed.
        As soon one of them is reached that is applicable, select the class it specifies and
        return to step 1, above.

        B. Mandatory, Singular.
        Pick any 1..1 association that is navigable to needed information.
        """
        mandate_classes = [
            cls
            for cls in properties.values()
            if cls["property_type"]
            in ["Reference Association", "Aggregation", "Composition"]
            and cls["multiplicity"] in ["1", "1..1"]
        ]
        """
        C. Singular.
        Pick any navigable association that is (0,1) and leads to needed information.
        """
        singular_classes = [
            cls
            for cls in properties.values()
            if cls["property_type"]
            in ["Reference Association", "Aggregation", "Composition"]
            and "0..1" == cls["multiplicity"]
        ]
        """
        E. Other Plural.
        Pick any navigable association that leads to needed information.
        """
        other_classes = [
            cls
            for cls in properties.values()
            if cls["property_type"]
            in ["Reference Association", "Aggregation", "Composition"]
            and cls["multiplicity"] in ["0..*", "1..*"]
        ]
        """
        B. Mandatory, Singular.
        Pick any 1..1 association that is navigable to needed information.
        """
        for _class in mandate_classes:
            property_type = _class['property_type']
            property_term = _class['property_term']
            associated_class = _class['associated_class']
            if property_term:
                selectedclass_term = f"{property_term}_{associated_class}"
            else:
                selectedclass_term = associated_class
            if selectedclass_term and selectedclass_term not in self.LIFO_list:
                current_multiplicity = _class['multiplicity']
                if self.DEBUG:
                    if property_term:
                        self.debug_print(f"  {level} {_class['class_term']}. {property_type}[{current_multiplicity}] {property_term}_ {associated_class}")
                    else:
                        self.debug_print(f"  {level} {_class['class_term']}. {property_type}[{current_multiplicity}] {associated_class}")
                self.parse_class(selectedclass_term, 'Reference Association'==property_type and _class['class_term'] or None)
        """
        C. Singular.
        Pick any navigable association that is (0,1) and leads to needed information.
        """
        for _class in singular_classes:
            property_type = _class['property_type']
            property_term = _class['property_term']
            associated_class = _class['associated_class']
            if property_term:
                selectedclass_term = f"{property_term}_{associated_class}"
            else:
                selectedclass_term = associated_class
            if selectedclass_term and selectedclass_term not in self.LIFO_list:
                current_multiplicity = _class['multiplicity']
                if self.DEBUG:
                    if property_term:
                        self.debug_print(f"  {level} {_class['class_term']}. {property_type}[{current_multiplicity}] {property_term}_ {associated_class}")
                    else:
                        self.debug_print(f"  {level} {_class['class_term']}. {property_type}[{current_multiplicity}] {associated_class}")
                self.parse_class(selectedclass_term, 'Reference Association'==property_type and _class['class_term'] or None)
        """
        E. Other Plural.
        Pick any navigable association that leads to needed information.
        """
        for _class in other_classes:
            property_type = _class['property_type']
            property_term = _class['property_term']
            associated_class = _class['associated_class']
            if self.DNM and associated_class in f"{class_term} Line":
                continue
            if property_term:
                selectedclass_term = f"{property_term}_{associated_class}"
            else:
                selectedclass_term = associated_class
            if selectedclass_term and selectedclass_term not in self.LIFO_list:
                current_multiplicity = _class['multiplicity']
                if self.DEBUG:
                    if property_term:
                        self.debug_print(f"  {level} {_class['class_term']}. {property_type}[{current_multiplicity}] {property_term}_ {associated_class}")
                    else:
                        self.debug_print(f"  {level} {_class['class_term']}. {property_type}[{current_multiplicity}] {associated_class}")
                self.parse_class(selectedclass_term, 'Reference Association'==property_type and _class['class_term'] or None)
        """
        F. None.
        If none of the above rules apply, cross the current class off the LIFO list.
        Take the prior class on the LIFO as the “current” class and immediately repeat steps
        A-E.
        If you have crossed the last class of the LIFO list, you have finished the process of
        selecting the classes and associations for the hierarchical logical data model.
        The sequence of Rules (B) – (E) leads to message types that seem more coherent to people.
        If there is doubt or disagreement about which association to pick based on this rule,
        the committee may ignore rules (B) – (E) completely and pick any association.
        The message will have the same information content.
        """
        self.debug_print(f"-- Done: {self.LIFO_list[-1]}\n")
        self.LIFO_list.pop(-1)
        self.debug_print(f"POP LIFO_list: {class_term} type is '{_type}'\t{self.LIFO_list}")
        if self.DNM and class_term.endswith(" Line"):
            """
            Line Class Handling:
            If a root class name ends with "Line," it is identified as the line class. In DNM, a reference association to the corresponding header class is presumed. The following actions are carried out after the normal graph walk.
            • Copy the header class.
                Name: Remove the trailing "Line" from the class term.
                Level: 2
                Type: 'DNM' (Decoupled Navigation Mode)
                Identifier: Empty
                Datatype: Leave empty as datatype is not applicable for reference association's associated class.
                Definition: Append ' This reference association is generated during the Decoupled Navigation Mode graph walk.'
            """
            header_class_term = class_term.replace(" Line", "")
            if header_class_term in self.object_class_dict:
                header_class = self.object_class_dict[header_class_term].copy()
                header_class['level'] = 2
                header_class['type'] = 'DNM'
                header_class['identifier'] = ''
                header_class['class_term'] = f"{object_class['class_term']}-{header_class_term}"
                header_class['representation_term'] = ''
                definition = header_class['definition']
                definition += ' This reference association is generated during the Decoupled Navigation Mode graph walk.'
                header_class['definition'] = definition
                self.LHM_model.append(header_class)
                """
                • Copy the unique identifier of the header class.
                    - Name: "{The name of the line class}-{The name of the unique identifier of the header class}"
                    - Level: 3
                    - Type: 'A' (Attribute)
                    - Identifier: ‘REF’
                    - Datatype: ‘Identifier’
                    - Definition: Replace 'unique identifier' with 'reference identifier.'
                """
                for id, property_ in header_class['properties'].items():
                    property = property_.copy()
                    if 'PK' == property['identifier']:
                        property['level'] = 1 + level
                        property['type'] = 'A'
                        property['identifier'] = 'REF'
                        property['class_term'] = f"{object_class['class_term']}-{header_class_term}"
                        definition = property['definition']
                        definition = definition.replace('unique identifier', 'reference identifier')
                        property['definition'] = definition
                        self.LHM_model.append(property)
                        self.debug_print(f"  {property['level']} {property['class_term']} {property['property_type']} {property['identifier']} [{property['multiplicity']}] {property['property_term']}{property['associated_class']}")

    def graph_walk(self):
        self.selected_class = set()
        self.exception_class = set()
        # read CSV file
        header =  ['sequence', 'level', 'property_type', 'identifier', 'class_term', 'property_term', 'representation_term', 'associated_class', 'multiplicity', 'definition', 'module', 'table', 'domain_name', 'element', 'label_local', 'definition_local', 'xpath', 'id']
        # write CSV file
        header2 = ['sequence', 'level', 'type', 'identifier', 'name', 'datatype', 'multiplicity', 'domain_name', 'definition', 'module', 'table', 'class_term', 'id', 'path', 'semantic_path', 'abbreviation_path', 'label_local', 'definition_local', 'element', 'xpath']

        with open(self.bsm_file, encoding = self.encoding, newline='') as f:
            reader = csv.DictReader(f, fieldnames = header)
            next(reader)
            business_segment_id = None
            for row in reader:
                record = {}
                for key in header:
                    if key in row:
                        record[key] = row[key]
                    else:
                        record[key] = ''
                class_term = self.update_class_term(record)
                property_type = row['property_type']
                associated_class = row['associated_class']
                self.debug_print(f"{class_term}({record['property_type']}) {record['associated_class'] or record['property_term']}")
                if class_term:
                    if property_type in ['Composition', 'Aggregation']:
                        if 'Base' != row['module']:
                            self.exception_class.add(associated_class)
                    if 'General' != self.object_class_dict[class_term]['module']:
                        self.selected_class.add(class_term)

        self.LHM_model = []
        self.selected_class = self.object_class_dict.keys()
        sorted_classes = sorted(self.selected_class, key = lambda x: self.object_class_dict[x]['table'] if self.object_class_dict[x]['table'] else 0)

        if self.DNM:
            self.exception_class = [cls for cls in self.exception_class if not (cls.endswith(" Line") and cls.replace(" Line", "") in self.selected_class)]

        root_found = False
        for root_term in self.root_terms:
            if root_term in self.selected_class:
                root_found = True
                self.debug_print(f"- root_term parse_class({root_term})")
                self.parse_class(root_term)      

        if not root_found:
            for class_term in sorted_classes:
                if class_term in self.exception_class:
                    continue
                self.debug_print(f"- parse_class({class_term})")
                self.parse_class(class_term)

        hierarchy_records = self.model2record()

        records = self.update_name(hierarchy_records)
        out_records = [{k: v for k, v in d.items() if k in header2} for d in records]
        # Use Counter to count occurrences of each path id
        indexed_list = [x['path'].split('/')[-1] for x in out_records]
        count = Counter(indexed_list)
        # Find elements that are duplicated (those that appear more than once)
        duplicates = {item: count[item] for item in count if item and count[item] > 1}
        # Print the results
        self.trace_print(f"Checking duplicated id and their counts: {duplicates}")
        with open(self.lhm_file, 'w', encoding = self.encoding, newline='') as f:
            writer = csv.DictWriter(f, fieldnames = header2)
            writer.writeheader()
            writer.writerows(out_records)
        print(f'** END {self.lhm_file}')

        self.selected_class = set()
        self.exception_class = set()
        if self.bsm_file_extension:
            self.bsm_file_extension = file_path(self.bsm_file_extension)
            with open(self.bsm_file_extension, encoding = self.encoding, newline='') as f:
                reader = csv.DictReader(f, fieldnames = header)
                next(reader)
                for row in reader:
                    record = {}
                    for key in header:
                        if key in row:
                            record[key] = row[key]
                        else:
                            record[key] = ''
                    class_term = self.update_class_term(record)
                    self.debug_print(f"{class_term}({record['property_type']}) {record['associated_class'] or record['property_term']}")
                    if class_term:
                        if row['property_type'] in ['Composition', 'Aggregation']:
                            associated_class = self.object_class_dict[class_term]
                            if 'Base' != associated_class['module']:
                                self.exception_class.add(row['associated_class'])
                        if 'General' != self.object_class_dict[class_term]['module']:
                            self.selected_class.add(class_term)

            self.LHM_model = []
            sorted_classes = sorted(self.selected_class, key = lambda x: self.object_class_dict[x]['table'] if self.object_class_dict[x]['table'] else 0)
            if self.DNM:
                self.exception_class = [cls for cls in self.exception_class if not (cls.endswith(" Line") and cls.replace(" Line", "") in self.selected_class)]

            root_found = False
            for root_term in self.root_terms:
                if root_term in self.selected_class:
                    root_found = True
                    self.debug_print(f"- root_term parse_class({root_term})")
                    self.parse_class(root_term)      

            if not root_found:
                for class_term in sorted_classes:
                    if class_term in self.exception_class:
                        continue
                    self.debug_print(f"- parse_class({class_term})")
                    self.parse_class(class_term)

            hierarchy_records = self.model2record()
            records = self.update_name(hierarchy_records)
            out_records = [{k: v for k, v in d.items() if k in header2} for d in records]
            # Use Counter to count occurrences of each path id
            indexed_list = [x['path'].split('/')[-1] for x in out_records]
            count = Counter(indexed_list)

            # Find elements that are duplicated (those that appear more than once)
            duplicates = {item: count[item] for item in count if item and count[item] > 1}
            # Print the results
            self.trace_print(f"Checking duplicated id and their counts:{duplicates}")

            with open(self.lhm_file_extension, 'w', encoding = self.encoding, newline='') as f:
                writer = csv.DictWriter(f, fieldnames = header2)
                writer.writeheader()
                writer.writerows(out_records)
            print(f'** END {self.lhm_file_extension}')


class AbbreviationGenerator:
    def __init__(self):
        """
        Initialize with a predefined abbreviation list if provided.
        :param abbreviation_list: A dictionary of terms and their abbreviations.
        """
        self.common_abbreviations = {
            "abbreviation": "Abrv",
            "academic": "Acad",
            "account": "Acnt",
            "accumulated": "Accum",
            "acquisition": "Acq",
            "activities": "Acts",
            "activity": "Act",
            "addition": "Add",
            "address": "Adr",
            "adjusted": "Adjd",
            "adjustment": "Adj",
            "after": "Aft",
            "allocation": "Alloc",
            "amount": "Amt",
            "application": "Apl",
            "approval": "Aprv",
            "approved": "Aprv",
            "balance": "Bal",
            "before": "Bef",
            "beginning": "Beg",
            "billing": "Bill",
            "branch": "Bra",
            "business": "Bus",
            "cancellation": "Cncl",
            "characteristic": "Char",
            "contact": "Cnt",
            "content": "Cont",
            "contract": "Contr",
            "corresponding": "Corr",
            "created": "Crea",
            "credit": "Cr",
            "currency": "Cur",
            "customer": "Cust",
            "date": "Dt",
            "debit": "Db",
            "default": "Dft",
            "department": "Dep",
            "depreciable": "Dprcbl",
            "depreciation": "Depre",
            "description": "Dscr",
            "details": "Dtls",
            "developer": "Dvlpr",
            "discount": "Dscnt",
            "dispatch": "Disp",
            "document": "Doc",
            "employee": "Emp",
            "employment": "Emplmnt",
            "encoding": "Enc",
            "ending": "End",
            "exclude": "Excl",
            "external": "Ext",
            "fiscal": "Fisc",
            "functional": "Func",
            "general": "Genr",
            "generated": "Gen",
            "grouping": "Grp",
            "hierarchy": "Hrchy",
            "impairment": "Impr",
            "include": "Incl",
            "indicator": "Ind",
            "inventory": "Inv",
            "invoice": "Invoi",
            "journal": "Jrn",
            "language": "Lang",
            "local": "Loc",
            "location": "Lct",
            "material": "Mat",
            "measurement": "Mea",
            "modified": "Mdf",
            "module": "Mod",
            "number": "Nr",
            "order": "Ord",
            "organization": "Org",
            "parent": "Par",
            "payable": "Pbl",
            "payment": "Pay",
            "percentage": "Perc",
            "period": "Per",
            "physical": "Phys",
            "primary": "Prim",
            "process": "Proc",
            "project": "Proj",
            "proportion": "Prop",
            "provision": "Prov",
            "purchase": "Pur",
            "purchasing": "Prchsng",
            "quantity": "Qt",
            "realized": "Rlzd",
            "receipt": "Rcpt",
            "receivable": "Rcvbl",
            "received": "Rcvd",
            "records": "Rec",
            "reference": "Ref",
            "regulator": "Rgltr",
            "remaining": "Rmng",
            "removal": "Rmv",
            "replacement": "Rplc",
            "report": "Rprt",
            "reporting": "Rprt",
            "requisition": "Rqstn",
            "residual": "Resi",
            "responsibility": "Resp",
            "reversal": "Rev",
            "sales": "Sal",
            "segment": "Sg",
            "sequence": "Sq",
            "service": "Srvc",
            "settlement": "Setl",
            "shipment": "Shp",
            "shipping": "Shpng",
            "software": "Sftw",
            "standard": "Std",
            "status": "Stat",
            "stocking": "Stck",
            "supplier": "Supl",
            "tax": "Tx",
            "total": "Tot",
            "transaction": "Tr",
            "version": "Vers",
            "year": "Yr",
        }

    def register_abbreviation(self, term, abbreviation, max_length = 5):
        """
        Register a new abbreviation to self.common_abbreviations.
        :param term: The term to be abbreviated.
        :param abbreviation: The abbreviation to register.
        :param max_length: Maximum allowed abbreviation length.
        """
        term_lower = term.lower()
        if len(abbreviation) > max_length:
            raise ValueError("Abbreviation length must not exceed 5 characters.")
        if abbreviation in self.common_abbreviations.values():
            raise ValueError("Abbreviation already exists.")
        self.common_abbreviations[term_lower] = abbreviation

    def _make_unique_abbreviation(self, abbreviation, term, max_length=5):
        """
        Modify the abbreviation to make it unique by appending an unused consonant from the term.
        If no unique abbreviation can be generated, return the original term.
        :param abbreviation: The current abbreviation.
        :param term: The original term to extract available consonants.
        :param max_length: Maximum allowed abbreviation length.
        :return: A unique abbreviation or the original term.
        """
        all_consonants = 'bcdfghjklmnpqrstvwxyz'

        # Extract consonants from the original term in order of appearance
        term_consonants = [ch.lower() for ch in term if ch.lower() in all_consonants]

        # Track used consonants from the abbreviation
        used_consonants = [ch for ch in abbreviation.lower() if ch in term_consonants]

        # Determine remaining consonants in the term (preserving order)
        remaining_consonants = term_consonants[len(used_consonants):]

        # Try appending remaining consonants in order
        for consonant in remaining_consonants:
            new_abbreviation = abbreviation + consonant
            if new_abbreviation not in self.common_abbreviations.values():
                self.register_abbreviation(term, new_abbreviation, 1 + max_length)
                return new_abbreviation
            
        # Return the original term if no unique abbreviation can be generated
        return term

    def process_term(self, term):
        """
        Process a list of terms and validate against initial abbreviations.
        :param term: term to process.
        :return: Dictionary of term with their abbreviations and validation results.
        """
        generated_abbreviation, rules = self.abbreviate(term)
        processed_term = {
            "Term": term,
            "Generated Abbreviation": generated_abbreviation,
            "Applied Rules": rules,
        }
        return processed_term


# IndexManager class to manage class and property indexing
class IndexManager:
    def __init__(self):
        self.class_counter = {}
        self.previous_suffix = {}
        self.base_map = "abcdefghijklmnopqrstuvwxyz"
        self.extended_map = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789" + self.base_map
        self.current_suffix = None
        self.last_base_class = None

    def get_suffix(self, class_name):
        if class_name not in self.class_counter:
            self.class_counter[class_name] = 0
        self.class_counter[class_name] += 1
        current_suffix = self.int_to_custom_alpha(self.class_counter[class_name] - 1)
        if class_name in self.previous_suffix and self.previous_suffix[class_name] == current_suffix:
            self.debug_print(f"Warning: Duplicate suffix {current_suffix} for class {class_name}")
        self.previous_suffix[class_name] = current_suffix
        return current_suffix

    def int_to_custom_alpha(self, index):
        if index < 26:
            return self.base_map[index % 26]
        suffix = self.int_to_custom_alpha(index // 26 - 1) + self.extended_map[index % 62]
        return suffix

    def generate_indexed_code(self, item):
        if "_" not in item:
            # A new Class has been found
            self.current_suffix = self.get_suffix(item)
            modified = f"{item}{self.current_suffix}"
            self.last_base_class = item  # Update: Set new base class name
        else:
            # For property items, use the current Class suffix
            base, extension = item.split('_', 1)
            if base != self.last_base_class:
                # If it differs from the previous class, update the suffix
                self.current_suffix = self.get_suffix(base)
            modified = f"{base}{self.current_suffix}_{extension}"
        return modified


# Main function to execute the script
def main():
    # Create the parser
    parser = argparse.ArgumentParser(
        prog='AWI21926_Specialization.py',
        usage='%(prog)s BSM_file LHM_file -l BSM_file_extension -m LHM_file_extension -e encoding [options] ',
        description='Converts logical model to HMD with graph walk.'
    )
    parser.add_argument('BSM_file', metavar='BSM_file', type = str, help='Business semantic model file path')
    parser.add_argument('LHM_file', metavar='LHM_file', type = str, help='LHM file path')
    parser.add_argument('-l', '--BSM_file_extension', required = False, help='Business semantic model extension file path')
    parser.add_argument('-m', '--LHM_file_extension', required = False, help='LHM extension file path')
    # parser.add_argument('-r', '--root', required = False, help='Root for LHM')
    parser.add_argument('-o', '--option', required = False, action='store_true')
    parser.add_argument('-e', '--encoding', required = False, default='utf-8-sig', help='File encoding, default is utf-8-sig')
    parser.add_argument('-t', '--trace', required = False, action='store_true')
    parser.add_argument('-d', '--debug', required = False, action='store_true')

    # Allow multiple values with action='append' or nargs='+'
    parser.add_argument(
        "-r", "--root", 
        action="append", 
        help="Root class term(s) for LHM to process. Can be specified multiple times."
    )

    args = parser.parse_args()

    # Flatten the list if necessary
    root_terms = []
    if args.root:
        for val in args.root:
            if isinstance(val, str) and "+" in val:
                root_terms.extend(val.split("+"))
            else:
                root_terms.append(val)
    root_terms = [x.strip() for x in root_terms]

    processor = Graphwalk(
        bsm_file = args.BSM_file.strip(),
        lhm_file = args.LHM_file.strip(),
        bsm_file_extension = args.BSM_file_extension.strip() if args.BSM_file_extension else None,
        lhm_file_extension = args.LHM_file_extension.strip() if args.LHM_file_extension else None,
        root_terms = root_terms,
        option = args.option if args.option else False,
        encoding = args.encoding.strip() if args.encoding else None,
        trace = args.trace,
        debug = args.debug
    )

    processor.graph_walk()

if __name__ == '__main__':
    main()
