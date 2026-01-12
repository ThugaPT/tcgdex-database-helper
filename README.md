```markdown
# tcgdex-database-helper
Helper tool to process and update the TCGdex cards database
```
## Requirements

- Python 3.10 or newer
- A local clone of the `cards-database` repository (see below)
## Setup

```bash
#create your workspace folder
mkdir workspace
cd workspace
##Clone the project, or download it from GIT to the workspace folder
##git clone https://github.com/ThugaPT/tcgdex-database-helper.git
##Follow the steps to contribute to https://github.com/tcgdex/cards-database.git
##Clone your fork of the cards-database to the root of the workspace folder
##git clone https://github.com/[you]/cards-database.git


cd tcgdex-database-helper
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .

```
## Configuration
Copy the default config and adjust local paths if needed:
```bash
cp config/config.yaml config/config.local.yaml
```
```yaml
paths:
  cards_database: /path/to/cards-database
  database_root_en: /path/to/cards-database/data
  database_root_ja: /path/to/cards-database/data-asia
  output_csv: /path/to/output/file.csv
```
## Usage
```bash

python -m tcgdex_database_helper [-h] [-l LANGUAGE] [-nsl]

#options:
#  -h, --help            show help message and exit
#  -l, --lang LANGUAGE   Language code to use (en or ja), if not set, uses en by default
#  -nsl, --no_ssl_verify
#                        Disable SSL verification - NOT RECOMMENDED, but for some networks it's required

```
## Result
The changes produced by the helper are on the files in your local clone of the cards-database fork, to have them in your repository(and after done, in the main repository via a pull request) don't forget to commit and push.