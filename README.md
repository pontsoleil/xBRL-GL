# Dimensional XBRL-GL and Structured CSV Project

This project modernizes **XBRL Global Ledger (XBRL GL)** by enabling it to be expressed using **xBRL-CSV** format. Through the use of a **dimensional definition linkbase**, this approach allows any XBRL GL XML instance to be represented as a single structured CSV file.

## 🔧 Key Features

- Converts **PWD 2016 XBRL GL** definitions into a semantic model.
- Generates both **palette schema taxonomy** and **OIM dimensional taxonomy** (hypercube-based).
- Transforms **XML instance documents** into structured **xBRL-CSV**.
- Supports two authoring paths:
  - **Palette-based reverse modeling**
  - **Semantic model-driven generation** via FSM → BSM → LHM

## 📁 Repository Contents

```
├── README.md
├── LICENSE
├── docs/
│   ├── user-guide.adoc            # Full guide (generated from the canvas)
│   ├── images/                    # Diagrams or UML exports
│   └── examples/                  # Mini walkthroughs or sample runs
├── scripts/                       # Core Python scripts
│   ├── specialization.py
│   ├── graphwalk.py
│   ├── xBRLGL_ParseTaxonomy.py
│   ├── xBRLGL_TaxonomyGenerator.py
│   └── xBRLGL_StructuredCSV.py
├── launch.json                    # VS Code config
├── taxonomy/
│   ├── FSM/
│   ├── BSM/
│   ├── LHM/
│   ├── gl/                        # XBRL schema files
│   └── OIM/                       # Output xBRL-CSV and JSON
├── ids/                           # Sample instance documents
├── output/                        # Generated taxonomy and CSVs
├── metadata/                      # JSON metadata, labels, etc.
└── tests/                         # (Optional) Pytest-compatible test cases
```

## 📜 Licensing

- **Scripts:** MIT License  
- **Documentation & Artifacts:** Creative Commons Attribution 4.0 (CC BY 4.0)

## 📚 User Guide

See [docs/user-guide.adoc](docs/user-guide.adoc) for a full walkthrough, including Mermaid flowcharts, CLI examples, and script documentation.

## 🚀 Quick Start

Open the project in VS Code and run the included launch configurations via `launch.json`.  
Use sample instance files in the `ids/` directory and start generating structured xBRL-CSV output.
