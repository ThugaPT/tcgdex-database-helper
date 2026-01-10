def main():
    from tcgdex_database_helper.config import load_config
    from tcgdex_database_helper.count_cards_by_illustrator import (
    configure_count_cards_by_illustrator,
    run_count_cards_by_illustrator,
    )
    from tcgdex_database_helper.tcgDex_database_helper_GUI import (
    configure_tcgDex_database_helper_GUI,
    run_tcgDex_database_helper_GUI,
    )
    #LOAD AND SET CONFIGS
    config = load_config()
    paths = config["paths"]
    runtime_settings = config["runtime_settings"]
    print(config)
    configure_count_cards_by_illustrator(
        database_root_en=paths["database_root_en"],
        database_root_ja=paths["database_root_ja"],
        illustrator_csv=paths["illustrator_csv"],
    )
    language = "EN" #To be fetched from a helper GUI on startup

    configure_tcgDex_database_helper_GUI(
        database_root_en=paths["database_root_en"],
        database_root_ja=paths["database_root_ja"],
        illustrator_csv=paths["illustrator_csv"],
        max_retries=runtime_settings["max_retries"],
        autocomplete_min_chars=runtime_settings["autocomplete_min_chars"],
        language=language,
    )
    run_count_cards_by_illustrator()
    run_tcgDex_database_helper_GUI()
