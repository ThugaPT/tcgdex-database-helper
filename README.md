## Requirements

This project operates on a local clone of the
[cards-database](https://github.com/ORG/cards-database) repository.

You must clone it separately.

## Setup

```bash
#create your workspace folder
mkdir workspace
##Clone the project, or download it from GIT
##git clone https://github.com/ThugaPT/tcgdex-database-helper.git
##Follow the steps to contribute to https://github.com/tcgdex/cards-database.git
##Clone your fork 
##git clone https://github.com/[you]/cards-database.git


cd tcgdex-database-helper
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .

#export CARDS_DATABASE_PATH=../cards-database
python -m tcgdex_database_helper
