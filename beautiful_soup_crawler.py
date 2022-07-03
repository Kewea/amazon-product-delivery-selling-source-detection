import json
import re
import requests
from pathlib import Path
from bs4 import BeautifulSoup
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
