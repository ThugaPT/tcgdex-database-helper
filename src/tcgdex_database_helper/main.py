def main():
    from tcgdex_database_helper.config import load_config
    from tcgdex_database_helper.count_cards_by_illustrator import (
    configure_count_cards_by_illustrator,
    run_count_cards_by_illustrator,
)
    config = load_config()
    paths = config["paths"]
    print(config)
    configure_count_cards_by_illustrator(
        database_root_en=paths["database_root_en"],
        database_root_ja=paths["database_root_ja"],
        output_csv=paths["output_csv"],
    )
    run_count_cards_by_illustrator()
