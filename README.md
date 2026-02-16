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
