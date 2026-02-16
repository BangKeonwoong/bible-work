# bhs-hierarchy

BHSA `clause_atom` mother-daughter hierarchy tooling.

Current implementation covers Stage A (core extraction + root selection + visualization)
and includes an agreement checker for `mother`-depth vs BHSA `tab`.

## Install

1. Install Graphviz system binaries so `dot` is available on `PATH`.
2. Install this project:

```bash
pip install -e .
```

On first run, Text-Fabric will download BHSA data to local cache.

## CLI

Show root candidates in a scope:

```bash
bhs-hier roots --book Genesis --chapter 1 --verse-from 1 --verse-to 5
```

Render selected root subtree (`root-index` is from `roots` output):

```bash
bhs-hier draw --book Genesis --chapter 1 --verse-from 1 --verse-to 5 --root-index 0 --out out/gen_1_1-5.svg
```

Scope options:

- `--book` required
- `--chapter` optional (omit for whole book)
- `--verse-from`, `--verse-to` optional (when `--chapter` is set)
- `--version` BHSA dataset version (default `2021`)

## Validation Script

Compare computed depth (from `mother`) vs BHSA `tab`:

```bash
python scripts/check_tab_agreement.py --book Genesis --chapter 1 --verse-from 1 --verse-to 5
```

## GUI

Launch the Tkinter GUI:

```bash
bhs-hier-gui
```

Or run from this repo without installing entry points:

```bash
./run_gui.sh
```

On Windows:

```bat
run_gui.bat
```

GUI fields:

- `version`
- `book`
- `chapter` (optional)
- `verse_from` / `verse_to` (optional)
- output `format` (`svg`, `png`, `pdf`, `dot`)
- output path

Use `Load roots` to populate candidates, select one root in the list, then click
`Render selected root`.

Notes:

- GUI requires Python `tkinter` (Linux often needs `python3-tk` package).
- If Graphviz `dot` is not installed, choose `dot` output format to still export a graph source file.
