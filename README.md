## Requirements

This project operates on a local clone of the
[cards-database](https://github.com/ORG/cards-database) repository.

You must clone it separately.

## Setup

```bash
git clone https://github.com/you/tcgdex-database-helper.git
git clone https://github.com/ORG/cards-database.git

cd tcgdex-database-helper
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export CARDS_DATABASE_PATH=../cards-database
python -m tcgdex_database_helper
