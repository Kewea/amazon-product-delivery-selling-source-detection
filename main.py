import datetime
import json
import platform
import re
import requests
import subprocess
from bs4 import BeautifulSoup
from decimal import Decimal


def source_detection():
    result = {}
    updated_products = []

    file = open('products.json')
    product_list = json.load(file)

    for existing_product_info in product_list["products"]:
        updated_product_info = existing_product_info
        with requests.session() as request:
            response = request.get(existing_product_info["link"])
            if response.ok:
                soup = BeautifulSoup(response.text, "html.parser")
                new_product_info = crawl_dom(soup)
                updated_product_info = compare_product_info(existing_product_info, new_product_info.values())

        updated_products.append(updated_product_info)

    result.update({"products": updated_products})
    with open('products.json', 'wb') as fp:
        fp.write(json.dumps(result, indent=2, ensure_ascii=False).encode("utf8"))


def compare_product_info(existing_info: dict, options) -> dict:
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
            info = update_product_info(existing_info, "Amazon", "Amazon", actual_price)
            return info

        # Shop with the lowest price
        if actual_price <= int(existing_info["expected_price"]):
            info = update_product_info(existing_info, item["ship_from"], item["sold_by"], actual_price)
            return info

    return existing_info


def update_product_info(product: dict, ship_from: str = "", sold_by: str = "", actual_price: int = 0) -> dict:
    """
    Check if the product has been recorded or not

    :param product:
    :param ship_from:
    :param sold_by:
    :param actual_price:
    :return:
    """
    if ("ship_from" not in product or product["ship_from"] != ship_from) and ("sold_by" not in product or product["sold_by"] != sold_by):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        send_mac_notification(product["name"], f'{now}: shipped by {ship_from} from {sold_by} with price {actual_price}')
        product.update({"ship_from": ship_from, "sold_by": sold_by, "actual_price": actual_price})
    return product


def crawl_dom(soup) -> dict:
    """
    Crawl through DOM to find corresponding info

    :param soup:
    :return:
    """
    product_info = {}
    for index, (ship_from_html, sold_by_html, price_html) in enumerate(zip(soup.select('div#aod-offer-shipsFrom'),
                                                                           soup.findAll(id='aod-offer-soldBy'),
                                                                           soup.findAll('div', {
                                                                               'id': re.compile('aod-price-\d*')}))):
        ship_from = ship_from_html.find('span', class_='a-size-small a-color-base').text.strip()
        sold_by = sold_by_html.find('a', class_='a-size-small a-link-normal').text.strip()
        price = price_html.find('span', class_='a-offscreen').text.strip()
        product_info[index] = {'ship_from': ship_from, 'sold_by': sold_by, 'price': price}

    return product_info


def send_mac_notification(title: str, message: str) -> None:
    """
    Send message to mac notification center

    :param title:
    :param message:
    :return:
    """
    cmd = '''
    on run argv
      display notification (item 2 of argv) with title (item 1 of argv)
    end run
    '''
    if platform.system() == "Darwin":
        subprocess.call(['osascript', '-e', cmd, title, message])


if __name__ == '__main__':
    source_detection()
