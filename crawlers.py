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
from selenium.common import NoSuchElementException, TimeoutException
from seleniumwire import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from constants import AMAZON_PRODUCT_PRICE_URL

logger = logging.getLogger(__name__)


class BaseCrawler:
    def __init__(self, file_path: Path, mode: int):
        with open(file_path, "r") as f:
            try:
                self.product_list = json.load(f)
            except json.JSONDecodeError:
                logger.error(f"{file_path} format is invalid")
                sys.exit()

        self.file_path = file_path
        self.mode = mode

    def compare_product_info(self, existing_info: dict, options) -> dict:
        """
        Compare existing product info against newly fetched one

        :param existing_info:
        :param options:
        :return:
        """
        optimal_choice = {}

        for index, item in enumerate(options):
            # print(f'{existing_info["name"]}. {item["ship_from"]} - {item["sold_by"]} : {item["price"]} + {item["delivery_fee"]}')
            delivery_fee = re.sub(r'[^\d.]', '', item["delivery_fee"])
            delivery_fee = 0 if not delivery_fee else int(Decimal(delivery_fee))

            # Sum up product price with delivery fee
            total_price = re.sub(r'[^\d.]', '', item["price"])
            total_price = 0 if not total_price else int(Decimal(total_price)) + delivery_fee

            if not total_price:
                continue

            amazon = re.compile(r"^Amazon.*")
            item.update({"id": index, "actual_price": total_price})

            # Delivery and selling source are both Amazon
            if re.match(amazon, item["ship_from"]) and re.match(amazon, item["sold_by"]):
                info = self.update_product_info(existing_info, item)
                return info

            # Lowest price
            if (self.mode == 0) and (not optimal_choice or total_price < optimal_choice["actual_price"]):
                optimal_choice = item

            # Price lower than expectation
            if (self.mode == 1) and (not optimal_choice and total_price <= int(existing_info["expected_price"])):
                optimal_choice = item

        if optimal_choice:
            return self.update_product_info(existing_info, optimal_choice)

        return existing_info

    def update_product_info(self, existing_info: dict, new_info: dict) -> dict:
        """
        Check if the product has been recorded or not

        :param existing_info:
        :param new_info:
        :return:
        """
        if "stop" in existing_info:
            return existing_info

        # Continue to send notification if both ship_from & sold_by are from Amazon
        amazon = re.compile(r"^Amazon.*")
        if ("ship_from" not in existing_info or existing_info["ship_from"] != new_info["ship_from"]) or \
                ("sold_by" not in existing_info or existing_info["sold_by"] != new_info["sold_by"]) or \
                (re.match(amazon, new_info["ship_from"]) and re.match(amazon, new_info["sold_by"])):
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            notitfication.send_mac_notification(existing_info["name"],
                                                f'{now}: shipped by {new_info["ship_from"]} from {new_info["sold_by"]} with actual price {new_info["actual_price"]}')
            existing_info.update({"ship_from": new_info["ship_from"], "sold_by": new_info["sold_by"], "actual_price": new_info["actual_price"]})
        return existing_info


class BeautifulSoupCrawler(BaseCrawler):
    def __init__(self, file_path: Path, mode: int):
        super().__init__(file_path, mode)

    def data_scraping(self):
        """
        Use BeautifulSoup to crawl the web

        :return:
        """
        updated_products = []

        for existing_product_info in self.product_list["products"]:
            updated_product_info = existing_product_info
            with requests.session() as request:
                product_id = re.match(".*/dp/(.*)/ref.*", existing_product_info["link"]).group(1)
                response = request.get(AMAZON_PRODUCT_PRICE_URL.format(product_id=product_id))
                if response.ok:
                    soup = BeautifulSoup(response.text, "html.parser")
                    updated_product_info = self.compare_product_info(existing_product_info, self.crawl_dom(soup).values())

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
        for index, (ship_from_html, sold_by_html, price_html, delivery_fee_html) in enumerate(zip(
                soup.select('div#aod-offer-shipsFrom'),
                soup.findAll(id='aod-offer-soldBy'),
                soup.findAll('div', {'id': re.compile('aod-price-\d*')}),
                soup.findAll('div', {'id': 'mir-layout-DELIVERY_BLOCK-slot-PRIMARY_DELIVERY_MESSAGE_LARGE'}))):
            ship_from = ship_from_html.find('span', class_='a-size-small a-color-base').text.strip()
            sold_by = sold_by_html.find('a', class_='a-size-small a-link-normal').text.strip()
            price = price_html.find('span', class_='a-offscreen').text.strip()
            delivery_fee = delivery_fee_html.find('span').get('data-csa-c-delivery-price')
            # print(ship_from, sold_by, price, delivery_fee)
            product_info[index] = {'ship_from': ship_from, 'sold_by': sold_by, 'price': price, 'delivery_fee': delivery_fee}

        return product_info


class SeleniumCrawler(BaseCrawler):
    def __init__(self, file_path: Path, mode: int):
        super().__init__(file_path, mode)
        self.driver = self.create_driver_instance()

    def data_scraping(self):
        """
        Use Selenium to crawl the web

        :return:
        """
        # Temporarily array for storing product info
        updated_products = []

        for existing_product_info in self.product_list["products"]:
            # Access Amazon product link
            self.driver.get(existing_product_info["link"])

            try:
                # Click on seller option button (a link)
                WebDriverWait(self.driver, 3) \
                    .until(EC.element_to_be_clickable((By.XPATH, "//a[@class='a-touch-link a-box olp-touch-link' and @href]"))) \
                    .click()
                self.driver.implicitly_wait(3)
            except TimeoutException:
                logger.error("[Selenium] Time out occurs when accessing the webpage")
                updated_products.append(existing_product_info)
            else:
                if new_product_info := self.crawl_dom(self.driver).values():
                    updated_products.append(self.compare_product_info(existing_product_info, new_product_info))
                else:
                    logger.info(f'[Selenium] Fail to update info for {existing_product_info["name"]}')
                    updated_products.append(existing_product_info)

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
        try:
            for index, (ship_from, sold_by, price, delivery_fee) in enumerate(zip(
                    driver.find_elements(By.XPATH, "//div[@id='aod-offer-shipsFrom']/div/div/div[2]/span"),
                    driver.find_elements(By.XPATH, "//div[@id='aod-offer-soldBy']/div/div/div[2]/a"),
                    driver.find_elements(By.XPATH, "//div[contains(@id, 'aod-price')]/span/span[1]"),
                    driver.find_elements(By.XPATH, "//div[contains(@id, 'mir-layout-DELIVERY_BLOCK-slot-PRIMARY_DELIVERY_MESSAGE_LARGE')]/span"))):
                # driver.find_elements(By.XPATH, "//div[@id='aod-offer-heading']/h5")
                product_info[index] = {
                    'ship_from': ship_from.get_attribute("innerHTML").strip(),
                    'sold_by': sold_by.get_attribute("innerHTML").strip(),
                    'price': price.get_attribute("innerHTML").strip(),
                    'delivery_fee': delivery_fee.get_attribute("data-csa-c-delivery-price")
                }
        except NoSuchElementException:
            logger.error("[Selenium] Fail to locate element")

        return product_info
