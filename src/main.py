import asyncio
import json
import random
import noble_tls
import pyuseragents

from loguru import logger
from bs4 import BeautifulSoup
from noble_tls import Client
from curl_cffi.requests import AsyncSession
from noble_tls.response import Response

from .utils import raise_for_status


BASE_URL = "https://www.indeed.com"


class Scraper:
    def __init__(self, url: str):
        self.url = url
        self.session = noble_tls.Session(
            client=Client.CHROME_111,
            random_tls_extension_order=True
        )

        self.company_name: str = ""
        self.reviews: list[dict] = []

    async def setup_session(self):
        try:
            client = random.choice(list(Client.__dict__.values()))
            self.session = noble_tls.Session(
                client=client,
                random_tls_extension_order=True,
            )
            self.session.timeout_seconds = 5
            self.session.proxies = {
                "http": "http://5rbld50md4:sfhw02cusg_country-rs@premium.proxywing.com:12321",
                "https": "http://5rbld50md4:sfhw02cusg_country-rs@premium.proxywing.com:12321"
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
            await asyncio.sleep(0.25)
            await self.setup_session()

    async def send_request(self, url: str, params: dict = None) -> Response:
        try:
            response = await self.session.get(url, params=params)
            raise_for_status(response)
            return response

        except Exception as error:
            logger.error(f"{error} | Retrying..")
            await asyncio.sleep(1)
            await self.setup_session()
            return await self.send_request(url, params=params)

    async def get_reviews(self) -> None:
        logger.info(f"Fetching reviews from {self.url}")

        async def fetch_and_parse_reviews(url: str) -> None:
            _response = await self.send_request(url)

            _soup = BeautifulSoup(_response.text, 'html.parser')
            _initial_data = soup.find('script', {'id': 'comp-initialData'}).text.strip()

            _data = json.loads(_initial_data)
            _reviews = _data["reviewsList"]["items"]
            logger.info(f"Fetched {len(_reviews)} reviews from {url}")
            self.reviews.extend(_reviews)


        async def process_safe_fetch(sem: asyncio.Semaphore, url: str) -> None:
            async with sem:
                await fetch_and_parse_reviews(url)

        response = await self.send_request(self.url, params={'fcountry': 'ALL'})
        soup = BeautifulSoup(response.text, 'html.parser')
        initial_data = soup.find('script', {'id': 'comp-initialData'}).text.strip()

        data = json.loads(initial_data)
        self.company_name = data["reviewsList"]["companyName"]
        self.reviews.extend(data["reviewsList"]["items"])

        # pagination_links = data["reviewsList"]["pagination"]["paginationLinks"]
        # print(pagination_links)
        # if pagination_links:
        #     print(len(pagination_links))
        #     links = [f"{BASE_URL}{link['href']}" for link in pagination_links[1:]]
        #     await asyncio.gather(*[fetch_and_parse_reviews(link) for link in links])

        total_review_count = data["reviewsFilters"]["reviewsCount"]["totalReviewCount"]
        logger.info(f"Total reviews found: {total_review_count} | URL: {self.url}")
        if total_review_count > 20:
            pages = total_review_count // 20
            links = [f"{self.url}?start={i * 20}" for i in range(1, pages)]
            sem = asyncio.Semaphore(1)
            await asyncio.gather(*[process_safe_fetch(sem, link) for link in links])

        if not self.reviews:
            logger.warning(f"No reviews found on {self.url}")
        else:
            logger.info(f"Fetched {len(self.reviews)} reviews from {self.url}")


    def process_reviews(self) -> list[dict]:
        processed_reviews = []

        for review in self.reviews:
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

        return processed_reviews


    async def start(self):
        logger.info(f"Starting to fetch reviews from {self.url}")

        try:
            await self.setup_session()
            await self.get_reviews()
            return self.process_reviews()

        except Exception as error:
            logger.error(f"Failed to fetch reviews from {self.url}: {error} | Retrying..")
            await asyncio.sleep(1)
            return await self.start()
