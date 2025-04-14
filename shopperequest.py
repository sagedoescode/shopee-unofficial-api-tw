import requests
import json
import re
import time
import random
import argparse
import csv
from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup


class ShopeeScraper:
    def __init__(self):
        self.session = requests.Session()
        # Set a realistic user agent
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        self.session.headers.update({
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0"
        })

    def extract_ids_from_url(self, url):
        """Extract shop_id and item_id from various Shopee URL formats"""
        # Format 1: i.SHOP_ID.ITEM_ID
        pattern1 = r'i\.(\d+)\.(\d+)'
        match = re.search(pattern1, url)
        if match:
            return match.group(1), match.group(2)

        # Format 2: /product/SHOP_ID/ITEM_ID
        pattern2 = r'/product/(\d+)/(\d+)'
        match = re.search(pattern2, url)
        if match:
            return match.group(1), match.group(2)

        # Format 3: ?sp_atk=XXXX&xptdk=XXXX&itemid=ITEM_ID&shopid=SHOP_ID
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        if 'itemid' in query_params and 'shopid' in query_params:
            return query_params['shopid'][0], query_params['itemid'][0]

        raise ValueError("Could not extract shop_id and item_id from URL. Please check the URL format.")

    def get_product_page(self, url):
        """Fetch the product page HTML"""
        # First visit the main site to get cookies
        self.session.get("https://shopee.tw/")

        # Add some delay to mimic human behavior
        time.sleep(random.uniform(1, 2))

        # Now visit the product page
        self.session.headers.update({"Referer": "https://shopee.tw/"})
        response = self.session.get(url)

        if response.status_code != 200:
            raise Exception(f"Failed to fetch the product page. Status code: {response.status_code}")

        return response.text

    def extract_data_from_html(self, html):
        """Extract the product data from the HTML"""
        # Look for the data embedded in the HTML as JSON
        soup = BeautifulSoup(html, 'html.parser')

        # Find all script tags
        scripts = soup.find_all('script')

        product_data = None
        for script in scripts:
            if script.string and "__INITIAL_STATE__" in script.string:
                # Extract the JSON data from the script
                match = re.search(r'__INITIAL_STATE__\s*=\s*({.*?});', script.string, re.DOTALL)
                if match:
                    try:
                        data_json = match.group(1)
                        data = json.loads(data_json)
                        if "productDetail" in data and "data" in data["productDetail"]:
                            product_data = data["productDetail"]["data"]
                            break
                    except json.JSONDecodeError:
                        continue

        if not product_data:
            # Alternative method: try to find itemsprop metadata
            meta_tags = soup.find_all('meta')
            product_data = {}

            for tag in meta_tags:
                if tag.get('property') == 'og:title':
                    product_data['title'] = tag.get('content')
                elif tag.get('property') == 'og:description':
                    product_data['description'] = tag.get('content')
                elif tag.get('property') == 'og:image':
                    product_data['image'] = tag.get('content')
                elif tag.get('property') == 'og:price:amount':
                    product_data['price'] = tag.get('content')
                elif tag.get('property') == 'og:price:currency':
                    product_data['currency'] = tag.get('content')

        return product_data

    def api_connection_with_cookies(self, shop_id, item_id):
        """Try to access the API with cookies set from visiting the main site"""
        url = f"https://shopee.tw/api/v4/pdp/get_pc?item_id={item_id}&shop_id={shop_id}"

        # Set the referer to the product page to appear legitimate
        self.session.headers.update({
            "Referer": f"https://shopee.tw/product/{shop_id}/{item_id}",
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json"
        })

    def get_product_info(self, url):
        """
        Get product information from Shopee using multiple fallback methods
        """
        try:

            shop_id, item_id = self.extract_ids_from_url(url)
            print(f"Extracted shop_id: {shop_id}, item_id: {item_id}")

            self.api_connection_with_cookies(shop_id, item_id)

            print("Direct page scraping...")
            product_url = f"https://shopee.tw/product/{shop_id}/{item_id}"
            html = self.get_product_page(product_url)
            data = self.extract_data_from_html(html)

            if data:
                print("Successfully extracted data from HTML")
                return {"data": data}

            # If both methods fail
            raise Exception("Failed to extract product data from both API and HTML scraping")

        except Exception as e:
            print(f"Error: {str(e)}")
            return None


def display_product_info(data):
    """
    Display key product information in a readable format
    """
    if not data or "data" not in data:
        print("No product data found in the response")
        return

    product_data = data["data"]

    print("\n===== PRODUCT INFORMATION =====\n")

    # Basic information
    if "item_basic" in product_data:
        basic = product_data["item_basic"]
        print(f"Name: {basic.get('name', 'N/A')}")
        print(f"Description: {basic.get('description', 'N/A')[:100]}..." if len(
            basic.get('description', '')) > 100 else f"Description: {basic.get('description', 'N/A')}")

        # Convert price from Shopee format (in 100,000s) to regular format
        if 'price' in basic:
            price = basic['price']
            if price > 1000:  # Likely in Shopee's special format
                price = price / 100000
            print(f"Price: {price:.2f} TWD")

        print(f"Stock: {basic.get('stock', 'N/A')}")

        if 'item_rating' in basic and basic['item_rating']:
            print(f"Rating: {basic['item_rating'].get('rating_star', 'N/A'):.1f}")

        print(f"Sales: {basic.get('historical_sold', 'N/A')}")

        # Categories
        if 'categories' in product_data:
            categories = []
            for cat in product_data.get('categories', []):
                if 'display_name' in cat:
                    categories.append(cat['display_name'])
            if categories:
                print(f"Categories: {' > '.join(categories)}")

    # Alternative data format (from HTML scraping)
    elif "title" in product_data:
        print(f"Name: {product_data.get('title', 'N/A')}")
        print(f"Description: {product_data.get('description', 'N/A')}")
        print(f"Price: {product_data.get('price', 'N/A')} {product_data.get('currency', '')}")

    # Models/Variations
    if "tier_variations" in product_data:
        print("\n----- Variations -----")
        variations = product_data["tier_variations"]
        for i, var in enumerate(variations):
            print(f"\nVariation {i + 1}: {var.get('name', 'N/A')}")
            for j, option in enumerate(var.get('options', [])):
                print(f"  Option {j + 1}: {option}")

    # Models
    if "models" in product_data:
        print("\n----- Models -----")
        models = product_data["models"]
        for i, model in enumerate(models):
            print(f"\nModel {i + 1}:")
            print(f"  Model ID: {model.get('model_id', 'N/A')}")
            print(f"  Name: {model.get('name', 'N/A')}")

            # Convert price if needed
            if 'price' in model:
                price = model['price']
                if price > 1000:  # Likely in Shopee's special format
                    price = price / 100000
                print(f"  Price: {price:.2f} TWD")

            print(f"  Stock: {model.get('stock', 'N/A')}")


def save_to_file(data, filename="product_info.json"):
    """
    Save the data to a JSON file
    """
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"Data saved to {filename}")


def save_to_csv(data, filename="product_info.csv", url=""):
    """
    Save product name, description and URL to a CSV file for Google Sheets
    """
    if not data or "data" not in data:
        print("No product data to save to CSV")
        return

    product_data = data["data"]

    # Extract name and description
    product_name = "N/A"
    product_description = "N/A"

    if "item_basic" in product_data:
        basic = product_data["item_basic"]
        product_name = basic.get('name', 'N/A')
        product_description = basic.get('description', 'N/A')
    elif "title" in product_data:
        product_name = product_data.get('title', 'N/A')
        product_description = product_data.get('description', 'N/A')

    # Clean up description - remove newlines to keep everything on one line
    product_description = product_description.replace('\n', ' ').replace('\r', ' ')

    # Write to CSV
    with open(filename, 'w', encoding='utf-8', newline='') as csvfile:
        csvwriter = csv.writer(csvfile)
        # Write header in English with URL as last column
        csvwriter.writerow(['Name', 'Description', 'URL'])
        # Write data with URL as last column
        csvwriter.writerow([product_name, product_description, url])

    print(f"CSV saved to {filename} - Ready for Google Sheets")


def main():
    parser = argparse.ArgumentParser(description='Scrape product information from Shopee')
    parser.add_argument('url', nargs='?', default="https://shopee.tw/---i.327985547.9368269078",
                        help='Shopee product URL')
    parser.add_argument('--output', '-o', default="product_info.json",
                        help='Output JSON file name')
    parser.add_argument('--csv', '-c', default="product_info.csv",
                        help='Output CSV file name')

    args = parser.parse_args()

    scraper = ShopeeScraper()
    data = scraper.get_product_info(args.url)

    if data:
        display_product_info(data)
        save_to_file(data, args.output)
        save_to_csv(data, args.csv, args.url)  # Salvar para CSV com URL
    else:
        print("Failed to retrieve product information.")


if __name__ == "__main__":
    main()