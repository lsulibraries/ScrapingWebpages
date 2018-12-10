

import time
import csv

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException


def has_elec(elem):
    if elem.find_elements_by_xpath('../../td[@aria-describedby="list_Online"]/img'):
        return True
    return False


def click_on_headers(driver):
    dropdown_headers = driver.find_elements_by_xpath('//div[@class="titleDetailsHeader"]/span/img[@name="rt"]')
    for i in dropdown_headers:
        i.click()


def get_path_text(driver, path):
    try:
        value = driver.find_element_by_xpath(path).text
    except NoSuchElementException:
        value = ''
    return value


def get_title(driver):
    path = '//span[@id="title_title"]/../../td'
    title = get_path_text(driver, path)
    return title.strip()


def get_vendor_publisher(driver):
    path = '//div[@id="publisherDetailsContainer"]/table/tbody/tr/td[not(text()="Parent")]/b[contains(text(), "Commercial Publisher")]/../../following-sibling::tr/td'
    vendor_publisher = get_path_text(driver, path)
    return vendor_publisher.strip()


def get_url(driver):
    try:
        url = driver.find_element_by_xpath('//div[@id="publisherDetailsContainer"]/table/tbody/tr/td[contains(text(), "Website:")]/a').get_attribute('href')
    except NoSuchElementException:
        url = ''
    return url


def get_phone_number(driver):
    path = '//div[@id="publisherDetailsContainer"]/table/tbody/tr/td[contains(text(), "Phone")]'
    phone = get_path_text(driver, path)
    formatted_phone = phone.replace('Phone:', '').strip()
    return formatted_phone


def get_parent_name(driver):
    path = '//div[@id="publisherDetailsContainer"]/table/tbody/tr/td/b[contains(text(), "Commercial Publisher")]/..[contains(normalize-space(.), "Parent")]/../following-sibling::tr/td'
    parent_name = get_path_text(driver, path)
    return parent_name.strip()


def get_email(driver):
    path = '//div[@id="publisherDetailsContainer"]/table/tbody/tr/td[contains(text(), "Email:")]'
    email = get_path_text(driver, path)
    formatted_email = email.replace('Email:', '').strip()
    return formatted_email


def search_one_title(driver, title_name):
    driver.get("http://ulrichsweb.serialssolutions.com.libezp.lib.lsu.edu/widget/search/", )
    time.sleep(30)
    search_bar = WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.NAME, "query"))
    )
    search_bar.clear()
    search_bar.send_keys(title_name)
    search_bar.send_keys(Keys.RETURN)
    time.sleep(10)
    assert "Search Results" in driver.title


def find_title_matches(driver, title_name):
    path = '//a[@class="titleDetailsLink"][text()="{}"]'.format(title_name)
    match_labels = driver.find_elements_by_xpath(path)
    print(match_labels)
    elec_labels = [i for i in match_labels if has_elec(i)]
    print(elec_labels)
    return elec_labels[0]


def enter_detail_page(driver, title_link):
    title_link.click()
    time.sleep(10)


def get_item_values(driver):
    title = get_title(driver)
    vendor_publisher = get_vendor_publisher(driver)
    provider = ''
    url = get_url(driver)
    parent_name = get_parent_name(driver)
    contact_email = get_email(driver)
    contact_phone = get_phone_number(driver)
    return {
        'title': title,
        'vendor_publisher': vendor_publisher,
        'provider': provider,
        'url': url,
        'parent_name': parent_name,
        'contact_email': contact_email,
        'contact_phone': contact_phone,
    }


def run_one(title_name):
    driver = webdriver.Firefox()
    search_one_title(driver, title_name)
    title_link = find_title_matches(driver, title_name)
    enter_detail_page(title_link, title_link)
    results_dict = get_item_values(driver)
    return results_dict


if __name__ == '__main__':
    titles = ('InfoWorld', 'American Periodicals')

    all_titles_dicts = list()
    for title in titles:
        print(title)
        all_titles_dicts.append(run_one(title))
    with open('output.csv', 'w') as f:
        fieldnames = all_titles_dicts[0].keys()
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for item in all_titles_dicts:
            writer.writerow(item)
