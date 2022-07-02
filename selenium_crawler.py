import datetime
import json
import re
import notitfication
from decimal import Decimal
from pathlib import Path
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
# from selenium import webdriver
from seleniumwire import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from base_crawler import BaseCrawler


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
            WebDriverWait(self.driver, 3)\
                .until(EC.element_to_be_clickable((By.XPATH, "//a[@class='a-touch-link a-box olp-touch-link' and @href]")))\
                .click()
            self.driver.implicitly_wait(3)

            updated_product_info = self.compare_product_info(existing_product_info, self.crawl_dom(self.driver).values())
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
        # print(product_info)
        return product_info
