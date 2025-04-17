#!/usr/bin/env python3
# coding: utf-8
"""
XBRLGL_TaxonomyGenerator.py

This script generate XBRL GL Taxonomy.

designed by SAMBUICHI, Nobuyuki (Sambuichi Professional Engineers Office)
written by SAMBUICHI, Nobuyuki (Sambuichi Professional Engineers Office)

Creation Date: 2025-04-03
Last Modified: 2025-04-16

MIT License

(c) 2025 SAMBUICHI, Nobuyuki (Sambuichi Professional Engineers Office)

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
import os
import sys
import csv
import json
import re


class xBRLGL_TaxonomyGenerator:
    def __init__(
            self, 
            in_file,
            base_dir,
            root,
            lang,
            currency,
            namespace,
            encoding,
            trace,
            debug
        ):
        self.encoding = encoding
        self.records = []
        self.presentation_dict = {}
        self.dimension_dict = {}
        self.element_dict = {}
        self.role_map = {}

        self.lines = None
        self.locs_defined = None
        self.arcs_defined = None

        self.TRACE = trace
        self.DEBUG = debug

        self.encoding = encoding.strip() if encoding else "utf-8-sig"

        if in_file:
            self.core_file = self.file_path(in_file.strip())
        else:
            print(f"Input ADC definition CSV file {self.core_file} is missing.")
            sys.exit()
        if not os.path.isfile(self.core_file):
            print(f"Input ADC definition CSV file {self.core_file} does not exist.")
            sys.exit()

        if not base_dir:
            base_dir = ""
        self.base_dir = self.file_path(base_dir.strip())
        if not os.path.isdir(self.base_dir):
            os.makedirs(self.base_dir, exist_ok=True)
            self.trace_print(f"Created output base directory: {self.base_dir}")
        self.xbrl_base = self.base_dir.strip(os.sep)
        if not os.path.isdir(self.xbrl_base):
            os.makedirs(self.xbrl_base, exist_ok=True)
            self.trace_print(f"Created output base directory: {self.xbrl_base}")

        self.root = root.lstrip() if root else None

        self.lang = lang.lstrip() if lang else "ja"

        self.currency = currency.lstrip() if currency else "JPY"

        self.namespace = namespace.lstrip() if namespace else 'http://www.xbrl.org/xbrl-gl"'

        encoding = encoding.lstrip() if encoding else "utf-8-sig"

    def debug_print(self, text):
        if self.DEBUG:
            print(text)

    def trace_print(self, text):
        if self.TRACE:
            print(text)

    def file_path(self, pathname):
        _pathname = pathname.replace("/", os.sep)
        if os.sep == _pathname[0]:
            return _pathname
        dir = os.path.dirname(__file__)
        return os.path.join(dir, _pathname)

    # lower camel case concatenate
    def LC3(self, term):
        if not term:
            return ""
        terms = term.split(" ")
        name = ""
        for i in range(len(terms)):
            if i == 0:
                if "TAX" == terms[i]:
                    name += terms[i].lower()
                elif len(terms[i]) > 0:
                    name += terms[i][0].lower() + terms[i][1:]
            else:
                name += terms[i][0].upper() + terms[i][1:]
        return name

    def titleCase(self, text):
        text = text.replace("ID", "Identification Identifier")
        # Example Camel case string
        camel_case_str = text  # "exampleCamelCaseString"
        # Use regular expression to split the string at each capital letter
        split_str = re.findall("[A-Z][a-z]*[_]?", camel_case_str)
        # Join the split string with a space and capitalize each word
        title_case_str = " ".join([x.capitalize() for x in split_str])
        title_case_str = title_case_str.replace("Identification Identifier", "ID")
        return title_case_str

    # snake concatenate
    def SC(self, term):
        if not term:
            return ""
        terms = term.split(" ")
        name = "_".join(terms)
        return name

    def getRecord(self, element_id, abbreviation_path=None):
        if abbreviation_path:
            element_id = f"{abbreviation_path}_{element_id}"
        if "$." in element_id:
            record = next((x for x in self.records if element_id == x["semPath"]), None)
            if not record:
                record = next((x for x in self.records if x["semPath"].endswith(element_id)), None)
        else:
            record = next((x for x in self.records if element_id == x["abbrevPath"]), None)
            if not record:
                record = next((x for x in self.records if x["abbrevPath"].endswith(element_id)), None)
            if not record:
                record = next((x for x in self.records if x["element_id"]==element_id), None)
            if not record:
                record = next((x for x in self.records if x["element"]==element_id), None)
            if not record:
                record = next((x for x in self.records if f"$.{element_id}" == x["semPath"]), None)
        return record

    def getParent(self, element_id):
        if element_id in self.parent_dict:
            parent = self.parent_dict[element_id]
        else:
            parent = None
        return parent

    def getChildren(self, element_id):
        record = self.getRecord(element_id)
        if record:
            return record["children"]
        return []

    def getElementID(self, cor_id):
        record = self.getRecord(cor_id)
        if record:
            return record["element_id"]
        return None

    def domainMember(self, children, primary_id, abbreviation_path = None):
        # global count
        self.lines = []
        for _child_element_id in children: # children are abbrebiated name list
            if not _child_element_id:
                continue
            child = self.getRecord(_child_element_id, abbreviation_path)
            child_element_id = child['element_id']
            if not child_element_id:
                continue
            child_type = child["type"]
            child_name = child["name"]
            taxonomy_schema, link_id, href = self.roleRecord(child_element_id)
            if "C" == child_type:
                target_name = child_element_id[1+child_element_id.index('-'):]
                target_id = f"p_{target_name}"
                target_link = f"link_{target_name}"
                self.debug_print(
                    f'domain-member: {primary_id} to {target_id} {child["name"]} order={self.count} in {target_link} targetRole="http://www.xbrl.org/xbrl-gl/role/{target_link}'
                )
                self.lines.append(f"    <!-- {primary_id} to targetRole {target_link} -->\n")
                if primary_id not in self.locs_defined:
                    self.locs_defined[primary_id] = set()
                if not target_id in self.locs_defined[primary_id]:
                    self.locs_defined[primary_id].add(target_id)
                    self.lines.append(
                        f'    <link:loc xlink:type="locator" xlink:href="gl-plt-oim-2025-12-01.xsd#{target_id}" xlink:label="{target_id}" xlink:title="{target_id} {child_name}"/>\n'
                    )
                self.count += 1
                arc_id = f"{primary_id} TO {target_link}"
                if primary_id not in self.arcs_defined:
                    self.arcs_defined[primary_id] = set()
                if not arc_id in self.arcs_defined[primary_id]:
                    self.arcs_defined[primary_id].add(arc_id)
                    self.lines.append(
                        f'    <link:definitionArc xlink:type="arc" xlink:arcrole="http://xbrl.org/int/dim/arcrole/domain-member" xbrldt:targetRole="http://www.xbrl.org/xbrl-gl/role/{target_link}" xlink:from="{primary_id}" xlink:to="{target_id}" xlink:title="domain-member: {primary_id} to {target_id} in {target_link}" order="{self.count}"/>\n'
                    )
            else:
                self.debug_print(f'domain-member: {primary_id} to {child_element_id} {child["name"]} order={self.count}')
                if primary_id not in self.locs_defined:
                    self.locs_defined[primary_id] = set()
                if not child_element_id in self.locs_defined[primary_id]:
                    self.locs_defined[primary_id].add(child_element_id)
                    self.lines.append(
                        f'    <link:loc xlink:type="locator" xlink:href="{taxonomy_schema}#{child_element_id}" xlink:label="{child_element_id}" xlink:title="{child_element_id} {child_name}"/>\n'
                    )
                self.count += 1
                arc_id = f"{primary_id} TO {child_element_id}"
                if primary_id not in self.arcs_defined:
                    self.arcs_defined[primary_id] = set()
                if arc_id not in self.arcs_defined[primary_id]:
                    self.arcs_defined[primary_id].add(arc_id)
                    self.lines.append(
                        f'    <link:definitionArc xlink:type="arc" xlink:arcrole="http://xbrl.org/int/dim/arcrole/domain-member" xlink:from="{primary_id}" xlink:to="{child_element_id}" xlink:title="domain-member: {primary_id} to {child_element_id} {child["name"]}" order="{self.count}"/>\n'
                    )
        return self.lines

    def defineHypercube(self, root):
        dimension_id_list = []
        taxonomy_schema, link_id, href = self.roleRecord(root['element_id'])
        path = root["xpath"] or root['element_id']
        if not path:
            path = root["abbrevPath"]
            paths = path.split("_")[1:]
            for id in paths:
                schema_id = self.getElementID(id)
                dimension_id = f"d_{schema_id[3:]}"
                dimension_id_list.append(dimension_id)
        else:
            paths = path.strip("/").split("/") #[1:]
            for id in paths:
                schema_id = self.getElementID(id)
                dimension_id = f"d_{schema_id[3:]}"
                dimension_id_list.append(dimension_id)
        element_id = f"gl-{link_id[5:]}"
        self.locs_defined[link_id] = set()
        self.arcs_defined[link_id] = set()
        primary_name = element_id[1+element_id.index('-'):]
        hypercube_id = f"h_{primary_name}"
        primary_id = f"p_{primary_name}"
        self.lines += [
            f'  <link:definitionLink xlink:type="extended" xlink:role="http://www.xbrl.org/xbrl-gl/role/{link_id}">\n',
            # all (has-hypercube)
            f"    <!-- {primary_id} all (has-hypercube) {hypercube_id} {link_id} -->\n",
            f'    <link:loc xlink:type="locator" xlink:href="gl-plt-oim-2025-12-01.xsd#{primary_id}" xlink:label="{primary_id}" xlink:title="{primary_id}"/>\n',
            f'    <link:loc xlink:type="locator" xlink:href="gl-plt-oim-2025-12-01.xsd#{hypercube_id}" xlink:label="{hypercube_id}" xlink:title="{hypercube_id}"/>\n',
            f'    <link:definitionArc xlink:type="arc" xlink:arcrole="http://xbrl.org/int/dim/arcrole/all" xlink:from="{primary_id}" xlink:to="{hypercube_id}" xlink:title="all (has-hypercube): {primary_id} to {hypercube_id}" order="1" xbrldt:closed="true" xbrldt:contextElement="segment"/>\n',
        ]
        self.debug_print(f"all(has-hypercube) {primary_id} to {hypercube_id} ")
        # hypercube-dimension
        self.lines.append("    <!-- hypercube-dimension -->\n")
        self.count = 0
        for dimension_id in dimension_id_list:
            self.lines.append(
                f'    <link:loc xlink:type="locator" xlink:href="gl-plt-oim-2025-12-01.xsd#{dimension_id}" xlink:label="{dimension_id}" xlink:title="{dimension_id}"/>\n'
            )
            self.count += 1
            self.lines.append(
                f'    <link:definitionArc xlink:type="arc" xlink:arcrole="http://xbrl.org/int/dim/arcrole/hypercube-dimension" xlink:from="{hypercube_id}" xlink:to="{dimension_id}" xlink:title="hypercube-dimension: {hypercube_id} to {dimension_id}" order="{self.count}"/>\n'
            )
            self.debug_print(f"hypercube-dimension {hypercube_id} to {dimension_id} ")
        # domain-member
        self.lines.append("    <!-- domain-member -->\n")
        element_id = root['element_id']
        record = next((x for x in self.records if element_id == x["element_id"]), None)
        abbreviation_path = record['abbrevPath']
        dimension = self.dimension_dict[abbreviation_path]
        if 'children' in dimension:
            children = dimension["children"]
            self.lines += self.domainMember(children, primary_id, abbreviation_path)
        self.lines.append("  </link:definitionLink>\n")

    def roleRecord(self, _element_id):
        record = self.getRecord(_element_id)
        element_id = record["element_id"]
        module = element_id[3:element_id.index("_")]
        taxonomy_schema = f"../{module}/gl-{module}-2025-12-01.xsd"
        link_id = f"link_{element_id[3:]}"
        href = f"{taxonomy_schema}/{link_id}"
        return taxonomy_schema, link_id, href

    def linkPresentation(self, _module, element_id, children, n):
        if not element_id:
            return
        order = 0
        record = next((x for x in self.records if element_id == x["element_id"]), None)
        if not record:
            return
        module = element_id[: element_id.index("_")][3:]
        name = record["name"]
        if not element_id in self.locs_defined:
            self.locs_defined[element_id] = name
            self.lines.append(f"    <!-- {name} -->\n")
            if _module==module:
                self.lines.append(
                    f'    <loc xlink:type="locator" xlink:href="gl-{module}-2025-12-01.xsd#{element_id}" xlink:label="{element_id}" xlink:title="loc: {element_id}"/>\n'
                )
            else:
                self.lines.append(
                    f'    <loc xlink:type="locator" xlink:href="../{module}/gl-{module}-2025-12-01.xsd#{element_id}" xlink:label="{element_id}" xlink:title="loc: {element_id}"/>\n'
                )
        for child_element_id in children:
            if not child_element_id:
                continue
            child = next((x for x in self.records if child_element_id == x["element_id"]), None)
            child_module = child_element_id[3:child_element_id.index("_")]
            child_name = child["name"]
            order += 10
            arc_id = f"{element_id} to {child_element_id}"
            if arc_id not in self.arcs_defined:
                self.arcs_defined[arc_id] = f"presentation: {element_id} to {child_element_id}"
                if _module==child_module:
                    self.lines += [
                        f'    <loc xlink:type="locator" xlink:href="gl-{child_module}-2025-12-01.xsd#{child_element_id}" xlink:label="{child_element_id}" xlink:title="presentation: {element_id} to {child_element_id} {child_name}"/>\n',
                        f'    <presentationArc xlink:type="arc" xlink:arcrole="http://www.xbrl.org/2003/arcrole/parent-child" xlink:from="{element_id}" xlink:to="{child_element_id}" xlink:title="presentation: {element_id} to {child_element_id}" use="optional" order="{order}"/>\n',
                    ]
                else:
                    self.lines += [
                        f'    <loc xlink:type="locator" xlink:href="../{child_module}/gl-{child_module}-2025-12-01.xsd#{child_element_id}" xlink:label="{child_element_id}" xlink:title="presentation: {element_id} to {child_element_id} {child_name}"/>\n',
                        f'    <presentationArc xlink:type="arc" xlink:arcrole="http://www.xbrl.org/2003/arcrole/parent-child" xlink:from="{element_id}" xlink:to="{child_element_id}" xlink:title="presentation: {element_id} to {child_element_id}" use="optional" order="{order}"/>\n',
                    ]
            if child_element_id in self.presentation_dict:
                grand_children = self.presentation_dict[child_element_id]
                self.linkPresentation(_module, child_element_id, grand_children, n + 1)
        children = None

    def escape_text(str):
        if not str:
            return ""
        escaped = str.replace("<", "&lt;")
        escaped = escaped.replace(">", "&gt;")
        return escaped

    def load_csv_data(self):
        # ====================================================================
        # 1. csv -> schema
        self.records = []
        self.dimension_dict = {}
        self.parent_dict = {}
        self.presentation_dict = {}

        level_presentation = [None] * 10
        level_dimension = [None] * 10

        header = [
            "sequence",
            "level",
            "type",
            "identifier",
            "name",
            "datatype",
            "multiplicity",
            "domainName",
            "definition",
            "module",
            "table",
            "classTerm",
            "id",
            "path",
            "semPath",
            "abbrevPath",
            "labelLocal",
            "definitionLocal",
            "element",
            "xpath",
        ]

        with open(self.core_file, encoding=self.encoding, newline="") as f:
            reader = csv.reader(f)
            next(reader)
            semSort = 1
            for cols in reader:
                record = {}
                for i in range(len(header)):
                    if i < len(cols):
                        col = cols[i]
                        record[header[i]] = col.strip()
                semPath = record["semPath"]
                abbrevPath = record["abbrevPath"].replace(".","_")
                if not abbrevPath:
                    continue
                d_level = len(abbrevPath.split("_"))
                # get root id from semantic path and check format
                _type = record["type"]
                if "_" in abbrevPath:
                    cor_id = abbrevPath[1+abbrevPath.rindex("_"):]  # terminal is
                else:
                    cor_id = abbrevPath
                if "C" == _type:
                    class_id = cor_id
                elif "R"==_type:
                    continue
                semSort = record["sequence"]
                identifier = record["identifier"]
                level = int(record["level"])
                objectClass = record["classTerm"]
                multiplicity = record["multiplicity"]
                name = record["name"]
                datatype = record["datatype"]
                element = record["element"]
                element_id = element.replace(":", "_")
                xpath = record["xpath"]
                if "REF" == identifier:
                    level = level - 1
                data = {
                    "level": level,
                    "semSort": int(semSort),
                    "d_level": d_level,
                    "type": _type,
                    "class_id": class_id,
                    "identifier": identifier,
                    "name": name,
                    "datatype": datatype,
                    "element": element,
                    "element_id": element_id,
                    "objectClass": objectClass,
                    "multiplicity": multiplicity,
                    "semPath": semPath,
                    "abbrevPath": abbrevPath,
                    "xpath": xpath,
                    "definition": record["definition"],
                    "labelLocal": record["labelLocal"],
                    "definitionLocal": record["definitionLocal"],
                    "id": cor_id,
                }
                if 1 == int(level):
                    level_presentation[level] = element_id
                    if element_id not in self.presentation_dict:
                        self.presentation_dict[element_id] = []
                    level_dimension[d_level] = cor_id
                elif int(level) > 1:
                    """
                    presentation link
                    """
                    level_presentation[level] = element_id
                    if "C" == _type:
                        if level > 1:
                            parent_id = level_presentation[level - 1]
                            data["parent_id"] = parent_id
                            if parent_id not in self.presentation_dict:
                                self.presentation_dict[parent_id] = []
                            if element_id not in self.presentation_dict[parent_id]:
                                self.presentation_dict[parent_id].append(element_id)
                    else:
                        parent_id = level_presentation[level - 1]
                        data["parent_id"] = parent_id
                        if parent_id not in self.presentation_dict:
                            self.presentation_dict[parent_id] = []
                        if element_id not in self.presentation_dict[parent_id]:
                            self.presentation_dict[parent_id].append(element_id)
                    """
                    definition link
                    """
                    _id = data["abbrevPath"]
                    level_dimension[d_level] = _id
                    d_parent = ""
                    if "_" in abbrevPath:
                        d_parent = '_'.join(abbrevPath.split("_")[:-1])
                    data["parent_sem_id"] = d_parent
                    if d_parent and d_parent not in self.dimension_dict:
                        parent_record = next(
                            (x for x in self.records if x["abbrevPath"].endswith(d_parent)), None
                        )
                        if not parent_record:
                            pass
                        multiplicity = parent_record["multiplicity"]
                        parent_id = parent_record["element"] if "*"==multiplicity[-1] else None
                        self.dimension_dict[d_parent] = {
                            "parent_id": parent_id,
                            "multiplicity": multiplicity,
                            "children": [],
                        }
                    if d_parent and cor_id not in self.dimension_dict[d_parent]["children"]:
                        if cor_id:
                            self.dimension_dict[d_parent]["children"].append(cor_id)
                self.records.append(data)

        filtered_records = []
        for data in self.records:
            _id = data["abbrevPath"]
            if "A"==data["type"] or _id in self.dimension_dict:
                filtered_records.append(data)
        self.records = filtered_records
        
    def process_records(self):
        for cor_id, record in list(self.dimension_dict.items()):
            if "children" in record:
                children = record["children"]
                for child_element_id in children:
                    child = self.getRecord(child_element_id)
                    if child and "C" == child["type"]:
                        if child["multiplicity"].endswith("*"):
                            child_element_id = child["element_id"]
                            parent_element_id = self.getElementID(cor_id)
                            self.parent_dict[child_element_id] = parent_element_id

        self.roleMap = {}
        for cor_id, data in self.dimension_dict.items():
            record = self.getRecord(cor_id)
            self.roleMap[record["element_id"]] = record

    def generate_taxonomy_files(self, xbrl_base):
        if not xbrl_base:
            xbrl_base = self.xbrl_base
        ###################################
        # xBRL GD Pallete Schema
        #
        elementsDefined = set()
        element_dict = {}

        for parent_id, children in self.presentation_dict.items():
            parent_record = next((x for x in self.records if parent_id == x["element_id"]), None)
            if not parent_record:
                continue
            parent_element = parent_id.replace("_", ":")
            parent_module = parent_id[3:parent_id.index("_")]
            if parent_module not in element_dict:
                element_dict[parent_module] = []
            _parent_record = next((x for x in element_dict[parent_module] if parent_element == x["element"]), None)
            if not _parent_record:
                element_data = {
                    "element": parent_element,
                    "id": parent_record["id"],
                    "name": parent_record["name"],
                    "definition": parent_record["definition"],
                    "label_local": parent_record["labelLocal"],
                    "definition_local": parent_record["definitionLocal"],
                    "multiplicity": "",
                    "datatype": "",
                    "children": children,
                }
                element_dict[parent_module].append(element_data)

            for element_id in children:
                record = next((x for x in self.records if element_id == x["element_id"]), None)
                if not record:
                    continue
                element = record["element"]
                if not element:
                    continue
                id = record["id"]
                module = element[3:element.index(":")]
                if module not in element_dict:
                    element_dict[module] = []
                multiplicity = record["multiplicity"]
                datatype = record["datatype"]
                name = record["name"]
                definition = record["definition"]
                label_local = record["labelLocal"]
                definition_local = record["definitionLocal"]
                if element_id in self.presentation_dict:
                    _children = self.presentation_dict[element_id]
                    element_data = {
                        "element": element,
                        "id": id,
                        "name": name,
                        "definition": definition,
                        "label_local": label_local,
                        "definition_local": definition_local,
                        "multiplicity": multiplicity,
                        "datatype": datatype,
                        "children": _children,
                    }
                    if element_data not in element_dict[module]:
                        element_dict[module].append(element_data)
                else:
                    element_data = {
                        "element": element,
                        "id": id,
                        "name": name,
                        "definition": definition,
                        "label_local": label_local,
                        "definition_local": definition_local,
                        "multiplicity": multiplicity,
                        "datatype": datatype,
                    }
                    if element_data not in element_dict[module]:
                        element_dict[module].append(element_data)

        for module, data in element_dict.items():
            modules = set()
            for record in data:
                datatype = record["element"]
                _module = datatype[3:datatype.index(":")]
                modules.add(_module)

            """
            Module taxonomy schema
            """
            html = [
                '<?xml version="1.0" encoding="UTF-8"?>\n',
                "<!-- (c) XBRL International.  See http://www.xbrl.org/legal -->\n",
                f'<schema targetNamespace="http://www.xbrl.org/int/gl/{module}/2025-12-01" attributeFormDefault="unqualified" elementFormDefault="qualified"\n',
                '  xmlns="http://www.w3.org/2001/XMLSchema"\n',
                '  xmlns:link="http://www.xbrl.org/2003/linkbase"\n'
                '  xmlns:xlink="http://www.w3.org/1999/xlink"\n',
                '  xmlns:xbrli="http://www.xbrl.org/2003/instance"\n',
                '  xmlns:xbrldt="http://xbrl.org/2005/xbrldt"\n',
            ]
            for _module in modules:
                html.append(
                    f'  xmlns:gl-{_module}="http://www.xbrl.org/int/gl/{_module}/2025-12-01"\n'
                )
            html.append(
                ">\n"
            )

            html += [
                '  <import namespace="http://www.xbrl.org/2003/instance" schemaLocation="http://www.xbrl.org/2003/xbrl-instance-2003-12-31.xsd"/>\n',
                '  <import namespace="http://www.xbrl.org/2003/linkbase" schemaLocation="http://www.xbrl.org/2003/xbrl-linkbase-2003-12-31.xsd"/>\n',
                '  <import namespace="http://xbrl.org/2005/xbrldt" schemaLocation="http://www.xbrl.org/2005/xbrldt-2005.xsd"/>\n',
            ]

            for _module in modules:
                if _module != module:
                    html.append(
                        f'  <import namespace="http://www.xbrl.org/int/gl/{_module}/2025-12-01" schemaLocation="../gen/gl-gen-2025-12-01.xsd"/>\n'
                    )

            html += [
                "  <annotation>\n",
                "    <appinfo>\n",
                f'      <link:linkbaseRef xlink:type="simple" xlink:href="gl-{_module}-2025-12-01-presentation.xml" xlink:title="Presentation Links, all" xlink:role="http://www.xbrl.org/2003/role/presentationLinkbaseRef" xlink:arcrole="http://www.w3.org/1999/xlink/properties/linkbase"/>\n'
            ]

            html += [
                "    </appinfo>\n",
                "  </annotation>\n"
            ]

            html.append("  <!-- item element -->\n")
            for line in data:
                element = line["element"]
                name = element[1 + element.index(":"):]
                element_id = element.replace(":", "_")
                multiplicity = line["multiplicity"]
                datatype = line["datatype"]
                if element in elementsDefined:
                    continue
                elementsDefined.add(element)
                if datatype:
                    html.append(
                        f'  <element name="{name}" id="{element_id}" type="{datatype}" substitutionGroup="xbrli:item" nillable="true" xbrli:periodType="instant"/>\n'
                    )
                    # html+= [
                    #     f' \n<complexType name="{name}ItemType">\n',
                    #     f'    <simpleContent>\n',
                    #     f'      <restriction base="{datatype}"/>\n',
                    #     f'    </simpleContent>\n',
                    #     f'  </complexType>\n',
                    #     f'  <element name="{name}" id="{element_id}" type="{name}ItemType" substitutionGroup="xbrli:item" nillable="true" xbrli:periodType="instant"/>\n'
                    # ]
                else:
                    html.append(
                        f'  <element name="{name}" id="{element_id}" type="{element}ComplexType" substitutionGroup="xbrli:tuple" nillable="false"/>\n'
                    )
            html.append("</schema>")

            """
            Write module taxonomy schema file
            """
            xsd_file = self.file_path(
                f"{xbrl_base}/{module}/gl-{module}-2025-12-01.xsd"
            )
            directory = os.path.dirname(xsd_file)
            if not os.path.isdir(directory):
                os.makedirs(directory, exist_ok=True)
                self.trace_print(f"Created moduke taxonomy schema directory: {directory}")            
            with open(xsd_file, "w", encoding=self.encoding, newline="") as f:
                f.writelines(html)
            self.trace_print(f"-- {xsd_file}")

        """
        Module content schema file
        """
        for module, data in element_dict.items():
            modules = set()
            for record in data:
                if "children" in record:
                    children = record["children"]
                    for child in children:
                        if not child:
                            continue
                        _module = child[3:child.index("_")]
                        modules.add(_module)
                else:
                    continue

            html = [
                '<?xml version="1.0" encoding="UTF-8"?>\n',
                "<!-- (c) XBRL International.  See http://www.xbrl.org/legal -->\n",
                f'<schema targetNamespace="http://www.xbrl.org/int/gl/{module}/2025-12-01" elementFormDefault="qualified" attributeFormDefault="unqualified"\n',
                '  xmlns="http://www.w3.org/2001/XMLSchema"\n',
                '  xmlns:xlink="http://www.w3.org/1999/xlink"\n',
                '  xmlns:xbrli="http://www.xbrl.org/2003/instance"\n',
            ]

            for _module in modules:
                if _module != module:
                    html.append(
                        f'  xmlns:gl-{_module}="http://www.xbrl.org/int/gl/{_module}/2025-12-01"\n'
                    )
            html.append(
                f'  xmlns:gl-{module}="http://www.xbrl.org/int/gl/{module}/2025-12-01">\n'
            )
            html.append(
                '  <import namespace="http://www.xbrl.org/2003/instance" schemaLocation="http://www.xbrl.org/2003/xbrl-instance-2003-12-31.xsd"/>\n'
            )
            for _module in modules:
                if _module != module:
                    html.append(
                        f'  <import namespace="http://www.xbrl.org/int/gl/{_module}/2025-12-01" schemaLocation="gl-{_module}-content-2025-12-01.xsd"/>\n'
                    )
            html.append(
                f'  <include schemaLocation="../{module}/gl-{module}-2025-12-01.xsd"/>\n'
            )
            html.append("  <!-- tuple data type -->\n")
            for record in data:
                element = record["element"]
                if record["datatype"]:
                    continue
                element_name = element[1 + element.index(":"):]
                module = element[3:element.index(":")]
                if "children" in record:
                    children = record["children"]
                    if 'choice' in record['name'].lower():
                        html += [
                            f'  <complexType name="{element_name}ComplexType">\n',
                            "    <choice>\n",
                        ]
                        sequence = []
                        for child_element_id in children:
                            child_name = child_element_id[1 + child_element_id.index("_"):]
                            child_module = child_element_id[3:child_element_id.index("_")]
                            child_record = next(
                                (x for x in self.records if child_element_id == x["element_id"]), None
                            )
                            if not child_record:
                                continue
                            _name = child_record['name']
                            if 'sequence' in _name:
                                sequence.append(child_record)
                                continue
                            child_multiplicity = child_record["multiplicity"]
                            min_occurs = child_multiplicity[0]
                            max_occurs = child_multiplicity[-1]
                            if "*" == max_occurs:
                                max_occurs = "unbounded"
                            if '1'==min_occurs:
                                if '1'==max_occurs:
                                    html.append(f'      <element ref="gl-{child_module}:{child_name}"/>\n')
                                else:
                                    html.append(f'      <element ref="gl-{child_module}:{child_name}" maxOccurs="{max_occurs}"/>\n')
                            else:
                                if '1'==max_occurs:
                                    html.append(f'      <element ref="gl-{child_module}:{child_name}" minOccurs="{min_occurs}"/>\n')
                                else:
                                    html.append(f'      <element ref="gl-{child_module}:{child_name}" minOccurs="{min_occurs}" maxOccurs="{max_occurs}"/>\n')
                        if len(sequence) > 0:
                            html.append(f'      <sequence>\n')
                            for _record in sequence:
                                _multiplicity = _record["multiplicity"]
                                min_occurs = _multiplicity[0]
                                max_occurs = _multiplicity[-1]
                                _name = _record['xpath'].split('/')[-1]
                                if "*" == max_occurs:
                                    max_occurs = "unbounded"
                                if '1'==min_occurs:
                                    if '1'==max_occurs:
                                        html.append(f'        <element ref="{_name}"/>\n')
                                    else:
                                        html.append(f'        <element ref="{_name}" maxOccurs="{max_occurs}"/>\n')
                                else:
                                    if '1'==max_occurs:
                                        html.append(f'        <element ref="{_name}" minOccurs="{min_occurs}"/>\n')
                                    else:
                                        html.append(f'        <element ref="{_name}" minOccurs="{min_occurs}" maxOccurs="{max_occurs}"/>\n')
                            html.append(f'      </sequence>\n')
                        html += [
                            "    </choice>\n",
                            '    <attribute name="id" type="ID"/>\n',
                            f'  </complexType>\n',
                        ]                        
                    else:
                        html += [
                            f'  <group name="{element_name}Group">\n',
                            "    <sequence>\n"
                        ]
                        choice = []
                        for child_element_id in children:
                            if not child_element_id:
                                continue
                            child_name = child_element_id[1 + child_element_id.index("_"):]
                            child_module = child_element_id[3:child_element_id.index("_")]
                            child_record = next(
                                (x for x in self.records if child_element_id == x["element_id"]), None
                            )
                            _name = child_record['name']
                            if 'choice' in _name and 'choice' not in child_record['objectClass']:
                                choice.append(child_record)
                                continue
                            child_multiplicity = child_record["multiplicity"]
                            min_occurs = child_multiplicity[0]
                            max_occurs = child_multiplicity[-1]
                            if "*" == max_occurs:
                                max_occurs = "unbounded"
                            child_datatype = child_record["datatype"]
                            if child_datatype:
                                if '1'==min_occurs:
                                    if '1'==max_occurs:
                                        html.append(f'      <element ref="gl-{child_module}:{child_name}"/>\n')
                                    else:
                                        html.append(f'      <element ref="gl-{child_module}:{child_name}" maxOccurs="{max_occurs}"/>\n')
                                else:
                                    if '1'==max_occurs:
                                        html.append(f'      <element ref="gl-{child_module}:{child_name}" minOccurs="{min_occurs}"/>\n')
                                    else:
                                        html.append(f'      <element ref="gl-{child_module}:{child_name}" minOccurs="{min_occurs}" maxOccurs="{max_occurs}"/>\n')
                            else: # null datatype is a tuple
                                if "(choice)" in child_record['name']: # choice
                                    if '1'==min_occurs:
                                        if '1'==max_occurs:
                                            html.append(f'      <element ref="gl-{child_module}:{child_name}"/>\n')
                                        else:
                                            html.append(f'      <element ref="gl-{child_module}:{child_name}" maxOccurs="{max_occurs}"/>\n')
                                    else:
                                        if '1'==max_occurs:
                                            html.append(f'      <element ref="gl-{child_module}:{child_name}" minOccurs="{min_occurs}"/>\n')
                                        else:
                                            html.append(f'      <element ref="gl-{child_module}:{child_name}" minOccurs="{min_occurs}" maxOccurs="{max_occurs}"/>\n')
                                else:
                                    html += [
                                        "      <choice>\n",
                                        f'        <group ref="gl-{child_module}:{child_name}Group" minOccurs="0"/>\n',
                                        f'        <element ref="gl-{child_module}:{child_name}" maxOccurs="unbounded"/>\n',
                                        "      </choice>\n",
                                    ]
                        if len(choice) > 0:
                            html.append(f'      <choice>\n')
                            for _record in choice:
                                _multiplicity = _record["multiplicity"]
                                min_occurs = _multiplicity[0]
                                max_occurs = _multiplicity[-1]
                                _name = _record['xpath'].split('/')[-1]
                                if "*" == max_occurs:
                                    max_occurs = "unbounded"
                                if '1'==min_occurs:
                                    if '1'==max_occurs:
                                        html.append(f'        <element ref="{_name}"/>\n')
                                    else:
                                        html.append(f'        <element ref="{_name}" maxOccurs="{max_occurs}"/>\n')
                                else:
                                    if '1'==max_occurs:
                                        html.append(f'        <element ref="{_name}" minOccurs="{min_occurs}"/>\n')
                                    else:
                                        html.append(f'        <element ref="{_name}" minOccurs="{min_occurs}" maxOccurs="{max_occurs}"/>\n')
                            html.append(f'      </choice>\n')
                        html += [
                            "    </sequence>\n",
                            "  </group>\n",
                            f'  <complexType name="{element_name}ComplexType">\n',
                            "    <complexContent>\n",
                            '      <restriction base="anyType">\n',
                            "        <sequence>\n",
                            f'          <group ref="gl-{module}:{element_name}Group"/>\n',
                            "        </sequence>\n",
                            '        <attribute name="id" type="ID"/>\n',
                            "      </restriction>\n",
                            "    </complexContent>\n",
                            "  </complexType>\n",
                        ]
                    
            html.append("</schema>")
            
            """
            Write module content schema file
            """
            directory = self.file_path(
                f"{xbrl_base}/plt"
            )
            if not os.path.isdir(directory):
                os.makedirs(directory, exist_ok=True)
                self.trace_print(f"Created moduke schema directory: {directory}")
            xsd_file = self.file_path(
                f"{xbrl_base}/plt/gl-{module}-content-2025-12-01.xsd"
            )
            with open(xsd_file, "w", encoding=self.encoding, newline="") as f:
                f.writelines(html)
            self.trace_print(f"-- {xsd_file}")

        html = [
            '<?xml version="1.0" encoding="UTF-8"?>\n',
            "<!-- (c) XBRL International.  See http://www.xbrl.org/legal -->\n",
            '<schema targetNamespace="http://www.xbrl.org/int/gl/plt/2025-12-01" attributeFormDefault="unqualified" elementFormDefault="qualified"\n',
            '  xmlns="http://www.w3.org/2001/XMLSchema"\n',
            '  xmlns:xbrli="http://www.xbrl.org/2003/instance"\n',
            '  xmlns:link="http://www.xbrl.org/2003/linkbase"\n',
            '  xmlns:xlink="http://www.w3.org/1999/xlink"\n',
            '  xmlns:xbrldt="http://xbrl.org/2005/xbrldt"\n',
            '  xmlns:gl-plt="http://www.xbrl.org/int/gl/plt/2025-12-01">\n'
        ]

        modules = element_dict.keys()
        for module in modules:
            if _module != module:
                html.append(
                    f'  <import namespace="http://www.xbrl.org/int/gl/{module}/2025-12-01" schemaLocation="../{module}/gl-{module}-2025-12-01.xsd"/>\n'
                )

        html += [
            '  <import namespace="http://www.xbrl.org/2003/instance" schemaLocation="http://www.xbrl.org/2003/xbrl-instance-2003-12-31.xsd"/>\n',
            '  <import namespace="http://www.xbrl.org/2003/linkbase" schemaLocation="http://www.xbrl.org/2003/xbrl-linkbase-2003-12-31.xsd"/>\n',
            '  <import namespace="http://xbrl.org/2005/xbrldt" schemaLocation="http://www.xbrl.org/2005/xbrldt-2005.xsd"/>\n',
            '  <import namespace="http://www.xbrl.org/int/gl/cor/2025-12-01" schemaLocation="gl-cor-content-2025-12-01.xsd"/>\n'
        ]

        html += [
            "  <annotation>\n",
            "    <appinfo>\n"
        ]
        for module in modules:
            html += [
                f'      <link:linkbaseRef xlink:type="simple" xlink:href="../{module}/lang/gl-{module}-2025-12-01-label.xml" xlink:title="Label Links, all" xlink:role="http://www.xbrl.org/2003/role/labelLinkbaseRef" xlink:arcrole="http://www.w3.org/1999/xlink/properties/linkbase"/>\n',
                f'      <link:linkbaseRef xlink:type="simple" xlink:href="../{module}/lang/gl-{module}-2025-12-01-label-ja.xml" xlink:title="Label Links, ja" xlink:role="http://www.xbrl.org/2003/role/labelLinkbaseRef" xlink:arcrole="http://www.w3.org/1999/xlink/properties/linkbase"/>\n'
            ]

        html += [
            "    </appinfo>\n",
            "  </annotation>\n"
        ]

        html.append(
            "</schema>\n"
        )

        """
        Write palette schema file
        """
        xsd_file = self.file_path(
            f"{xbrl_base}/plt/gl-plt-all-2025-12-01.xsd"
        )
        with open(xsd_file, "w", encoding=self.encoding, newline="") as f:
            f.writelines(html)
        self.trace_print(f"Write palette schema file {xsd_file}")

        """
        OIM schema
        """
        modules = element_dict.keys()
        html = [
            '<?xml version="1.0" encoding="UTF-8"?>\n',
            "<!-- (c) XBRL International.  See http://www.xbrl.org/legal -->\n",
            '<schema targetNamespace="http://www.xbrl.org/int/gl/plt/2025-12-01" attributeFormDefault="unqualified" elementFormDefault="qualified"\n',
            '  xmlns="http://www.w3.org/2001/XMLSchema"\n',
            '  xmlns:xbrli="http://www.xbrl.org/2003/instance"\n',
            '  xmlns:link="http://www.xbrl.org/2003/linkbase"\n',
            '  xmlns:xlink="http://www.w3.org/1999/xlink"\n',
            '  xmlns:xbrldt="http://xbrl.org/2005/xbrldt"\n',
            '  xmlns:gl-plt="http://www.xbrl.org/int/gl/plt/2025-12-01">\n'
        ]

        for module in modules:
            if _module != module:
                html.append(
                    f'  <import namespace="http://www.xbrl.org/int/gl/{module}/2025-12-01" schemaLocation="../{module}/gl-{module}-2025-12-01.xsd"/>\n'
                )

        html += [
            '  <import namespace="http://www.xbrl.org/2003/instance" schemaLocation="http://www.xbrl.org/2003/xbrl-instance-2003-12-31.xsd"/>\n',
            '  <import namespace="http://www.xbrl.org/2003/linkbase" schemaLocation="http://www.xbrl.org/2003/xbrl-linkbase-2003-12-31.xsd"/>\n',
            '  <import namespace="http://xbrl.org/2005/xbrldt" schemaLocation="http://www.xbrl.org/2005/xbrldt-2005.xsd"/>\n',
            '  <import namespace="http://www.xbrl.org/int/gl/cor/2025-12-01" schemaLocation="gl-cor-content-2025-12-01.xsd"/>\n'
        ]

        html += [
            "  <annotation>\n",
            "    <appinfo>\n"
        ]

        for module in modules:
            html += [
                f'      <link:linkbaseRef xlink:type="simple" xlink:href="../{module}/lang/gl-{module}-2025-12-01-label.xml" xlink:title="Label Links, all" xlink:role="http://www.xbrl.org/2003/role/labelLinkbaseRef" xlink:arcrole="http://www.w3.org/1999/xlink/properties/linkbase"/>\n',
                f'      <link:linkbaseRef xlink:type="simple" xlink:href="../{module}/lang/gl-{module}-2025-12-01-label-ja.xml" xlink:title="Label Links, ja" xlink:role="http://www.xbrl.org/2003/role/labelLinkbaseRef" xlink:arcrole="http://www.w3.org/1999/xlink/properties/linkbase"/>\n'
            ]

        html.append(
            f'      <link:linkbaseRef xlink:type="simple" xlink:href="gl-plt-def-2025-12-01.xml" xlink:title="Definition" xlink:role="http://www.xbrl.org/2003/role/definitionLinkbaseRef" xlink:arcrole="http://www.w3.org/1999/xlink/properties/linkbase"/>\n',
        )

        html += [
            "      <!-- \n",
            "        role type\n",
            "      -->\n",
            '      <link:roleType id="xbrl-gl-role" roleURI="http://www.xbrl.org/xbrl-gl/role">\n',
            "        <link:definition>link xbrl-gl</link:definition>\n",
            "        <link:usedOn>link:definitionLink</link:usedOn>\n",
            "        <link:usedOn>link:presentationLink</link:usedOn>\n",
            "      </link:roleType>\n"
        ]

        for element_id in self.roleMap.keys():
            element_name = element_id[3:]
            html += [
                f'      <link:roleType id="link_{element_name}" roleURI="http://www.xbrl.org/xbrl-gl/role/link_{element_name}">\n',
                "        <link:usedOn>link:definitionLink</link:usedOn>\n",
                "      </link:roleType>\n"
            ]

        html += [
            "    </appinfo>\n",
            "  </annotation>\n"
        ]

        html += [
            "  <!-- typed dimension referenced element -->\n",
            '  <element name="_v" id="_v">\n',
            "    <simpleType>\n",
            '    <restriction base="string"/>\n',
            "    </simpleType>\n",
            "  </element>\n"
        ]

        html.append("  <!-- Hypercube -->\n")
        for element_id in self.roleMap.keys():
            element_name = element_id[3:]
            html.append(
                f'  <element name="h_{element_name}" id="h_{element_name}" substitutionGroup="xbrldt:hypercubeItem" type="xbrli:stringItemType" nillable="true" abstract="true" xbrli:periodType="instant"/>\n'
            )

        html.append("  <!-- Dimension -->\n")
        for element_id in self.roleMap.keys():
            element_name = element_id[3:]
            html.append(
                f'  <element name="d_{element_name}" id="d_{element_name}" substitutionGroup="xbrldt:dimensionItem" type="xbrli:stringItemType" abstract="true" xbrli:periodType="instant" xbrldt:typedDomainRef="#_v"/>\n'
            )

        html.append("  <!-- Primary -->\n")
        for element_id in self.roleMap.keys():
            element_name = element_id[3:]
            html.append(
                f'  <element name="p_{element_name}" id="p_{element_name}" substitutionGroup="xbrli:item" type="xbrli:stringItemType" nillable="true" xbrli:periodType="instant"/>\n'
            )

        html.append(
            "</schema>\n"
        )

        """
        Write xBRL-CSV schema file
        """
        xsd_file = self.file_path(
            f"{xbrl_base}/plt/gl-plt-oim-2025-12-01.xsd"
        )
        with open(xsd_file, "w", encoding=self.encoding, newline="") as f:
            f.writelines(html)
        self.trace_print(f"Write xBRL-CSV schema file {xsd_file}")

        ###################################
        # labelLink en
        #
        for module, data in element_dict.items():
            self.lines = [
                '<?xml version="1.0" encoding="UTF-8"?>\n',
                "<!-- (c) XBRL International.  See http://www.xbrl.org/legal -->\n",
                '<linkbase xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.xbrl.org/2003/linkbase http://www.xbrl.org/2003/xbrl-linkbase-2003-12-31.xsd"\n',
                '    xmlns="http://www.xbrl.org/2003/linkbase"\n',
                '    xmlns:xlink="http://www.w3.org/1999/xlink">\n',
                '    <labelLink xlink:type="extended" xlink:role="http://www.xbrl.org/2003/role/link">\n',
            ]

            for record in data:
                element = record["element"]
                name = record["name"]
                desc = record["definition"].replace('\\n','\n') if "definition" in record else None
                module = element[3:element.index(":")]
                element_name = element[1 + element.index(":"):]
                self.lines += [
                    f"        <!-- {element} {name} -->\n",
                    f'        <loc xlink:type="locator" xlink:href="../gl-{module}-2025-12-01.xsd#gl-{module}_{element_name}" xlink:label="{element_name}"/>\n',
                    f'        <label xlink:type="resource" xlink:label="{element_name}_lbl" xlink:role="http://www.xbrl.org/2003/role/label" xlink:title="gl-{module}_{element_name}_en" xml:lang="en">{name}</label>\n',
                    f'        <label xlink:type="resource" xlink:label="{element_name}_lbl" xlink:role="http://www.xbrl.org/2003/role/documentation" xml:lang="{self.lang}">{desc}</label>\n',
                    f'        <labelArc xlink:type="arc" xlink:arcrole="http://www.xbrl.org/2003/arcrole/concept-label" xlink:from="{element_name}" xlink:to="{element_name}_lbl"/>\n',
                ]

            self.lines.append("  </labelLink>\n")
            self.lines.append("</linkbase>\n")
            """
            Write label linkbase file
            """
            directory = self.file_path(
                f"{xbrl_base}/{module}/lang"
            )
            if not os.path.isdir(directory):
                os.makedirs(directory, exist_ok=True)
                self.trace_print(f"Created label linkbase directory: {directory}")
            label_file = self.file_path(
                f"{xbrl_base}/{module}/lang/gl-{module}-2025-12-01-label.xml"
            )
            with open(label_file, "w", encoding=self.encoding, newline="") as f:
                f.writelines(self.lines)
            self.trace_print(f"-- {label_file}")

        ###################################
        # labelLink lang
        #
        for module, data in element_dict.items():
            self.lines = [
                '<?xml version="1.0" encoding="UTF-8"?>\n',
                "<!-- (c) XBRL International.  See http://www.xbrl.org/legal -->\n",
                '<linkbase xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.xbrl.org/2003/linkbase http://www.xbrl.org/2003/xbrl-linkbase-2003-12-31.xsd"\n',
                '    xmlns="http://www.xbrl.org/2003/linkbase"\n',
                '    xmlns:xlink="http://www.w3.org/1999/xlink">\n',
                '    <labelLink xlink:type="extended" xlink:role="http://www.xbrl.org/2003/role/link">\n',
            ]

            for record in data:
                element = record["element"]
                label_local = record["label_local"]
                definition_local = (
                    record["definition_local"].replace('\\n','\n') if "definition_local" in record else None
                )
                module = element[3:element.index(":")]
                element_name = element[1 + element.index(":"):]
                self.lines += [
                    f"        <!-- {element} {label_local} -->\n",
                    f'        <loc xlink:type="locator" xlink:href="../gl-{module}-2025-12-01.xsd#gl-{module}_{element_name}" xlink:label="{element_name}"/>\n',
                    f'        <label xlink:type="resource" xlink:label="{element_name}_lbl" xlink:role="http://www.xbrl.org/2003/role/label" xlink:title="gl-{module}_{element_name}_{self.lang}" xml:lang="en">{label_local}</label>\n',
                    f'        <label xlink:type="resource" xlink:label="{element_name}_lbl" xlink:role="http://www.xbrl.org/2003/role/documentation" xml:lang="{self.lang}">{definition_local}</label>\n',
                    f'        <labelArc xlink:type="arc" xlink:arcrole="http://www.xbrl.org/2003/arcrole/concept-label" xlink:from="{element_name}" xlink:to="{element_name}_lbl"/>\n',
                ]

            self.lines.append("  </labelLink>\n")
            self.lines.append("</linkbase>\n")
            """
            Write label linkbase file
            """
            label_file = self.file_path(
                f"{xbrl_base}/{module}/lang/gl-{module}-2025-12-01-label-{self.lang}.xml"
            )
            with open(label_file, "w", encoding=self.encoding, newline="") as f:
                f.writelines(self.lines)
            self.trace_print(f"-- {label_file}")

        ###################################
        #   presentationLink
        #
        for module, data in element_dict.items():
            self.locs_defined = {}
            self.arcs_defined = {}
            self.lines = [
                '<?xml version="1.0" encoding="UTF-8"?>\n',
                "<!-- (c) XBRL International.  See http://www.xbrl.org/legal -->\n",
                '<linkbase xmlns="http://www.xbrl.org/2003/linkbase"\n',
                '  xmlns:xlink="http://www.w3.org/1999/xlink"\n',
                '  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.xbrl.org/2003/linkbase http://www.xbrl.org/2003/xbrl-linkbase-2003-12-31.xsd">\n',
                '  <presentationLink xlink:type="extended" xlink:role="http://www.xbrl.org/2003/role/link">\n',
            ]
            class_records = [x for x in data if not x["datatype"]]
            for record in class_records:
                element = record["element"]
                element_id = element.replace(":", "_")
                self.count = 0
                if "children" in record:
                    children = record["children"]
                    self.linkPresentation(module, element_id, children, 1)

            self.lines.append("  </presentationLink>\n")
            self.lines.append("</linkbase>\n")

            """
            Write presentation linkbase file
            """
            presentation_file = self.file_path(
                f"{xbrl_base}/{module}/gl-{module}-2025-12-01-presentation.xml"
            )
            with open(presentation_file, "w", encoding=self.encoding, newline="") as f:
                f.writelines(self.lines)
            self.trace_print(f"-- {presentation_file}")

        ###################################
        # definitionLink
        #
        self.locs_defined = {}
        self.arcs_defined = {}
        self.lines = [
            '<?xml version="1.0" encoding="UTF-8"?>\n',
            "<!-- (c) XBRL International.  See http://www.xbrl.org/legal -->\n",
            "<link:linkbase\n",
            '\txmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n',
            '\txsi:schemaLocation="http://www.xbrl.org/2003/linkbase http://www.xbrl.org/2003/xbrl-linkbase-2003-12-31.xsd"\n',
            '\txmlns:link="http://www.xbrl.org/2003/linkbase"\n',
            '\txmlns:xbrldt="http://xbrl.org/2005/xbrldt"\n',
            '\txmlns:xlink="http://www.w3.org/1999/xlink">\n',
        ]
        self.lines.append("  <!-- roleRef -->\n")
        # 	<link:roleRef roleURI="http://www.xbrl.org/xbrl-gl/role/link_cor_accontingEntries" xlink:type="simple" xlink:href="core.xsd#link_cor_accontingEntries"/>
        for record in self.roleMap.values():
            taxonomy_schema, link_id, href = self.roleRecord(record['element_id'])
            self.lines.append(
                f'  <link:roleRef roleURI="http://www.xbrl.org/xbrl-gl/role/{link_id}" xlink:type="simple" xlink:href="gl-plt-oim-2025-12-01.xsd#{link_id}"/>\n'
            )

        self.lines += [
            "  <!-- arcroleRef -->\n",
            '  <link:arcroleRef arcroleURI="http://xbrl.org/int/dim/arcrole/all" xlink:type="simple" xlink:href="http://www.xbrl.org/2005/xbrldt-2005.xsd#all"/>\n',
            '  <link:arcroleRef arcroleURI="http://xbrl.org/int/dim/arcrole/domain-member" xlink:type="simple" xlink:href="http://www.xbrl.org/2005/xbrldt-2005.xsd#domain-member"/>\n',
            '  <link:arcroleRef arcroleURI="http://xbrl.org/int/dim/arcrole/hypercube-dimension" xlink:type="simple" xlink:href="http://www.xbrl.org/2005/xbrldt-2005.xsd#hypercube-dimension"/>\n',
            '  <link:arcroleRef arcroleURI="http://xbrl.org/int/dim/arcrole/dimension-domain" xlink:type="simple" xlink:href="http://www.xbrl.org/2005/xbrldt-2005.xsd#dimension-domain"/>\n',
        ]

        for cor_id, record in self.roleMap.items():
            # role = roleRecord(record)
            self.count = 0
            self.defineHypercube(record)

        self.lines.append("</link:linkbase>\n")

        cor_definition_file = self.file_path(
            f"{xbrl_base}/plt/gl-plt-def-2025-12-01.xml"
        )
        with open(cor_definition_file, "w", encoding=self.encoding, newline="") as f:
            f.writelines(self.lines)
        self.trace_print(f"-- {cor_definition_file}")

    def json_meta_file(self, taxonomy, xbrl_base=None): # "plt/gl-plt-oim-2025-12-01.xsd"
        if not xbrl_base:
            xbrl_base = self.xbrl_base
        json_meta = {
            "documentInfo": {
                "documentType": "https://xbrl.org/2021/xbrl-csv",
                "namespaces": {
                    "ns0": "http://www.example.com",
                    "link": "http://www.xbrl.org/2003/linkbase",
                    "iso4217": "http://www.xbrl.org/2003/iso4217",
                    "xsi": "http://www.w3.org/2001/XMLSchema-instance",
                    "xbrli": "http://www.xbrl.org/2003/instance",
                    "xbrldi": "http://xbrl.org/2006/xbrldi",
                    "xlink": "http://www.w3.org/1999/xlink",
                    "gl-gen": "http://www.xbrl.org/int/gl/gen/2025-12-01",
                    "gl-cor": "http://www.xbrl.org/int/gl/cor/2025-12-01",
                    "gl-bus": "http://www.xbrl.org/int/gl/bus/2025-12-01",
                    "gl-muc": "http://www.xbrl.org/int/gl/muc/2025-12-01",
                    "gl-usk": "http://www.xbrl.org/int/gl/usk/2025-12-01",
                    "gl-taf": "http://www.xbrl.org/int/gl/taf/2025-12-01",
                    "gl-ehm": "http://www.xbrl.org/int/gl/ehm/2025-12-01",
                    "gl-srcd": "http://www.xbrl.org/int/gl/srcd/2025-12-01",
                    "gl-plt": "http://www.xbrl.org/int/gl/plt/2025-12-01"
                },
                "taxonomy": [
                    taxonomy # "plt/gl-plt-oim-2025-12-01.xsd"
                ]
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

        if self.root:
            dimension_columns = []
            property_columns = []
            root_id = next((x for x in self.dimension_dict.keys() if self.root in x), None)
            root_element_id = next((x for x in self.records if root_id == x["id"]), None)[
                "element_id"
            ]
            root_name = root_element_id[1 + root_element_id.index("-"):]
            dimensions = [
                v["parent_id"]
                for k, v in self.dimension_dict.items()
                if isinstance(v, dict)
                and "multiplicity" in v
                and "*"==v["multiplicity"][-1]
            ]
            properties = [
                x["element_id"]
                for x in self.records
                if x["element_id"] not in dimensions and "A" == x["type"]
            ]

            json_meta["tableTemplates"]["xbrl-gl_template"]["dimensions"][
                f"gl-plt:d_{root_name}"
            ] = f"${root_name}"
            json_meta["tableTemplates"]["xbrl-gl_template"]["columns"][root_name] = {}

            for dimension in dimensions[1:]:
                # dimension_column = dimension[1 + dimension.index("_"):]
                dimension_name = dimension[1 + dimension.index("-"):].replace(":","_")
                dimension_columns.append(dimension_name)
                json_meta["tableTemplates"]["xbrl-gl_template"]["dimensions"][
                    f"gl-plt:d_{dimension_name}"
                ] = f"${dimension_name}"
                json_meta["tableTemplates"]["xbrl-gl_template"]["columns"][
                    dimension_name
                ] = {}

            for property in properties:
                property_column = property[1 + property.index("_"):]
                property_name = property[1 + property.index("-"):]
                property_columns.append(property_name)
                property_module = property[: property.index("_")]
                if property.endswith("Amount"):
                    json_meta["tableTemplates"]["xbrl-gl_template"]["columns"][
                        property_name
                    ] = {
                        "dimensions": {
                            "concept": f"{property_module}:{property_column}",
                            "unit": f"iso4217:{self.currency}",
                        }
                    }
                else:
                    json_meta["tableTemplates"]["xbrl-gl_template"]["columns"][
                        property_name
                    ] = {"dimensions": {"concept": f"{property_module}:{property_column}"}}

            out = "xbrl-gl"
            csv_file = f"{out}_skeleton.csv"
            json_meta["tables"]["xbrl-gl_table"]["url"] = csv_file

            json_meta_file = self.file_path(
                f"{xbrl_base}/{out}.json"
            )
            try:
                with open(json_meta_file, "w", encoding=self.encoding) as file:
                    json.dump(json_meta, file, ensure_ascii=False, indent=4)
                print(f"JSON file '{json_meta_file}' has been created successfully.")
            except Exception as e:
                print(f"An error occurred while creating the JSON file: {e}")
            self.trace_print(f"-- JSON meta file {json_meta_file}")

            out_file = self.file_path(
                f"{xbrl_base}/{csv_file}"
            )
            header_list = [root_name] + dimension_columns + property_columns
            try:
                with open(out_file, "w", encoding=self.encoding, newline="") as file:
                    writer = csv.writer(file)
                    # Write the header and columnname rows
                    writer.writerow(header_list)
                print(f"CSV template file '{out_file}' has been created successfully.")
            except Exception as e:
                print(f"An error occurred while creating the JSON file: {e}")
            self.trace_print(f"-- CSV file with header {csv_file}")

        print("** END **")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("inFile", help="Input HMD structure CSV file")
    parser.add_argument("-b", "--base_dir", help="Base output directory", default=".")
    parser.add_argument("-r", "--root")
    parser.add_argument("-l", "--lang", default="ja")
    parser.add_argument("-c", "--currency", default="JPY")
    parser.add_argument("-n", "--namespace", default="http://www.xbrl.org/xbrl-gl")
    parser.add_argument("-e", "--encoding", default="utf-8-sig")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-d", "--debug", action="store_true")
    args = parser.parse_args()

    generator = xBRLGL_TaxonomyGenerator(
        in_file=args.inFile,
        base_dir=args.base_dir,
        root=args.root,
        lang=args.lang,
        currency=args.currency,
        namespace=args.namespace,
        encoding=args.encoding,
        trace=args.verbose,
        debug=args.debug
    )

    generator.load_csv_data()
    generator.process_records()
    generator.generate_taxonomy_files(generator.xbrl_base)
    generator.json_meta_file("plt/gl-plt-oim-2025-12-01.xsd", generator.xbrl_base)

if __name__ == "__main__":
    main()