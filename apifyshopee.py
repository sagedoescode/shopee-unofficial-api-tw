from apify_client import ApifyClient
import re
import json
import csv
import os


# Function to extract shop_id and item_id from product URL
def extract_ids(url):
    pattern = r"-i\.(\d+)\.(\d+)"
    result = re.search(pattern, url)
    if result:
        shop_id, item_id = result.groups()
        return shop_id, item_id
    else:
        raise ValueError("Could not extract shop_id and item_id from URL.")


# Initialize the ApifyClient with your token
client = ApifyClient("apify_api_x7e5BqDKPhrM7M4AwtaaTNEI62rXJ61VDXi1")

# Path to CSV file with links
links_path = r"C:\Users\Administrator\Documents\GitHub\shopee\links_shopee.csv"

# CSV files to save the results and errors
output_file = "shopee_products.csv"
error_file = "shopee_failed_links.csv"

# Create or prepare output CSV files
fieldnames = ['shop_id', 'item_id', 'title', 'description', 'price', 'url']

# Check if output file exists and has content
if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
    # Create new file with headers
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames,
                                quoting=csv.QUOTE_MINIMAL,
                                doublequote=True)
        writer.writeheader()

# Check if error file exists and has content
if not os.path.exists(error_file) or os.path.getsize(error_file) == 0:
    # Create new file with headers
    with open(error_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['url', 'error_message'])

# Check if the links file exists
if not os.path.exists(links_path):
    print(f"Error: File not found at {links_path}")
    exit()

# Read all URLs from CSV file
urls = []
with open(links_path, 'r', encoding='utf-8') as file:
    csv_reader = csv.reader(file)
    for row in csv_reader:
        if row and row[0].strip():
            urls.append(row[0].strip())

print(f"Found {len(urls)} URLs to process")

# Lists to keep track of success and failure counts
successful_products = 0
failed_products = 0

# Process each URL
for product_url in urls:
    print(f"Processing: {product_url}")

    try:
        shop_id, item_id = extract_ids(product_url)
    except ValueError as e:
        print(f"Error: {e} URL: {product_url}")
        # Save the failed URL to error file - always append, even if duplicate
        with open(error_file, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([product_url, str(e)])
        failed_products += 1
        continue

    # Build the Shopee API URL
    api_url = f"https://shopee.tw/api/v4/pdp/get_rw?item_id={item_id}&shop_id={shop_id}"

    # Prepare the input for the Actor with the GET request to the API
    run_input = {
        "requests": [
            {
                "url": api_url,
                "method": "GET"
            }
        ]
    }

    try:
        # Run the Actor and wait for the result
        run = client.actor("fBTzvpGyXkGAU2wge").call(run_input=run_input)

        # Retrieve the first item from the returned dataset
        product = None
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            product = item
            break

        if not product or not product.get("data") or not product.get("data", {}).get("item"):
            error_msg = "No results found."
            print(error_msg)
            # Save the failed URL to error file - always append, even if duplicate
            with open(error_file, 'a', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow([product_url, error_msg])
            failed_products += 1
            continue

        # Extract product data
        data = product.get("data", {})
        item_info = data.get("item", {})

        # Get product information
        product_title = item_info.get("title", "Title not available")
        product_description = item_info.get("description", "Description not available")

        raw_price = item_info.get("price", None)
        product_price = f"{int(raw_price) / 100}" if raw_price is not None else "Price not available"

        # Clean the description - remove newlines to ensure it stays on one line
        product_description = product_description.replace('\n', ' ').replace('\r', '')
        product_title = product_title.replace('\n', ' ').replace('\r', '')

        # Print product information
        print(f"Title: {product_title}")
        print(f"Price: {product_price}")

        # Save data to CSV file - append mode - always add, even if duplicate
        with open(output_file, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames,
                                    quoting=csv.QUOTE_MINIMAL,
                                    doublequote=True)
            writer.writerow({
                'shop_id': shop_id,
                'item_id': item_id,
                'title': product_title,
                'description': product_description,
                'price': product_price,
                'url': product_url
            })

        print(f"Product data saved: {product_title}")
        print("-" * 50)
        successful_products += 1

    except Exception as e:
        error_msg = str(e)
        print(f"Error processing {product_url}: {error_msg}")
        # Save the failed URL to error file - always append, even if duplicate
        with open(error_file, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([product_url, error_msg])
        failed_products += 1
        continue

print(f"Processing complete!")
print(f"Successful products: {successful_products}")
print(f"Failed products: {failed_products}")
print(f"Successful products saved to: {output_file}")
print(f"Failed links saved to: {error_file}")