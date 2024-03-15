from fred import Fred


if __name__ == "__main__":
    fred = Fred(log_level="info", human_name="Utkash", dry_run=True)
    fred.start()
