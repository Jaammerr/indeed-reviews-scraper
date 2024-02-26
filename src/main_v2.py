import json
import random
import threading
import time
import pyuseragents
import tls_client

from loguru import logger
from bs4 import BeautifulSoup
from tls_client.response import Response

from .utils import raise_for_status


BASE_URL = "https://www.indeed.com"


class Scraper:
    def __init__(self, url: str, proxy: str, sem: threading.Semaphore):
        self.url: str = url
        self.sem: threading.Semaphore = sem
        self.proxy: str = proxy

        self.session = None
        self.company_name: str = ""
        self.reviews: list[dict] = []
        self.total_review_count: int = 0

    def setup_session(self):
        try:
            self.session = tls_client.Session(
                client_identifier=random.choice(["chrome_112", "chrome_117", "chrome_120", "chrome_111", "chrome_110"]),
                random_tls_extension_order=True
            )
            self.session.timeout_seconds = 5
            self.session.proxies = {
                "http": f"http://{self.proxy}",
                "https": f"http://{self.proxy}",
            }
            self.session.headers = {
                'authority': 'www.indeed.com',
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'accept-language': 'en-US,en;q=0.9,ru;q=0.8',
                'cache-control': 'max-age=0',
                'referer': 'https://www.indeed.com',
                'upgrade-insecure-requests': '1',
                'user-agent': pyuseragents.random(),
            }

        except Exception as error:
            logger.error(f"Failed to setup session: {error} | Retrying..")
            time.sleep(0.25)
            self.setup_session()

    def send_request(self, url: str, params: dict = None) -> Response:
        try:
            response = self.session.get(url, params=params)
            raise_for_status(response)
            return response

        except Exception as error:
            logger.error(f"{error} | Retrying..")
            time.sleep(0.25)
            self.setup_session()
            return self.send_request(url, params=params)

    def get_reviews(self) -> None:
        logger.info(f"Fetching reviews from {self.url}")

        def fetch_and_parse_reviews(url: str) -> None:
            _response = self.send_request(url)

            _soup = BeautifulSoup(_response.text, 'html.parser')
            _initial_data = soup.find('script', {'id': 'comp-initialData'}).text.strip()

            _data = json.loads(_initial_data)
            _reviews = _data["reviewsList"]["items"]

            logger.info(f"Fetched {len(_reviews)} reviews from {url} | Total: {len(self.reviews)}/{self.total_review_count}")
            self.reviews.extend(_reviews)

        def process_safe_fetch(_sem: threading.Semaphore, url: str) -> None:
            _sem.acquire()
            try:
                fetch_and_parse_reviews(url)
            finally:
                _sem.release()


        response = self.send_request(self.url, params={'fcountry': 'ALL'})
        soup = BeautifulSoup(response.text, 'html.parser')
        initial_data = soup.find('script', {'id': 'comp-initialData'}).text.strip()

        data = json.loads(initial_data)
        self.company_name = data["reviewsList"]["companyName"]
        self.reviews.extend(data["reviewsList"]["items"])

        self.total_review_count = data["reviewsFilters"]["reviewsCount"]["totalReviewCount"]
        logger.info(f"Total reviews found: {self.total_review_count} | URL: {self.url}")

        if self.total_review_count > 20:
            pages = self.total_review_count // 20
            links = [f"{self.url}?start={i * 20}" for i in range(1, pages)]

            threads = [
                threading.Thread(target=process_safe_fetch, args=(self.sem, link))
                for link in links
            ]
            [thread.start() for thread in threads]
            [thread.join() for thread in threads]

        if not self.reviews:
            logger.warning(f"No reviews found on {self.url}\n\n")
        else:
            logger.success(f"Fetched {len(self.reviews)} reviews from {self.url}\n\n")


    def process_reviews(self) -> list[dict]:
        processed_reviews = []

        for review in self.reviews:
            try:
                review_date = review["submissionDate"]
                location_data = review["location"].split(", ")
                if len(location_data) == 2:
                    location_city, location_state = location_data
                else:
                    location_city, location_state = location_data[0], None
                job_title = review["jobTitle"]
                employments_status = review["currentEmployee"]
                overall_rating = review["overallRating"]
                work_and_life_balance_rating = review["workAndLifeBalanceRating"]["rating"]
                compensation_and_benefits_rating = review["compensationAndBenefitsRating"]["rating"]
                job_security_and_advancement_rating = review["jobSecurityAndAdvancementRating"]["rating"]
                management_rating = review["managementRating"]["rating"]
                job_culture_rating = review["cultureAndValuesRating"]["rating"]
                title = review["title"]["text"].replace("\n", " ").strip()
                review_text = review["text"]["text"].replace("\n", " ").strip()

                processed_reviews.append({
                    "Company Name": self.company_name,
                    "Review Date": review_date,
                    "Location City": location_city,
                    "Location State": location_state,
                    "Job Title": job_title.strip(),
                    "Employment Status": employments_status,
                    "Overall Rating": overall_rating,
                    "Job Work/Life Balance Rating": work_and_life_balance_rating,
                    "Compensation/Benefits Rating": compensation_and_benefits_rating,
                    "Job Security/Advancement Rating": job_security_and_advancement_rating,
                    "Management Rating": management_rating,
                    "Job Culture Rating": job_culture_rating,
                    "Title": title,
                    "Review": review_text
                })

            except Exception as error:
                logger.error(f"Failed to process review: {error} | Skipping..")
                continue

        return processed_reviews


    def start(self) -> list[dict]:
        logger.info(f"Starting to fetch reviews from {self.url}")

        try:
            self.setup_session()
            self.get_reviews()
            return self.process_reviews()

        except Exception as error:
            logger.error(f"Failed to fetch reviews from {self.url}: {error} | Retrying..")
            time.sleep(1)
            return self.start()
