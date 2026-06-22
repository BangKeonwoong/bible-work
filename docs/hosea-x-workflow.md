# Hosea capital-X analysis workflow

The GitHub Actions workflow in `.github/workflows/hosea-x-fronting.yml` runs the reproducible Text-Fabric analysis supplied by a pull request that changes `scripts/analyze_hosea_x_fronting.py`.

It installs this repository, loads ETCBC/BHSA 2021 through Text-Fabric, and uploads CSV, JSON, and Markdown outputs as the `hosea-capital-x-analysis` artifact.
