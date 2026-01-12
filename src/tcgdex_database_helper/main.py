

def main():
    import asyncio
    import argparse
    from tcgdex_database_helper.config import (
        load_config,
        set_language,
        set_no_ssl_verify,
    )
    from tcgdex_database_helper.count_cards_by_illustrator import (
    configure_count_cards_by_illustrator,
    run_count_cards_by_illustrator,
    )
    from tcgdex_database_helper.tcgDex_database_helper_GUI import (
    configure_tcgDex_database_helper_GUI,
    run_tcgDex_database_helper_GUI_async,
    )
    def parse_args():
        parser = argparse.ArgumentParser(
            description="TCGDex Database Helper GUI"
        )

        parser.add_argument(
            "-l", "--lang",
            dest="language",
            default=None,
            help="Language code to use (en or ja), if not set, uses en by default",
        )
        parser.add_argument(
            "-nsl", "--no_ssl_verify",
            action="store_true",
            help="Disable SSL verification",
        )

        return parser.parse_args()
    
    
    args = parse_args()
    if args.language:
        if args.language in ["en", "ja"]:
            set_language(args.language)
            if args.language == "ja":
                print("Japanese Language not yet supported")
                return
        else:
            print("No valid language specified, please use --lang or -l with 'en' or 'ja'")
            return
    
    if args.no_ssl_verify:
        set_no_ssl_verify(True)

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
    configure_tcgDex_database_helper_GUI(
        database_root_en=paths["database_root_en"],
        database_root_ja=paths["database_root_ja"],
        illustrator_csv=paths["illustrator_csv"],
        max_retries=runtime_settings["max_retries"],
        autocomplete_min_chars=runtime_settings["autocomplete_min_chars"],
    )
    run_count_cards_by_illustrator()
    asyncio.run(run_tcgDex_database_helper_GUI_async())