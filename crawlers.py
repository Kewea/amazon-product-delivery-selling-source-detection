import json
import re
import requests
import logging
import sys
import datetime
import notitfication
from bs4 import BeautifulSoup
from pathlib import Path
from decimal import Decimal
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from seleniumwire import webdriver
from webdriver_manager.chrome import ChromeDriverManager

logger = logging.getLogger(__name__)


class BaseCrawler:
    def __init__(self, file_path: Path):
        with open(file_path, "r") as f:
            try:
                self.product_list = json.load(f)
            except json.JSONDecodeError:
                logger.error(f"{file_path} format is invalid")
                sys.exit()

        self.file_path = file_path

    def compare_product_info(self, existing_info: dict, options) -> dict:
        """
        Compare existing product info against newly fetched one

        :param existing_info:
        :param options:
        :return:
        """
        for index, item in enumerate(options):
            # print(f'{product["name"]}. {item["ship_from"]} - {item["sold_by"]} : {item["price"]}')
            actual_price = int(Decimal(re.sub(r'[^\d.]', '', item["price"])))
            amazon = re.compile(r"^Amazon.*")

            # Delivery and selling source are both Amazon
            if re.match(amazon, item["ship_from"]) and re.match(amazon, item["sold_by"]):
                info = self.update_product_info(existing_info, "Amazon", "Amazon", actual_price)
                return info

            # Shop with the lowest price
            if actual_price <= int(existing_info["expected_price"]):
                info = self.update_product_info(existing_info, item["ship_from"], item["sold_by"], actual_price)
                return info

        return existing_info

    def update_product_info(self, product: dict, ship_from: str = "", sold_by: str = "", actual_price: int = 0) -> dict:
        """
        Check if the product has been recorded or not

        :param product:
        :param ship_from:
        :param sold_by:
        :param actual_price:
        :return:
        """
        if ("ship_from" not in product or product["ship_from"] != ship_from) or (
                "sold_by" not in product or product["sold_by"] != sold_by):
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            notitfication.send_mac_notification(product["name"],
                                                f'{now}: shipped by {ship_from} from {sold_by} with actual price {actual_price}')
            product.update({"ship_from": ship_from, "sold_by": sold_by, "actual_price": actual_price})
        return product


class BeautifulSoupCrawler(BaseCrawler):
    def __init__(self, file_path: Path):
        super().__init__(file_path)

    def data_scraping(self):
        updated_products = list()

        for existing_product_info in self.product_list["products"]:
            updated_product_info = existing_product_info
            with requests.session() as request:
                response = request.get(existing_product_info["link"])
                if response.ok:
                    soup = BeautifulSoup(response.text, "html.parser")
                    updated_product_info = self.compare_product_info(existing_product_info,
                                                                     self.crawl_dom(soup).values())

            updated_products.append(updated_product_info)

        with open(self.file_path, 'wb') as fp:
            fp.write(json.dumps({"products": updated_products}, indent=2, ensure_ascii=False).encode("utf8"))

    def crawl_dom(self, soup) -> dict:
        """
        Crawl through DOM to find corresponding info

        :param soup:
        :return:
        """
        product_info = {}
        for index, (ship_from_html, sold_by_html, price_html) in enumerate(zip(soup.select('div#aod-offer-shipsFrom'),
                                                                               soup.findAll(id='aod-offer-soldBy'),
                                                                               soup.findAll('div', {'id': re.compile(
                                                                                   'aod-price-\d*')}))):
            ship_from = ship_from_html.find('span', class_='a-size-small a-color-base').text.strip()
            sold_by = sold_by_html.find('a', class_='a-size-small a-link-normal').text.strip()
            price = price_html.find('span', class_='a-offscreen').text.strip()
            product_info[index] = {'ship_from': ship_from, 'sold_by': sold_by, 'price': price}

        return product_info


class SeleniumCrawler(BaseCrawler):
    def __init__(self, file_path: Path):
        super().__init__(file_path)
        self.driver = self.create_driver_instance()

    def data_scraping(self):
        updated_products = list()

        for existing_product_info in self.product_list["products"]:
            # Access Amazon product link
            self.driver.get(existing_product_info["link"])

            # Click on seller option button (a link)
            WebDriverWait(self.driver, 3) \
                .until(
                EC.element_to_be_clickable((By.XPATH, "//a[@class='a-touch-link a-box olp-touch-link' and @href]"))) \
                .click()
            self.driver.implicitly_wait(3)

            updated_product_info = self.compare_product_info(existing_product_info,
                                                             self.crawl_dom(self.driver).values())
            updated_products.append(updated_product_info)

        self.driver.quit()
        with open(self.file_path, 'wb') as fp:
            fp.write(json.dumps({"products": updated_products}, indent=2, ensure_ascii=False).encode("utf8"))

    def create_driver_instance(self):
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--headless')
        return webdriver.Chrome(ChromeDriverManager().install(), options=chrome_options)

    def crawl_dom(self, driver) -> dict:
        product_info = {}

        # Get shipping source
        for index, (ship_from, sold_by, price) in enumerate(zip(
                driver.find_elements(By.XPATH, "//div[@id='aod-offer-shipsFrom']/div/div/div[2]/span"),
                driver.find_elements(By.XPATH, "//div[@id='aod-offer-soldBy']/div/div/div[2]/a"),
                driver.find_elements(By.XPATH, "//div[contains(@id, 'aod-price')]/span/span[1]"))):
            product_info[index] = {
                'ship_from': ship_from.get_attribute("innerHTML").strip(),
                'sold_by': sold_by.get_attribute("innerHTML").strip(),
                'price': price.get_attribute("innerHTML").strip()
            }

        return product_info
