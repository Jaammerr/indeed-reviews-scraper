import csv

from loguru import logger


class SaveToCSV:
    def __init__(self, processed_reviews: list[dict]):
        self.processed_reviews = processed_reviews

    def save(self):
        try:
            with open(f"reviews.csv", "w", encoding="utf-8", newline='') as file:
                writer = csv.DictWriter(file, fieldnames=self.processed_reviews[0].keys())
                writer.writeheader()
                writer.writerows(self.processed_reviews)

        except Exception as error:
            logger.error(f"Failed to save to CSV: {error}")
