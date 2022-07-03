import argparse
import logging
import sys
import constants
import os
from pathlib import Path

logging.basicConfig(level=logging.ERROR,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    encoding='utf-8',
                    filename="app.log")
logger = logging.getLogger(__name__)
os.environ['WDM_LOG'] = "0"

if __name__ == '__main__':
    import crawlers
    parser = argparse.ArgumentParser()
    parser.add_argument('-e', '--environment', type=str, default=constants.PROD, choices=[constants.PROD, constants.TEST],
                        help="Select environment")
    parser.add_argument('-c', '--crawl-approach', type=str, default=constants.SELENIUM,
                        choices=[constants.SELENIUM, constants.BEAUTIFULSOUP], help="Select crawling approach")
    # parser.add_argument('-d', '--data-format', type=str, default=constants.JSON,
    #                     choices=[constants.JSON, constants.CSV], help="Select data file type")
    args = parser.parse_args()

    if args.environment.lower() == constants.PROD:
        # Filepath example: data/products.{json|csv} TODO csv
        file_path = Path(__file__).parent / f"{constants.DATA}/products.json"
    else:
        # Filepath example: tests/products_{selenium|beautifulsoup}.{json|csv} TODO csv
        file_path = Path(__file__).parent / f"{constants.TEST}/products_{args.crawl_approach.lower()}.json"

    if not Path(file_path).is_file():
        logger.error(f"File does not exist: {file_path}")
        sys.exit()

    if args.crawl_approach.lower() == constants.SELENIUM:
        crawlers.SeleniumCrawler(file_path).data_scraping()
    else:
        crawlers.BeautifulSoupCrawler(file_path).data_scraping()
