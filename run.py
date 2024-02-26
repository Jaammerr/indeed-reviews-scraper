import os
import threading
import yaml

from src.main_v2 import Scraper
from src.utils import SaveToCSV
from loguru import logger


def verify_config() -> dict:
    if os.path.exists("config.yaml"):
        with open("config.yaml", "r") as file:
            config = yaml.safe_load(file)

            if not config.get("proxy") or "@" not in config["proxy"]:
                raise ValueError("Proxy not found in config.yaml or had invalid format | Format: username:password@ip:port")

            if not config.get("urls"):
                raise ValueError("No urls found in config.yaml")

            if not all(url.split('/')[-1] == "reviews" for url in config["urls"]):
                raise ValueError("All urls in config.yaml must end with '/reviews'")

            if not config.get("threads"):
                raise ValueError("No threads found in config.yaml")

            if not isinstance(config["threads"], int):
                raise ValueError("Threads in config.yaml must be an integer")

            return config

    else:
        raise FileNotFoundError("config.yaml not found")


def run():
    config = verify_config()
    sem = threading.Semaphore(config["threads"])
    logger.info(f"Scraper started | Loaded {len(config['urls'])} urls | Threads: {config['threads']}\n")

    total_reviews = []
    for url in config["urls"]:
        reviews = Scraper(url, config['proxy'], sem).start()
        if reviews:
            total_reviews.extend(reviews)

    if total_reviews:
        logger.success(f"Fetched {len(total_reviews)} reviews in total | Saving to CSV..")
        SaveToCSV(total_reviews).save()
        logger.success(f"Saved to CSV")



if __name__ == "__main__":
    run()
