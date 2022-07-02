# Amazon Product Delivery and Selling Source Detection Script
## Preface
For product being listed on Amazon which is both delivered and sold by Amazon company itself, the price most likely will be cheaper than the other sellers.<br/><br/>
Meanwhile, it is more secure to purchase product which meets the previous mentioned requirement since Amazon will be responsible for return and refund when something goes wrong.<br/><br/>
However, for major hit products, it could be difficult to do so since they could be sold out within a short period of time as people may us bots to detect and complete the whole process.
This script neither solve the related issue nor acting as a bot to compete against other user for purchasing products. Instead, it just detects whether the product which is delivered and sold by Amazon company itself
is available or not.

## Overview
This script aims at 
- Detecting whether the delivery and selling source is Amazon or not OR
- Detecting the price which is below your expected price


## Prerequisite
Python3 is required. To check for existence or version of Python, you may execute
```bash
python3 -V
```

## Installation & Usage
1. Git clone/fork the project to any directory of your computer
2. Choose either Beautiful soup or Selenium version

### Difference between Beauty soup and Selenium version
|                 | Beautiful soup          | Selenium            |
|-----------------|-------------------------|---------------------|
| Execution speed | faster                  | slower              |
| Stability       | sometimes fail          | steady              |
| Product's URL   | from browser's dev tool | Amazon product page |


### Selenium version
1. Data Preparation
   1. Copy the URL of the product

### Beauty soup version
1. Data Preparation
   1. Open dev tool (F12 for Chrome) and select `Network` tab
   2. Access the product page on Amazon 
   3. Click on section for listing out all available prices and sellers
   4. Look for request with type xhr which has `.../gp/product/ajax/ref...` in the URL
   ```bash
    https://www.amazon.co.jp/gp/product/ajax/ref=...
   ```

### Application Setup
1. Rename `example_products.json` to `products.json` and write down product details into `products.json`
    ```json
   {
      "products": [
        {
          "name": "any name you want",
          "link": "URL found in above steps",
          "expected_price": 1000
        }
      ]
    }  
    ```
2. Setup cron job
   1. Open terminal
   2. Type `crontab -e` and then `i`
   3. Put down execution command
   ```bash
   # Date time can be changed
   */1 * * * * cd {directory having source code}; source .venv/bin/activate && python main.py -e prod; deactivate;
   ```
   4. Click `Esc`, type `:wq`
   
### Command Arguments
1. `-e` or `--environment`
   - Affect the data file being used. `prod` is used by default
2. `-c` or `--crawl-approach`
   - Approach being used for crawling. `selenium` is used by default

# Disclaimer
This script is for recreational purpose only. Any illegal usage including transforming the script into any means 
for automatic ordering purpose by modifying the source code is prohibited. All rights reserved by the author of 
this script.