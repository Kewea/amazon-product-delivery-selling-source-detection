import logging
import sys

import constants
import datetime
import json
import re
import notitfication
from decimal import Decimal
from pathlib import Path

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

            # Delivery and selling source are both Amazon
            if item["ship_from"] == 'Amazon' and item["sold_by"] == 'Amazon':
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
