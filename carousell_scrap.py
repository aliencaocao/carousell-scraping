import sys, os
import time
import re
import urllib
from pprint import pprint
import pandas as pd
import bs4
from bs4 import BeautifulSoup
import selenium
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
print(f'Carousell Scraping V1.0 by Billy Cao\nRunning on Python {sys.version}, Selenium {selenium.__version__}, BeautifulSoup {bs4.__version__}')


def request_page(url):
    """ Returns BeautifulSoup4 Objects (soup)"""
    driver.get(url)
    page = 1
    timeout = 5
    while page < page_limit:
        try:
            next_page_btn = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.XPATH, '//main[1]/div/button[.="Load more"]')))  # wait max timeout sec for loading
            driver.execute_script("arguments[0].click();", next_page_btn)  # click the load more button through ads
            page += 1
        except TimeoutException as e:
            break
    time.sleep(timeout)
    print(f'All results loaded. Total: {page} pages.')
    return BeautifulSoup(driver.page_source, "html.parser")


def parse_info(item_div, mode=1):
    a = item_div.div.find_all('a', recursive=False)
    seller_divs = a[0].find_all('div', recursive=False)[1]
    item_p = a[1].find_all('p', recursive=False)
    if mode == 1:
        return {'seller_name': seller_divs.p.get_text(),
                'seller_url': home+a[0]['href'],
                'item_name': a[1].find_all('div', recursive=False)[1].p.get_text(),
                'item_url': home+a[1]['href'],
                'time_posted': seller_divs.div.p.get_text(),  # TODO: process into absolute datetime
                'condition': item_p[1].get_text(),
                'price': re.findall(r"\d+", item_p[0].get_text().replace(',', ''))[0]}  # 0 is discounted price, 1 is original price, if applicable
    else:
        return {'seller_name': seller_divs.p.get_text(),
                'seller_url': home+a[0]['href'],
                'item_name': item_p[0].get_text(),
                'item_url': home+a[1]['href'],
                'time_posted': seller_divs.div.p.get_text(),  # TODO: process into absolute datetime
                'condition': item_p[3].get_text(),
                'price': re.findall(r"\d+", item_p[1].get_text().replace(',', ''))[0]}  # 0 is discounted price, 1 is original price, if applicable


home = 'https://sg.carousell.com'
item = input('Enter item to scrape: ')
page_limit = int(input('Up to how many pages to scrap? Each page is 23-25 listings: '))
extension = f'/search/{urllib.parse.quote(item)}'
opts = Options()
opts.add_experimental_option('prefs', {'intl.accept_languages': 'en,en_US'})
driver = webdriver.Chrome(options=opts)
driver.minimize_window()
print(f'Chrome Web Driver loaded. Version: {driver.capabilities["browserVersion"]}\n')  # use "version" on Linux
parse_mode = 1  # Carousell have 2 formats of their item divs. See below comment for more info.
tries = 1

while tries < 5:  # retrying loop as the div class position is random
    try:
        print(f'Retrieving search results on {item}...')
        search_results_soup = request_page(home+extension)
        # TODO: Find concrete way to locate correct class name, current work around works 99% of times.
        item_divs_class = ' '.join(search_results_soup.find('main').find('div').find('div').find('div')['class'])  # changes randomly but 99% of the time its the first div
        print(f'Detected item_divs class: {item_divs_class}')
        item_divs = search_results_soup.find('main').find('div').find('div').find_all('div', class_=item_divs_class, recursive=False)  # filter out ads divs
        print(f'Found {len(item_divs)} listings. Parsing...')
        items_list = [parse_info(item_div, parse_mode) for item_div in item_divs]
        break
    except AttributeError as e:  # no item_divs at all
        raise RuntimeError('The search has returned no result.')
    except IndexError as e:
        print(f'Parsing attempt {tries} failed due to class name error using parse mode {parse_mode}. Retrying with parse mode 2...\n')
        tries += 1
        parse_mode = 2
        continue
else:
    raise RuntimeError('Parsing failed as it still faces IndexError after 10 tries.')

driver.quit()
print(f'Parse success using mode {parse_mode}! Sample item parsed:')
pprint(items_list[0])
df = pd.DataFrame(items_list)
df.to_csv(f'{item}.csv', index=False)
print(f'Results saved to {item}.csv')
input('Press enter to exit')

'''
Two parse modes only differs in item divs 2nd a
Structure of Carousell HTML FORMAT 1 (parse_mode 1):
body > find main > 1st div > 1st div > divs of items
    in divs of items > parents of each item
        parent > 1st div > 1st a is seller, 2nd a is item page
            in 1st a: 2nd div > p is seller name, > div > p is time posted
            in 2nd a: 2nd div > p is item name but with ... if too long, directly under 2nd a first p is price, 2nd p is condition
        parent > 2nd div > button > span is number of likes
total 24 or 25 results loaded once.

Structure of Carousell HTML FORMAT 2 (parse_mode 2):
body > find main > 1st div > 1st div > divs of items
    in divs of items > parents of each item
        parent > 1st div > 1st a is seller, 2nd a is item page
            in 1st a: 2nd div > p is seller name, > div > p is time posted
            in 2nd a: 1st p is FULl NAME, 2nd p is price, 3rd p is description, 4th p is condition
        parent > 2nd div > button > span is number of likes
total 24 or 25 results loaded once.

body > find main > div > button to view more
view more button loads on top of existing, so can prob spam view more then gather all items at once
MAY NOT BE FIRST DIV! Temp workaround is to get class name of the correct item divs
'''
