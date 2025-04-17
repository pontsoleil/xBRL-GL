#!/usr/bin/env python3
# coding: utf-8
"""
xBRLGL_StructuredCSV.py

Converts an XBRL-GL instance document into a hierarchical tidy CSV format,
using a combined structure file that includes both Logical Hierarchical Model (LHM)
and binding definitions.

Designed by SAMBUICHI, Nobuyuki (Sambuichi Professional Engineers Office)
Written by SAMBUICHI, Nobuyuki (Sambuichi Professional Engineers Office)

Creation Date: 2025-04-04
Last Modified: 2025-04-12

MIT License

© 2025 SAMBUICHI Nobuyuki (Sambuichi Professional Engineers Office)

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
from lxml import etree as ET
import os
import sys
import argparse
import csv
import json
import re
# import pandas as pd

from csv2tidy import DataProcessor

class xBRLGL_StructuredCSV:
    def __init__(
            self, 
            input_file,
            version,
            structure_file,
            output_file,
            encoding,
            trace,
            debug
        ):

        self.input_file = self.file_path(input_file.strip())
        if not os.path.isfile(self.input_file):
            print(f"Input XBRL GL instance file {self.input_file} is missing.")
            sys.exit()

        self.version = version.strip()

        self.structure_file = self.file_path(structure_file.strip())
        if not os.path.isfile(self.structure_file):
            print(f"Structure file {self.structure_file} is missing.")
            sys.exit()

        self.output_file = self.file_path(output_file.strip())
        self.output_dir = os.path.dirname(self.output_file)
        if self.output_dir and not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir, exist_ok=True)
            print(f"Created output directory: {self.output_dir}")

        self.encoding = encoding.strip() if encoding else "utf-8-sig"
        self.TRACE = trace
        self.DEBUG = debug
        self.currency = "usd"

        self.dimensions = set()

    def trace_print(self, text):
        if self.TRACE or self.DEBUG:
            print(text)

    def debug_print(self, text):
        if self.DEBUG:
            print(text)

    def file_path(self, pathname):
        if os.sep == pathname[0:1]:
            return pathname
        else:
            _pathname = pathname.replace("/", os.sep)
            dir = os.path.dirname(__file__)
            return os.path.join(dir, _pathname)

    def xml_to_dict(self, element, nsmap=None):
        def get_prefixed_tag(el):
            qname = ET.QName(el.tag)
            ns = [x for x,v in self.namespaces.items() if v==qname.namespace]
            if ns:
                return f"{ns[0]}:{qname.localname}"
            return  qname.localname

        children = list(element)
        if not children:
            return element.text.strip() if element.text else ""
        result = {}
        element_tag = get_prefixed_tag(element)
        result[element_tag] = ''
        if ':' not in element_tag:
            self.debug_print(element_tag)
        self.dimensions.add(element_tag)
        for child in children:
            if not isinstance(child.tag, str):
                continue  # Skip comments and special nodes
            tag = get_prefixed_tag(child)
            value = self.xml_to_dict(child, nsmap)
            if tag in result:
                if not isinstance(result[tag], list):
                    result[tag] = [result[tag]]
                result[tag].append(value)
            else:
                result[tag] = value
        return result

    def json_meta_file(self, taxonomy_base, json_meta_file): 
        namespaces = {
            'xbrli': 'http://www.xbrl.org/2003/instance',
            'xbrll': 'http://www.xbrl.org/2003/linkbase',
            'xlink': 'http://www.w3.org/1999/xlink',
            'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
            'gl-cor': 'http://www.xbrl.org/int/gl/cor/2025-12-01',
            'gl-muc': 'http://www.xbrl.org/int/gl/muc/2025-12-01',
            'gl-bus': 'http://www.xbrl.org/int/gl/bus/2025-12-01',
            'gl-usk': 'http://www.xbrl.org/int/gl/usk/2025-12-01',
            'gl-ehm': 'http://www.xbrl.org/int/gl/ehm/2025-12-01',
            'gl-taf': 'http://www.xbrl.org/int/gl/taf/2025-12-01',
            'gl-srcd': 'http://www.xbrl.org/int/gl/srcd/2025-12-01',
            'gl-plt': 'http://www.xbrl.org/int/gl/plt/2025-12-01',
            'iso4217': 'http://www.xbrl.org/2003/iso4217',
            'iso639': 'http://www.xbrl.org/2005/iso639',
            'ns0': "http://example.com"
        }
        palettes = [
            "case-c",
            "case-c-b",
            "case-c-b-m",
            "case-c-b-m-u",
            "case-c-b-m-u-e",
            "case-c-b-m-u-e-t",
            "case-c-b-m-u-e-t-s",
            "case-c-b-m-u-t",
            "case-c-b-m-u-t-s",
            "case-c-b-t",
            "case-c-t"
        ]
        for prefix in  self.unique_prefixes:
            namespaces[prefix] = f"http://www.{prefix}"
        json_meta = {
            "documentInfo": {
                "documentType": "https://xbrl.org/2021/xbrl-csv",
                "namespaces": namespaces
            },
            "tableTemplates": {
                "xbrl-gl_template": {
                    "dimensions": {
                        "period": "2025-05-17T00:00:00",
                        "entity": "ns0:Example Co.",
                    },
                    "columns": {},
                }
            },
            "tables": {"xbrl-gl_table": {"template": "xbrl-gl_template"}},
        }

        dimensions = [f.replace(":", "_") for f in self.dimension_fields]
        properties = [f.replace(":", "_") for f in self.non_dimension_fields]

        modules = set()
        for x in properties:
            modules.add(x[3:x.index("_")][0] )
        matching = [
            p for p in palettes
            if set(p.removeprefix("case-").split("-")) == modules
        ]
        self.debug_print(matching)
        if 1==len(matching):
            taxonomy = f"../gl-{matching[0]}/plt/gl-plt-oim-2025-12-01.xsd"
            json_meta["documentInfo"]["taxonomy"] = [taxonomy]
        else:
            taxonomy = f"{taxonomy_base}/gl-case-c-b-m-u-e-t-s/plt/gl-plt-oim-2025-12-01.xsd"

        for dimension in dimensions:
            dimension_name = dimension[3:]
            dimension_column = dimension.split("_", 1)[-1]
            json_meta["tableTemplates"]["xbrl-gl_template"]["dimensions"][
                f"gl-plt:d_{dimension_name}"
            ] = f"${dimension_column}"
            json_meta["tableTemplates"]["xbrl-gl_template"]["columns"][
                dimension_column
            ] = {}

        for property in properties:
            property_name = property[1 + property.index("_"):]
            property_module = property[: property.index("_")]
            if self.datatype_map[property.replace("_",":")].endswith("monetaryItemType"):
                json_meta["tableTemplates"]["xbrl-gl_template"]["columns"][
                    property_name
                ] = {
                    "dimensions": {
                        "concept": f"{property_module}:{property_name}",
                        "unit": f"iso4217:{self.currency.upper()}",
                    }
                }
            else:
                json_meta["tableTemplates"]["xbrl-gl_template"]["columns"][
                    property_name
                ] = {"dimensions": {"concept": f"{property_module}:{property_name}"}}

        csv_file = json_meta_file[1+json_meta_file.rindex(os.sep):].replace("json", "csv")
        json_meta["tables"]["xbrl-gl_table"]["url"] = csv_file

        try:
            with open(json_meta_file, "w", encoding=self.encoding) as file:
                json.dump(json_meta, file, ensure_ascii=False, indent=4)
            self.trace_print(f"JSON file '{json_meta_file}' has been created successfully.")
        except Exception as e:
            print(f"An error occurred while creating the JSON file: {e}")
        self.trace_print(f"JSON meta file {json_meta_file}")

        print("** END **")

    # Function to merge lines and delete unnecessary lines
    def merge_rows(self, records, dimensions):
        i = 0
        changed = True
        while changed:
            changed = False
            while i < len(records):
                row = records[i]
                self.debug_print(f"{i} row:{row}")
                dims = []
                for dim in dimensions:
                    targets = [k for k in row.keys() if k in self.parent and self.parent[k] in dimensions]
                    if row.get(dim) or dim in targets:
                        dims.append(dim)
                if len(dims) < 2:
                    i += 1
                    continue
                children = []
                for r in records: # look for another child having the same dimension
                    target_dims = dims[:-1]
                    d = dims[-1]
                    for dim in target_dims:
                        if dim not in row or dim not in r or row[dim]!= r[dim]:
                            continue
                    if d in r and row[d] != r[d]:
                        children.append(r)
                        break
                if 0==len(children):
                    # copy data to parent
                    condition = {key: row[key] for key in target_dims}
                    for r in records[:i]:
                        # If all parent dimensions match and no values exist in other dimensions, then set values
                        if all(r.get(k, "") == condition[k] for k in target_dims):
                            if all(not r.get(k, "") for k in dimensions if k not in target_dims):
                                if r:
                                    parent = r
                                    for k, v in row.items():
                                        if parent and k not in dimensions and k not in parent:
                                            parent[k] = v
                    self.debug_print(f"{i} parent: {parent}")
                    # Delete row
                    del records[i]
                    changed = True
                    break
                i += 1
        return records

    def convert(self):
        # Step 1: Read XML
        if not os.path.isfile(self.input_file):
            print(f"ERROR file not found {self.input_file}")
            return

        tree = ET.parse(self.input_file)
        root = tree.getroot()

        # Step 2: Define namespace map for XPath and parsing
        self.namespaces = {
            'xbrli': 'http://www.xbrl.org/2003/instance',
            'xbrll': 'http://www.xbrl.org/2003/linkbase',
            'xlink': 'http://www.w3.org/1999/xlink',
            'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
            'gl-cor': f'http://www.xbrl.org/int/gl/cor/{self.version}',
            'gl-muc': f'http://www.xbrl.org/int/gl/muc/{self.version}',
            'gl-bus': f'http://www.xbrl.org/int/gl/bus/{self.version}',
            'gl-usk': f'http://www.xbrl.org/int/gl/usk/{self.version}',
            'gl-ehm': f'http://www.xbrl.org/int/gl/ehm/{self.version}',
            'gl-taf': f'http://www.xbrl.org/int/gl/taf/{self.version}',
            'gl-srcd': f'http://www.xbrl.org/int/gl/srcd/{self.version}',
            'gl-plt': f'http://www.xbrl.org/int/gl/plt/{self.version}',
            'iso4217': 'http://www.xbrl.org/2003/iso4217',
            'iso639': 'http://www.xbrl.org/2005/iso639'
        }

        # Step 3: Convert XML to nested dictionary using namespace prefixes
        # Extract the root business object (e.g., accountingEntries)
        entries = root.xpath("/xbrli:xbrl/gl-cor:accountingEntries", namespaces=self.namespaces)
        if not entries:
            self.trace_print("ERROR: /xbrli:xbrl/gl-cor:accountingEntries not found.")
            return
        data_dict = self.xml_to_dict(entries[0], self.namespaces)

        # Step 4: Load combined structure (LHM + binding)
        binding_dict = {}

        # Step 5: Flatten the dictionary into tidy records
        dp = DataProcessor(binding_dict)
        dp.flatten_dict(data_dict)
        records = dp.get_records()
        if not records:
            self.trace_print("No records extracted.")
            return

        # Step 6: Write to CSV file
        # Only include fields that are actually used in records (i.e. appear in used_keys)
        # Dynamically determine all unique field names from all records
        qname_pattern = r'^[A-Za-z_][\w.-]*:[A-Za-z_][\w.-]*$' # QName regex pattern
        used_qname = set()
        used_keys = set()
        for r in records:
            used_keys.update(r.keys())
            for v in r.values():
                if isinstance(v, str) and re.fullmatch(qname_pattern, v):
                    used_qname.add(v)

        # Read and sort structure file rows by 'sequence' as integer (if available)
        with open(self.structure_file, mode="r", encoding=self.encoding) as f:
            sorted_rows = sorted(
                (row for row in csv.DictReader(f) if row.get("element")),
                key=lambda r: int(r["sequence"]) if r.get("sequence", "").isdigit() else 9999
            )
        # Extract and collect unique prefixes
        unique_prefixes = {qname.split(":")[0] for qname in used_qname if ":" in qname}
        self.unique_prefixes = [x for x in unique_prefixes if x not in self.namespaces.keys()]
        # Extract 'element' values from sorted rows if they appear in used_keys
        self.ordered_fieldnames = []
        self.ordered_fieldnames = [
            row["element"].strip()
            for row in sorted_rows
            if row.get("element", "").strip() in used_keys
            and row["element"].strip() not in self.ordered_fieldnames
        ]

        self.datatype_map = {}
        for row in sorted_rows:
            element = row["element"].strip()
            datatype = row["datatype"]
            self.datatype_map[element] = datatype

        levels = {}
        parents = [""]*10
        self.parent = {}
        for row in sorted_rows:
            element = row.get("element", "").strip()
            typ = row.get("type", "").strip()
            level = row.get("level", "").strip()
            self.debug_print(f"  → Element: {element}, Type: {typ}, Level: {level}")
            if level.isdigit():
                level = int(level)
            if 'C'==typ:
                levels[element] = level
                parents[level] = element
            elif level > 1:
                self.parent[element] = parents[level - 1]

        def set_dimension(element, dimension):
            level = levels[element]
            if dimension[level-1]:
                if element in dimension[level-1]:
                    dimension[level-1] = {element: 1 + dimension[level-1][element]}
                else:
                    dimension[level-1] = {element: 1}
            else:
                dimension[level-1] = {element: 1}
            for i in range(1+level,10):
                dimension[i-1] = None

        dimension = [None]*10
        idx = 0
        revised_records = []
        for row in records:
            idx = idx + 1
            element = list(row.keys())[0]
            if element in levels:
                set_dimension(element, dimension)
            self.debug_print(f"{idx} {dimension}")
            for item in dimension:
                if item and isinstance(item, dict):
                    for key, value in item.items():
                        row[key] = value
            revised_records.append(row)

        fieldnames = list(self.ordered_fieldnames)
        dimensions = [f for f in fieldnames if f in self.dimensions]
        merged_records = self.merge_rows(revised_records, dimensions)
        used_fields = set()
        for record in merged_records:
            for key in record:
                if record[key] not in [None, '', []]:  # 空でない値がある場合
                    used_fields.add(key)

        # Convert to field name without namespace
        self.dimension_fields = [f.replace(":", "_") for f in fieldnames if f in dimensions and f in used_fields]
        self.non_dimension_fields = [f.replace(":", "_") for f in fieldnames if f not in dimensions and f in used_fields]
        # These fields are used in json_meta_file()
        fieldnames = self.dimension_fields + self.non_dimension_fields
        local_fieldnames = [f.split("_", 1)[-1] for f in fieldnames]
        # Write to CSV file (this will create the file if it doesn't exist)
        with open(self.output_file, mode="w", newline="", encoding=self.encoding) as f:
            writer = csv.DictWriter(f, fieldnames=local_fieldnames)
            writer.writeheader()
            for row in merged_records:
                # Check if any of the fieldnames are included in the row
                if not any(f in [k.replace(":", "_") for k in row.keys()] for f in self.non_dimension_fields):
                    continue  # Skip if none
                # Convert key to local name also in output row
                local_row = {k.split(":", 1)[-1]: v for k, v in row.items()}
                writer.writerow(local_row)

        print(f"Tidy CSV written to: {self.output_file}")

        json_meta_file = f"{self.output_file[:-4]}.json"
        self.json_meta_file("../OIM-CSV/XBRL-GL-2025", json_meta_file)


def main():
    parser = argparse.ArgumentParser(description="Convert XBRL-GL XML instance to tidy hierarchical CSV.")
    parser.add_argument("-i", "--input", required=True, help="Input XBRL-GL XML file path")
    parser.add_argument("-n", "--version", required=True, help="Input XBRL-GL taxonomy version date")
    parser.add_argument("-s", "--structure", required=True, help="Combined structure CSV (LHM + binding)")
    parser.add_argument("-o", "--output", required=True, help="Output tidy CSV file path")
    parser.add_argument("-e", "--encoding", default="utf-8-sig", help="File encoding (default: utf-8-sig)")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-d", "--debug", action="store_true")

    args = parser.parse_args()

    converter = xBRLGL_StructuredCSV(
            input_file = args.input,
            version = args.version,
            structure_file = args.structure,
            output_file = args.output,
            encoding = args.encoding,
            trace = args.verbose,
            debug = args.debug
    )

    converter.convert()

if __name__ == "__main__":
    main()
