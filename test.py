from fred import Fred


if __name__ == "__main__":
    fred = Fred(
        log_level="warn",
        human_name="Utkash",
        dry_run=False,
        verify_home_assistant_ssl=False,
    )
    fred.start()
