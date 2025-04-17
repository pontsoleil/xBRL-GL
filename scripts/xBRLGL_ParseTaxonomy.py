#!/usr/bin/env python3
# coding: utf-8
"""
xBRLGL_ParseTaxonomy.py

This script parses the XBRL Global Ledger (XBRL GL) palette taxonomy and 
generates a CSV file that represents the labeled hierarchical structure 
defined by complexType definitions.

Designed by SAMBUICHI, Nobuyuki (Sambuichi Professional Engineers Office)
Written by SAMBUICHI, Nobuyuki (Sambuichi Professional Engineers Office)

Creation Date: 2025-04-02
Last Modified: 2025-04-12

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

Usage:
    python xbrl_gl_label_parser.py --base-dir <taxonomy-root-directory> [--palette <palette-subdir>] [--lang <language-code>] [--debug] [--trace] [--output <filename>]

Arguments:
    --base-dir     Required. Path to the root of the XBRL GL taxonomy (e.g., XBRL-GL-PWD-2016-12-01).
    --palette      Optional. Subdirectory name of the palette folder (default: case-c-b-m-u-e-t-s).
    --output       Optional. Filename for the output CSV (default: XBRL_GL_Parsed_LHM_Structure.csv).
    --lang         Optional. Language code for multilingual labels. Default is 'ja'.
    --debug        Optional. Enables detailed debug output.
    --trace        Optional. Enables trace messages.

Example:
    python xbrl_gl_label_parser.py --base-dir XBRL-GL-PWD-2016-12-01 --palette case-c-b --output my_labels.csv --lang ja --debug
"""

import lxml.etree as ET
import os
import sys
import re
import csv
import argparse
from collections import defaultdict

class xBRLGL_ParseTaxonomy:
    def __init__(
            self,
            base_dir,
            palette,
            output,
            lang,
            trace,
            debug
        ):
        if base_dir:
            self.base_dir = self.file_path(base_dir.strip())
        else:
            print(f"Taxonomy base directory {self.base_dir} is missing.")
            sys.exit()
        if not os.path.isdir(self.base_dir):
            print(f"Taxonomy base directory {self.base_dir} does not exist.")
            sys.exit()
        self.output_file = self.file_path(output.strip())
        self.output_dir = os.path.dirname(self.output_file)
        if self.output_dir and not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir, exist_ok=True)
            self.trace_print(f"Created output directory: {self.output_dir}")
        self.lang = lang.strip() if lang else "ja"
        self.palette = palette
        self.TRACE = trace or False
        self.DEBUG = debug or False

        self.xsd_path = os.path.join(base_dir, f"gl/plt/{self.palette}/gl-cor-content-2016-12-01.xsd")
        self.namespaces = {
            'xs': "http://www.w3.org/2001/XMLSchema",
            'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
            'xbrli': "http://www.xbrl.org/2003/instance",
            'xlink': 'http://www.w3.org/1999/xlink',
            'link': "http://www.xbrl.org/2003/linkbase",
            'gl-cor': 'http://www.xbrl.org/int/gl/cor/2016-12-01',
            'gl-muc': 'http://www.xbrl.org/int/gl/muc/2016-12-01',
            'gl-bus': 'http://www.xbrl.org/int/gl/bus/2016-12-01',
            'gl-usk': 'http://www.xbrl.org/int/gl/usk/2016-12-01',
            'gl-ehm': 'http://www.xbrl.org/int/gl/ehm/2016-12-01',
            'gl-taf': 'http://www.xbrl.org/int/gl/taf/2016-12-01',
            'gl-plt': 'http://www.xbrl.org/int/gl/plt/2016-12-01'
        }

        self.modules = ['gen', 'cor', 'bus', 'muc', 'usk', 'ehm', 'taf', 'srcd']
        # Load base schemas and build type maps
        self.element_type_map = {}
        self.type_base_map = {}
        self.type_base_lookup = {}
        self.complex_type_lookup = {}

    def debug_print(self, text):
        if self.DEBUG:
            print(text)

    def trace_print(self, text):
        if self.TRACE:
            print(text)

    def file_path(self, pathname):
        _pathname = pathname.replace("/", os.sep)
        if os.sep == _pathname[0:1]:
            return _pathname
        else:
            dir = os.path.dirname(__file__)
            return os.path.join(dir, _pathname)

    # Helper to clean label IDs
    def clean_label_id(self, label_id):
        label_id = re.sub(r"^label_", "", label_id)
        label_id = re.sub(r"(_lbl|_\d+(_\d+)?)$", "", label_id)
        return label_id

    # Load label linkbases (EN and JA)
    def load_labels(self, mod, lang):
        label_map = defaultdict(dict)
        suffix = "label.xml" if lang == "en" else f"label-{lang}.xml"
        path = os.path.join(self.base_dir, f"gl/{mod}/lang/gl-{mod}-2016-12-01-{suffix}")
        if not os.path.exists(path):
            return label_map
        tree = ET.parse(path)
        root = tree.getroot()
        locator_map = {}
        label_resources = {}
        # Map locator label -> href target
        for loc in root.xpath(".//link:loc", namespaces=self.namespaces):
            label_id = loc.get("{http://www.w3.org/1999/xlink}label")
            href = loc.get("{http://www.w3.org/1999/xlink}href")
            _, anchor = href.split("#")
            if label_id and href and '#' in href:
                locator_map[label_id] = anchor
        # Collect label resources
        for label in root.xpath(".//link:label", namespaces=self.namespaces):
            label_id = label.get("{http://www.w3.org/1999/xlink}label")
            role = label.get("{http://www.w3.org/1999/xlink}role")
            label_text = label.text.strip() if label.text else ""
            if label_id not in label_resources:
                label_resources[label_id] = {}
            if role.endswith("label"):
                label_resources[label_id]["label"] = label_text
            elif role.endswith("documentation"):
                label_resources[label_id]["documentation"] = label_text
        # Resolve labelArcs and map labels to href anchors
        for arc in root.xpath(".//link:labelArc", namespaces=self.namespaces):
            from_label = arc.get("{http://www.w3.org/1999/xlink}from")
            to_label = arc.get("{http://www.w3.org/1999/xlink}to")
            href = locator_map.get(from_label)
            label = label_resources.get(to_label)
            if href and label is not None:
                role = label.get("{http://www.w3.org/1999/xlink}role")
                if lang == "en":
                    if "label" in label:
                        label_map[href]["label"] = label["label"]
                    if "documentation" in label:
                        label_map[href]["documentation"] = label["documentation"]
                elif lang != "en":
                    if "label" in label:
                        label_map[href][f"label_{lang}"] = label["label"]
                    if "documentation" in label:
                        label_map[href][f"documentation_{lang}"] = label["documentation"]
        return label_map

    # Helpers
    def is_tuple_type(self, complex_type_element):
        if complex_type_element is None:
            return False
        if complex_type_element.find("xs:simpleContent", self.namespaces) is not None:
            return False
        complex_content = complex_type_element.find("xs:complexContent", self.namespaces)
        if complex_content is not None:
            for tag in ["xs:restriction", "xs:extension"]:
                inner = complex_content.find(tag, self.namespaces)
                if inner is not None:
                    base = inner.get("base")
                    return base == "anyType"
        sequence_content = complex_type_element.find("xs:sequence", self.namespaces)
        if sequence_content is not None:
            return True
        choice_content = complex_type_element.find("xs:choice", self.namespaces)
        if choice_content is not None:
            return True
        return False

    def resolve_base_type(self, type_str):
        type_name = type_str.split(":")[-1]
        return self.type_base_lookup.get(type_name, "")

    def abbreviate_term(self, term):
        """
        Abbreviates each word in the input term according to the following rules:

        - Remove common stop_words (e.g., to, with, on, of, etc.).
        - Remove any symbol characters: !"#$%&'()=~|\^-@`[]{}:;+*/?.,<>\_
        - Capitalize the first letter of each remaining word.
        - Keep the first vowel of each word, remove all other vowels.
        - If the abbreviation is 6 characters or more:
            - Keep only the first vowel and remove the rest.
            - If the first character is a vowel and the result is still long,
            remove the 5th character (index 4) to shorten further.
        - Ensure the abbreviated word is shorter than the original word.
        - Words of length 3 or less are returned unchanged.
        """
        def abbreviate_word(word):
            if len(word) <= 3:
                return word  # already short
            chars = [word[0]]  # keep first character
            # include non-vowels from rest, skipping first vowel if it's the first char
            first_vowel_found = word[0] in vowels
            for c in word[1:]:
                if c.lower() not in vowels:
                    chars.append(c)
                elif not first_vowel_found:
                    chars.append(c)
                    first_vowel_found = True
            abbr = ''.join(chars)
            # If abbreviation is still too long, remove all vowels
            if len(abbr) >= 6:
                # Keep the first vowel
                first_vowel_index = next(
                    (i for i, c in enumerate(abbr) if c.lower() in vowels), None
                )
                if first_vowel_index is not None:
                    first_vowel = abbr[first_vowel_index]
                    abbr_chars = [
                        abbr[i]
                        for i in range(len(abbr))
                        if abbr[i].lower() not in vowels or i == first_vowel_index
                    ]
                    abbr = "".join(abbr_chars)
                    # If the first character is a vowel and the abbreviation is still long,
                    # trim to the first 5 characters and append the last character to shorten
                    # while preserving the start and end of the word
                    if abbr and abbr[0].lower() in vowels and len(abbr) > 5:
                        abbr = abbr[:5] + abbr[-1]
            # Final fallback: truncate if still too long
            return abbr if len(abbr) < len(word) else word # must be shorter

        stop_words = {
            'a', 'an', 'the',
            'to', 'with', 'on', 'of', 'in', 'for', 'at', 'by', 'from', 'as',
            'about', 'into', 'over', 'after', 'under', 'above', 'below'
        }
        vowels = 'aeiouAEIOU'
        # Remove symbols
        term = re.sub(r'[!"#$%&\'()=~|\\^\-@`\[\]{}:;+*/?,.<>\_]', '', term)
        # Remove (choice)
        if '(choice)' in term:
            term = term.replace("(choice)", "").strip()
        # Tokenize and filter stop_words
        words = re.findall(r'\w+', term)
        filtered = [w.capitalize() for w in words if w.lower() not in stop_words]
        # Abbreviate remaining words
        abbreviated = [abbreviate_word(w) for w in filtered]
        return ' '.join(abbreviated)

    def process_element(self, el, xpath, option=''):
        self.idx = 1 + self.idx
        ref = el.get("ref")
        name = el.get("name")
        el_name = ref or name
        if not el_name:
            return
        el_type = self.element_type_map.get(el_name, "")
        type_name = el_type.split(":")[-1]
        complex_type = self.complex_type_lookup.get(type_name)
        is_tuple = False
        if complex_type is not None:
            is_tuple = self.is_tuple_type(complex_type)
        path_str = xpath
        new_path = f"{path_str}/{el_name}"
        min_occurs = el.get("minOccurs", "1")
        max_occurs = el.get("maxOccurs", "1")
        base_type = self.resolve_base_type(el_type) if not is_tuple and el_type else ""
        level = new_path.count("/") - 1
        raw_key = el_name.replace(":", "_")
        label_info = self.label_texts.get(raw_key, {})
        name = label_info.get("label", "")
        _type = "C" if is_tuple else "A"
        multiplicity = f"{min_occurs}..{'*' if 'unbounded'==max_occurs else max_occurs}"
        self.parents[level] = name
        if 'choice-sequence'==option:
            name += ' (sequence)'
        elif 'sequence-choice'==option:
            name += ' (choice)'
        # Clear higher levels
        for i in range(level + 1, len(self.parents)):
            self.parents[i] = ""
        semantic_path = f"${'.'.join(self.parents[:1+level])}"
        if option in ['choice', 'choice-sequence'] and " (choice)" in semantic_path:
            semantic_path = semantic_path.replace(" (choice)", "")
        abbreviated_path = (
            ".".join([self.abbreviate_term(p) for p in self.parents[1 : 1 + level]])
            .replace(" ", "")
            .replace(".", "_")
        )
        if option in ['choice', 'choice-sequence'] and "Choc" in abbreviated_path:
            abbreviated_path = abbreviated_path.replace("Choc", "")
        record = {
            "sequence": self.idx,
            "level": level,
            "type": _type,
            "identifier": "",
            "name": name,
            "datatype": base_type,
            "multiplicity": multiplicity,
            "domain_name": "",
            "definition": label_info.get("documentation", ""),
            "module": el_name[: el_name.index(":")],
            "table": "",
            "class_term": (
                self.parents[level] if "C" == _type else self.parents[level - 1]
            ),
            "id": "",
            "path": "",
            "semantic_path": semantic_path,
            "abbreviation_path": abbreviated_path,
            "label_local": label_info.get("label_ja", ""),
            "definition_local": label_info.get("documentation_ja", ""),
            "element": el_name,
            "xpath": new_path,
        }
        self.records.append(record)
        if not el_type:
            return
        type_name = el_type.split(":")[-1]
        if is_tuple:
            mod = el_type.split(":")[0][3:]
            for _path in [
                os.path.join(self.base_dir, f"gl/{mod}/gl-{mod}-2016-12-01.xsd"),
                os.path.join(
                    self.base_dir,
                    f"gl/plt/{self.palette}/gl-{mod}-content-2016-12-01.xsd",
                ),
            ]:
                if os.path.exists(_path):
                    tree = ET.parse(_path)
                    nested = tree.xpath(
                        f".//xs:complexType[@name='{type_name}']",
                        namespaces=self.namespaces,
                    )
                    if nested:
                        self.walk_complex_type(
                            type_name, nested[0], "tuple", mod, new_path
                        )
                        return

    def process_sequence(self, sequence, _type, module, xpath, base):
        self.debug_print(f" - Processing xs:sequence in xpath: {xpath}")
        for el in sequence.findall("xs:element", namespaces=self.namespaces):
            self.process_element(el, xpath)
        for choice in sequence.findall("xs:choice", namespaces=self.namespaces):
            for el in choice.findall("xs:element", namespaces=self.namespaces):
                self.process_element(el, xpath, 'sequence-choice')

    def process_choice(self, choice, _type, module, xpath, base):
        self.debug_print(f" - Processing xs:choice in xpath: {xpath}")
        for el in choice.findall("xs:element", namespaces=self.namespaces):
            self.process_element(el, xpath, 'choice')           
        for sq in choice.findall("xs:sequence", namespaces=self.namespaces):
            for el in sq.findall("xs:element", namespaces=self.namespaces):
                self.process_element(el, xpath, 'choice-sequence') 

    def walk_complex_type(self, name, element, _type, module, xpath):
        self.trace_print(f"Walking: '{name}' at xpath: {xpath}")
        sequence = element.find("xs:sequence", self.namespaces)
        if sequence is not None:
            self.process_sequence(sequence, _type, module, xpath, name)
            return
        choice = element.find("xs:choice", self.namespaces)
        if choice is not None:
            self.records[-1]['name'] += ' (choice)'
            self.records[-1]['class_term'] += ' (choice)'
            self.parents[self.records[-1]['level']] += ' (choice)'
            self.process_choice(choice, _type, module, xpath, name)
            return
        complex_content = element.find("xs:complexContent", self.namespaces)
        if complex_content is not None:
            for tag in ["xs:restriction", "xs:extension"]:
                inner = complex_content.find(tag, self.namespaces)
                if inner is not None:
                    base = inner.get("base")
                    sequence = inner.find("xs:sequence", self.namespaces)
                    if sequence is not None:
                        self.process_sequence(sequence, _type, module, xpath, base)
                    return

    def parse(self):
        for mod in self.modules:
            path = os.path.join(self.base_dir, f"gl/{mod}/gl-{mod}-2016-12-01.xsd")
            if os.path.exists(path):
                tree = ET.parse(path)
                root = tree.getroot()
                for el in root.xpath("//xs:element", namespaces=self.namespaces):
                    name, type_ = el.get("name"), el.get("type")
                    if name and type_:
                        # self.debug_print(f"gl-{mod}:{name}")
                        self.element_type_map[f"gl-{mod}:{name}"] = type_
                for tdef in root.xpath("//xs:simpleType | //xs:complexType", namespaces=self.namespaces):
                    name = tdef.get("name")
                    if name:
                        # self.debug_print(name)
                        self.complex_type_lookup[name] = tdef
                        restriction = tdef.find(".//xs:restriction", self.namespaces)
                        if restriction is not None:
                            base = restriction.get("base")
                            if base:
                                self.type_base_map[name] = base
                                self.type_base_lookup[name] = base
                        extension = tdef.find(".//xs:extension", self.namespaces)
                        if extension is not None:
                            base = extension.get("base")
                            if base:
                                self.type_base_map[name] = base
                                self.type_base_lookup[name] = base

        # Load content schemas
        self.content_roots = {}
        for mod in self.modules:
            path = os.path.join(self.base_dir, f"gl/plt/{self.palette}/gl-{mod}-content-2016-12-01.xsd")
            if os.path.exists(path):
                self.content_roots[mod] = ET.parse(path).getroot()
                tree = ET.parse(path)
                root = tree.getroot()
                for el in root.xpath("//xs:element", namespaces=self.namespaces):
                    name, type_ = el.get("name"), el.get("type")
                    if name and type_:
                        # self.debug_print(f"gl-{mod}:{name}")
                        self.element_type_map[f"gl-{mod}:{name}"] = type_
                for tdef in root.xpath("//xs:simpleType | //xs:complexType", namespaces=self.namespaces):
                    name = tdef.get("name")
                    if name:
                        # self.debug_print(name)
                        self.complex_type_lookup[name] = tdef
                        restriction = tdef.find(".//xs:restriction", self.namespaces)
                        if restriction is not None:
                            base = restriction.get("base")
                            if base:
                                self.type_base_map[name] = base
                                self.type_base_lookup[name] = base
                        extension = tdef.find(".//xs:extension", self.namespaces)
                        if extension is not None:
                            base = extension.get("base")
                            if base:
                                self.type_base_map[name] = base
                                self.type_base_lookup[name] = base

        self.label_texts = defaultdict(dict)
        for mod in self.modules:
            labels = [self.load_labels(mod, "en")]
            if self.lang != "en":
                labels.append(self.load_labels(mod, self.lang))
            for label_map in labels:
                for k, v in label_map.items():
                    self.label_texts[k].update(v)

        # Traversal
        self.records = []
        self.idx = 0
        self.parents = ['']*10
        # Start with root complexType
        self.root = self.content_roots["cor"]
        self.complex_type_list = self.root.xpath(".//xs:complexType[@name='accountingEntriesComplexType']", namespaces=self.namespaces)
        if self.complex_type_list:
            href = "gl-cor_accountingEntries"
            label = self.label_texts[href].get("label", "")
            self.parents[1] = label
            record = {
                "sequence": 1,
                "level": 1,
                "type": "C",
                "identifier": "",
                "name": label,
                "datatype": "",
                "multiplicity": "1..*",
                "domain_name": "",
                "definition": self.label_texts[href].get("documentation", ""),
                "module": "gl-cor",
                "table": "",
                "class_term": "xBRL",
                "id": "",
                "path": "",
                "semantic_path": "$.Accounting Entries",
                "abbreviation_path": "AccntgEntrs",
                "label_local": self.label_texts[href].get("label_ja", ""),
                "definition_local": self.label_texts[href].get("documentation_ja", ""),
                "element": "gl-cor:accountingEntries",
                "xpath": f"/xbrli:xbrl/gl-cor:accountingEntries",
            }
            self.records.append(record)
            self.walk_complex_type("accountingEntriesComplexType", self.complex_type_list[0], "tuple", "cor", "/xbrli:xbrl/gl-cor:accountingEntries")
        else:
            print("❌ Not found: accountingEntriesComplexType")

        # Output to CSV
        with open(self.output_file, mode='w', newline='', encoding='utf-8-sig') as f:
            if self.records:
                header = self.records[0].keys()
                writer = csv.DictWriter(f, fieldnames=header)
                writer.writeheader()
                writer.writerows(self.records)
            else:
                print("⚠️ No records to write.")

        print(f"\n✅ Saved parsed structure to: {self.output_file}")


def main():
    parser = argparse.ArgumentParser(description="Parse XBRL-GL schemas and extract labeled hierarchy.")
    # Argument parser for base directory
    parser.add_argument("-b", "--base_dir", type=str, required=True, default=".", help="Base directory path to XBRL GLtaxonomy, e.g. XBRL-GL-PWD-2016-12-01")
    parser.add_argument("-p", "--palette", type=str, default="case-c-b-m-u-e-t-s", help="Palette subdirectory under gl/plt/ (e.g. case-c-b or case-c-b-m-u-e-t-s)")
    parser.add_argument("-o", "--output", type=str, default="XBRL_GL_case-c-b-m-u-e-t_Structure.csv", help="Output CSV filename")
    parser.add_argument("-l", "--lang", type=str, default="ja", help="Language code for local labels (e.g. 'ja', 'en')")
    parser.add_argument("-v", "--trace", action="store_true", help="Enable trace output")
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug output")

    args = parser.parse_args()

    generator = xBRLGL_ParseTaxonomy(
        base_dir=args.base_dir,
        palette=args.palette,
        output=args.output,
        lang=args.lang,
        trace=args.trace,
        debug=args.debug
    )

    generator.parse()

if __name__ == "__main__":
    main()
