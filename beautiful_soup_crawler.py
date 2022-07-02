import datetime
import json
import re
import requests
import notitfication
from pathlib import Path
from bs4 import BeautifulSoup
from decimal import Decimal
from base_crawler import BaseCrawler


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
                    updated_product_info = self.compare_product_info(existing_product_info, self.crawl_dom(soup).values())

            updated_products.append(updated_product_info)

        with open(self.file_path, 'wb') as fp:
            fp.write(json.dumps({"products": updated_products}, indent=2, ensure_ascii=False).encode("utf8"))

    # def compare_product_info(self, existing_info: dict, options) -> dict:
    #     """
    #     Compare existing product info against newly fetched one
    #
    #     :param existing_info:
    #     :param options:
    #     :return:
    #     """
    #     for index, item in enumerate(options):
    #         # print(f'{product["name"]}. {item["ship_from"]} - {item["sold_by"]} : {item["price"]}')
    #         actual_price = int(Decimal(re.sub(r'[^\d.]', '', item["price"])))
    #
    #         # Delivery and selling source are both Amazon
    #         if item["ship_from"] == 'Amazon' and item["sold_by"] == 'Amazon':
    #             info = self.update_product_info(existing_info, "Amazon", "Amazon", actual_price)
    #             return info
    #
    #         # Shop with the lowest price
    #         if actual_price <= int(existing_info["expected_price"]):
    #             info = self.update_product_info(existing_info, item["ship_from"], item["sold_by"], actual_price)
    #             return info
    #
    #     return existing_info
    #
    # def update_product_info(self, product: dict, ship_from: str = "", sold_by: str = "", actual_price: int = 0) -> dict:
    #     """
    #     Check if the product has been recorded or not
    #
    #     :param product:
    #     :param ship_from:
    #     :param sold_by:
    #     :param actual_price:
    #     :return:
    #     """
    #     if ("ship_from" not in product or product["ship_from"] != ship_from) and (
    #             "sold_by" not in product or product["sold_by"] != sold_by):
    #         now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    #         notitfication.send_mac_notification(product["name"],
    #                                             f'{now}: shipped by {ship_from} from {sold_by} with actual price {actual_price}')
    #         product.update({"ship_from": ship_from, "sold_by": sold_by, "actual_price": actual_price})
    #     return product

    def crawl_dom(self, soup) -> dict:
        """
        Crawl through DOM to find corresponding info

        :param soup:
        :return:
        """
        product_info = {}
        for index, (ship_from_html, sold_by_html, price_html) in enumerate(zip(soup.select('div#aod-offer-shipsFrom'),
                                                                               soup.findAll(id='aod-offer-soldBy'),
                                                                               soup.findAll('div', {'id': re.compile('aod-price-\d*')}))):
            ship_from = ship_from_html.find('span', class_='a-size-small a-color-base').text.strip()
            sold_by = sold_by_html.find('a', class_='a-size-small a-link-normal').text.strip()
            price = price_html.find('span', class_='a-offscreen').text.strip()
            product_info[index] = {'ship_from': ship_from, 'sold_by': sold_by, 'price': price}

        return product_info
