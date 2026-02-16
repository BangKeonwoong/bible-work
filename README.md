# bhs-hierarchy

BHSA `clause_atom` mother-daughter hierarchy tooling.

Current implementation includes:

- Stage A: scope selection, root listing, graph render
- PR#2: root normalization (`self-mother`, `code=0/dist=0`) and `check-tab`
- PR#3: decisions file (`yaml/json`), mother overrides, CTT-like export

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

Validate `mother` depth against BHSA `tab`:

```bash
bhs-hier check-tab --book Genesis --chapter 1 --verse-from 1 --verse-to 5
```

Create decisions file:

```bash
bhs-hier init-decisions --book Genesis --chapter 1 --verse-from 1 --verse-to 5 --out decisions/gen_1_1-5.yaml --root-index 0
```

Export CTT-like output using decisions (subtree only from selected roots):

```bash
bhs-hier ctt --book Genesis --chapter 1 --verse-from 1 --verse-to 5 --decisions decisions/gen_1_1-5.yaml --subtree --out out/gen_1_1-5.ctt.txt
```

Render graph with decisions overrides:

```bash
bhs-hier draw --book Genesis --chapter 1 --verse-from 1 --verse-to 5 --decisions decisions/gen_1_1-5.yaml --out out/gen_1_1-5.dot --fmt dot
```

Scope options:

- `--book` required unless `--decisions` is used
- `--chapter` optional (omit for whole book)
- `--verse-from`, `--verse-to` optional (when `--chapter` is set)
- `--decisions` optional for `draw`/`ctt` (uses decisions `scope`, `roots`, `overrides`)
- `--version` BHSA dataset version (default `2021`)

## Validation Script

Legacy wrapper for `check-tab`:

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
