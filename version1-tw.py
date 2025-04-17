import os
import json
import requests
import time
import random
import concurrent.futures
from tqdm import tqdm
import re
import pandas as pd

class ShopeeTWProductScraper:
    def __init__(self, cookies_dir="cookies", proxies_file="proxies.txt"):
        self.cookies_dir = cookies_dir
        self.proxies_file = proxies_file
        self.all_cookies = self.load_all_cookies()
        self.current_cookie_index = 0
        self.current_cookies_dict = {}
        self.proxies = self.load_proxies()
        self.current_proxy_index = 0
        if self.all_cookies:
            self.current_cookies_dict = self.all_cookies[self.current_cookie_index]

        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Referer": "https://shopee.tw/---i.327985547.9368269078",
            "X-API-Source": "pc",
            "X-Requested-With": "XMLHttpRequest",
            "X-Shopee-Language": "zh-Hant",
            "sec-ch-ua": '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "Priority": "u=1, i",
            "Host": "shopee.tw",
            "Content-Type": "application/json",
            "af-ac-enc-dat": "e5f726d6c16495fd",
            "af-ac-enc-sz-token": "ig7tQgeFfQkijhOwJs9cGA==|yZIRWkPxEY6zoyXgiVfBIGmHeYlDX/qjkSs89XmYZ8CSC1HlamlmbQj/Ulq3t4eKRkxOTQ8ABK0h6pui0JQ=|vM4yLxQ46nHuKjj9|08|3",
            "sz-token": "ig7tQgeFfQkijhOwJs9cGA==|yZIRWkPxEY6zoyXgiVfBIGmHeYlDX/qjkSs89XmYZ8CSC1HlamlmbQj/Ulq3t4eKRkxOTQ8ABK0h6pui0JQ=|vM4yLxQ46nHuKjj9|08|3",
            "d-nonptcha-sync": "AAAG0DKXxKgAAAgAABC8qOphlMgdYAAB1gGIAAAB4AHNAYAAAAHiAb4BcgAAAecBtwFrAAAB6QGwAWUAAAHqATQA5gAAAiMBMwDjAAACJQDrA|6|N7",
            "x-sap-ri": "ac4700680a359d5e9fc72d3805018b5b81ee43c6f27d8240989b",
            "x-sap-sec": "1mHrnVDW5CD+pfBkon9ooFOk2K9konBkDs9aoWEkWn90ou/k+n8doUvkEnXhoFWkLn9noWfkQs93o1sktn91oqvkYn8ToqOkUCWvoDfkrnXSonfk9n9+onOktK87otBkbKWKoWvkTn9dotIkUs9soXfktsWyo8nkdn8ooVBkRnWdoUEkMn8BoFCkXsW+ovWk4nWYo1EknnWko8BPon974qrez+EInlOkonX+onWkdKgf8pmMeYOkon8oCnnkonWkqu/kovJNjnvkoUWPon9ioKWkonWkXSH/lIWkonWr59Q2b1LGpHDkoTfQjLrfdCWkoAx9oKWkPnvkoABPonWkoUfMNZgKIZWPonXn3hFwon88R+fPonWJRC8MHSUgjsWkDLMp2HHTnEaG2qE7jyXqaP0WoWVjQQfPonWkoTkWRgfraDfMwaCXVqxPzD2zJCWk5mQToKWk9lkG3mWOonWkon9NlqBLkkWPonWkovcFsnWkoWImgEpEiOHSosnkoXLB+YzVV5ALVYRER2uH0KU7SwC/DAR0SQcdkVqB5Wtt5g4L4wHBYkw6jshh+LhUqLa8cqvmzZyaelVPv7Uuqcz6lrcjXpZpL9QRbN/OrWbwpOH57hZXO+0BgYozydEc1ANUInQic6mRZS+xI4eHfGv3FKAG4HuXPiHjsS3p9OBKdSD4g51bfB1W3rU935r2fbrdASc6CzjSHBQkfsXWhThTsOYk9hf1fvG2RpMxUmjMUU9Oixr1IR7QbFIMPk917bvZRGRND8ou3yrQj/zHpyBQvpRDZbfjDpk/VKrXngaBD0j5LFyrAXzPPeXJ+U2cBHulEKl7glMFho6f8uTVDc6e6dp6SKRQmQt+rDD4z63WvImBPPPKhdHDx6/Cnty+YeuE/nY96SRM6ZFZeINSarrEPj27YRqiF8Czar0CBA1P0o+UMj2MctSZQMXbdbCNKD8af/yDRYAgvdoQw6Nk1c+Z/4FwcnoFKgfdFbSnCXRG6QqH0lNifZ0dYOCp6gy6ViQvnN2hH6taOskuc4hRgUWyQd5N5cYs/1hDrbbG1q9XOFuIdnPmXZwFtltzi7Y7ovCLba+8GTi58OHJHovyt28zIjLbT/rAPaxkMU+Hm8IuPZPKJWZR9STyM5OHOcthPknE5DAx4V30MD2lica/+RiVPQQDvBHtTbEazlgsMo+VoDxkoWskon99FoHbeIoyEw9Rk71zrrdwFfh4jcohegHyG0jlVEBxTLxAZyttIEObl+jHsdmQGQIO/G1mY1s1YeTjzj8KQDq75ywRk59mUXQrXLI2YQIpEYeIHFmZCK0IPU25/do13GWiHeUikyQQXXExgv/px+IRm7z4trzWs54oCq2FoL/LsQ7qiD2cntqnfpWkonfkon9xvSwDpnWkoWYuxjsOonWknolkonlkon9Ge8Tv3KWkotvkon92em17+14CDNWN1JET2ziIDL0RonWkonWkonWkEnWko9QKaBeuBjiIWZRsUHLAmWHjpI0KBSpg1CWkonWkonWkonWkoqfkon9Y0WzEIa481zvcxILnki2JfGiNYSIx9J7G2cdKMw5xYyL5ZgskonWksnWko9SoWNoKhgpfInWkoX3hxInGI5HPfvqeCpgUlliZSmReMSRGYje5ZMJqBANsF/X6G23umDAU0O2PJ1otYTcsZlIYMk++onWkonWkonWoonWkZHqalKBSv5neonWkuou6t7gpiOq1HQ7oNaVyon==",
            "shopee_webUnique_ccd": "ig7tQgeFfQkijhOwJs9cGA%3D%3D%7CyZIRWkPxEY6zoyXgiVfBIGmHeYlDX%2FqjkSs89XmYZ8CSC1HlamlmbQj%2FUlq3t4eKRkxOTQ8ABK0h6pui0JQ%3D%7CvM4yLxQ46nHuKjj9%7C08%7C3",
            "x-sz-sdk-version": "1.12.19"
        }

        if "csrftoken" in self.current_cookies_dict:
            self.headers["x-csrftoken"] = self.current_cookies_dict["csrftoken"]

        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.apply_cookies_from_dict()
        self.success_count = 0
        self.failure_count = 0
        self.total_requests = 0
        self.request_times = []
        self.current_cookie_failures = 0
        self.max_cookie_failures = 3

    def load_all_cookies(self):
        all_cookies = []
        if not os.path.exists(self.cookies_dir):
            print(f"Cookies directory not found: {self.cookies_dir}")
            return all_cookies
        cookie_files = [f for f in os.listdir(self.cookies_dir) if f.endswith('.txt')]
        for cookie_file in cookie_files:
            cookie_path = os.path.join(self.cookies_dir, cookie_file)
            cookie_text = self.load_cookies_text(cookie_path)
            cookie_dict = self.parse_cookies_to_dict(cookie_text)
            if cookie_dict:
                all_cookies.append(cookie_dict)
        print(f"Loaded {len(all_cookies)} cookie files")
        return all_cookies

    def load_cookies_text(self, cookies_file):
        if os.path.exists(cookies_file):
            try:
                with open(cookies_file, "r", encoding="utf-8") as f:
                    cookie_text = f.read().strip()
                return cookie_text
            except Exception as e:
                print(f"Error loading cookies from {cookies_file}: {e}")
        return ""

    def parse_cookies_to_dict(self, cookie_text):
        cookie_dict = {}
        if not cookie_text:
            return cookie_dict
        cookie_pairs = cookie_text.split(';')
        for pair in cookie_pairs:
            if '=' in pair:
                name, value = pair.strip().split('=', 1)
                cookie_dict[name] = value
        return cookie_dict

    def load_proxies(self):
        proxies = []
        if not os.path.exists(self.proxies_file):
            print(f"Proxies file not found: {self.proxies_file}")
            return proxies

        try:
            with open(self.proxies_file, "r", encoding="utf-8") as f:
                lines = f.readlines()

            if len(lines) == 1 and ":" not in lines[0] and len(lines[0].strip().split()) == 1:

                proxy_url = lines[0].strip()
                proxies.append({"http": proxy_url, "https": proxy_url})
                print("Loaded rotating proxy")
            else:
                for line in lines:
                    line = line.strip()
                    if ":" in line:

                        parts = line.split(":")
                        if len(parts) >= 4:
                            ip, port, user, password = parts[:4]
                            proxy_url = f"http://{user}:{password}@{ip}:{port}"
                            proxies.append({"http": proxy_url, "https": proxy_url})
                    else:

                        parts = line.split()
                        if len(parts) >= 4:
                            ip, port, user, password = parts[:4]
                            proxy_url = f"http://{user}:{password}@{ip}:{port}"
                            proxies.append({"http": proxy_url, "https": proxy_url})

                print(f"Loaded {len(proxies)} individual proxies")
        except Exception as e:
            print(f"Error loading proxies: {e}")

        return proxies

    def get_next_cookie(self):
        if not self.all_cookies:
            return False
        self.current_cookie_failures = 0
        self.current_cookie_index = (self.current_cookie_index + 1) % len(self.all_cookies)
        self.current_cookies_dict = self.all_cookies[self.current_cookie_index]
        if "csrftoken" in self.current_cookies_dict:
            self.headers["x-csrftoken"] = self.current_cookies_dict["csrftoken"]
            self.session.headers.update({"x-csrftoken": self.current_cookies_dict["csrftoken"]})
        self.apply_cookies_from_dict()
        return True

    def get_next_proxy(self):
        if not self.proxies:
            return None
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
        return self.proxies[self.current_proxy_index]

    def apply_cookies_from_dict(self):
        if not self.current_cookies_dict:
            return
        self.session.cookies.clear()
        for name, value in self.current_cookies_dict.items():

            self.session.cookies.set(name, value, domain='.shopee.tw')

    def add_random_delay(self, min_sec=1, max_sec=3):
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)

    def get_product_detail(self, item_id, shop_id, detail_level=0, tz_offset_minutes=60, max_retries=3):
        request_start_time = time.time()
        self.total_requests += 1

        api_url = f"https://shopee.tw/api/v4/pdp/get_pc?item_id={item_id}&shop_id={shop_id}&tz_offset_minutes={tz_offset_minutes}&detail_level={detail_level}"


        product_referer = f"https://shopee.tw/product-i.{shop_id}.{item_id}"

        self.session.headers.update({"Referer": product_referer})

        retries = 0
        while retries < max_retries:
            current_proxy = self.get_next_proxy() if self.proxies else None
            if current_proxy:
                self.session.proxies = current_proxy

            self.add_random_delay(2, 4)

            try:
                response = self.session.get(api_url)
                if response.status_code == 200:
                    self.success_count += 1
                    self.current_cookie_failures = 0
                    try:
                        data = response.json()
                        request_time = time.time() - request_start_time
                        self.request_times.append(request_time)
                        return data
                    except json.JSONDecodeError:
                        self.failure_count += 1
                else:
                    self.failure_count += 1
                    self.current_cookie_failures += 1
                    print(f"Failed with status code: {response.status_code}")
                    if self.current_cookie_failures >= self.max_cookie_failures:
                        if self.get_next_cookie():
                            print(f"Switching to next cookie after {self.current_cookie_failures} failures")
                        else:
                            print("No more cookies available")
            except requests.exceptions.RequestException as e:
                self.failure_count += 1
                self.current_cookie_failures += 1
                print(f"Request exception: {e}")
                if self.current_cookie_failures >= self.max_cookie_failures:
                    if self.get_next_cookie():
                        print(f"Switching to next cookie after connection error")
                    else:
                        print("No more cookies available")
            retries += 1

        return None

    def save_product_detail(self, item_id, shop_id, filename=None):
        if filename is None:
            filename = f"product_{item_id}_{shop_id}.json"
        product_data = self.get_product_detail(item_id, shop_id)
        if product_data:
            print(product_data)
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(product_data, f, ensure_ascii=False, indent=2)
            return True
        else:
            return False


    def get_account_info(self):
        api_url = "https://shopee.tw/api/v4/account/basic/get_account_info"

        try:
            response = self.session.get(api_url)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Failed to get account info: HTTP {response.status_code}")
                return None
        except Exception as e:
            print(f"Error getting account info: {e}")
            return None


def process_products_parallel(product_list, max_workers=5, cookies_dir="cookies", proxies_file="proxies.txt",
                              output_dir="results"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    results = []
    product_queue = []

    for i, (item_id, shop_id) in enumerate(product_list):
        product_queue.append((i, item_id, shop_id))


    total_products = len(product_queue)
    progress_bar = tqdm(total=total_products, desc="Processing products")

    def process_product(worker_id):
        worker_results = []
        scraper = ShopeeTWProductScraper(cookies_dir=cookies_dir, proxies_file=proxies_file)

        account_info = scraper.get_account_info()
        if account_info and 'data' in account_info:
            print(
                f"Worker {worker_id} authenticated as user: {account_info.get('data', {}).get('username', 'Unknown')}")

        while product_queue:
            try:

                product_id, item_id, shop_id = product_queue.pop(0)


                progress_bar.set_description(f"Processing product {item_id}_{shop_id}")

                filename = os.path.join(output_dir, f"product_{item_id}_{shop_id}.json")
                success = scraper.save_product_detail(item_id, shop_id, filename)


                worker_results.append((item_id, shop_id, success))
                progress_bar.update(1)


                status = "Success" if success else "Failed"
                print(f"Product {item_id}_{shop_id}: {status}")

            except IndexError:

                break
            except Exception as e:
                print(f"Error processing product: {e}")
                progress_bar.update(1)

        return worker_results

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:

        futures = [executor.submit(process_product, i) for i in range(max_workers)]


        all_results = []
        for future in concurrent.futures.as_completed(futures):
            try:
                worker_results = future.result()
                all_results.extend(worker_results)
            except Exception as e:
                print(f"Worker failed: {e}")

    progress_bar.close()

    success_count = sum(1 for _, _, success in all_results if success)
    print(
        f"Processed {len(all_results)} products. Success: {success_count}, Failed: {len(all_results) - success_count}")

    return all_results




def get_items_from_xlsx(input_file):

    try:
        df = pd.read_excel(input_file)


        if df.empty:
            print("The Excel file is empty")
            return []

        urls = df.iloc[:, 0].tolist()

        products = []
        pattern = r"i\.(\d+)\.(\d+)"

        for url in urls:
            if not isinstance(url, str):
                continue


            url = url.replace("**", "").replace("**", "")

            matches = re.findall(pattern, url)

            for shop_id, item_id in matches:
                products.append((item_id, shop_id))

        print(f"Extracted {len(products)} products from the Excel file")
        return products

    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return []


if __name__ == "__main__":

    test_products = [(9368269078, 327985547)]

    results = process_products_parallel(
        product_list=test_products,  # Use test products instead of Excel file
        max_workers=1,
        cookies_dir="cookies",
        proxies_file="proxies.txt",
        output_dir="results_tw"
    )

    # Alternatively, read from Excel:
    # results = process_products_parallel(
    #     product_list=get_items_from_xlsx("items_for_test.xlsx"),
    #     max_workers=1,
    #     cookies_dir="cookies",
    #     proxies_file="proxies.txt",
    #     output_dir="results_tw"
    # )