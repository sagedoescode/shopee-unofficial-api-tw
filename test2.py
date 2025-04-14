import asyncio
import aiohttp
import re
import json
import csv
import os
import time
from tqdm.asyncio import tqdm
import random

# Configurações
CONCURRENT_REQUESTS = 100  # Número de requisições concorrentes
MAX_REQUESTS_PER_SECOND = 20  # Limite de requisições por segundo
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.106 Safari/537.36"
]

# Path to CSV file with links
links_path = r"C:\Users\Administrator\Documents\GitHub\shopee\links_shopee.csv"

# CSV files to save the results and errors
output_file = "shopee_products_direct.csv"
error_file = "shopee_failed_links_direct.csv"

# Create or prepare output CSV files
fieldnames = ['shop_id', 'item_id', 'title', 'description', 'price', 'url']


# Function to extract shop_id and item_id from product URL
def extract_ids(url):
    pattern = r"-i\.(\d+)\.(\d+)"
    result = re.search(pattern, url)
    if result:
        shop_id, item_id = result.groups()
        return shop_id, item_id
    else:
        raise ValueError("Could not extract shop_id and item_id from URL.")


# Setup semaphore for rate limiting
async def setup_rate_limiter():
    return asyncio.Semaphore(CONCURRENT_REQUESTS)


# Setup files if they don't exist
def setup_files():
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


# Load URLs from CSV file
def load_urls():
    # Check if the links file exists
    if not os.path.exists(links_path):
        print(f"Error: File not found at {links_path}")
        return []

    # Read all URLs from CSV file
    urls = []
    with open(links_path, 'r', encoding='utf-8') as file:
        csv_reader = csv.reader(file)
        for row in csv_reader:
            if row and row[0].strip():
                urls.append(row[0].strip())

    print(f"Found {len(urls)} URLs to process")
    return urls


# Process a single product URL
async def process_product(session, url, semaphore, progress):
    async with semaphore:
        # Add a small delay to avoid hitting rate limits
        await asyncio.sleep(1 / MAX_REQUESTS_PER_SECOND)

        try:
            shop_id, item_id = extract_ids(url)
        except ValueError as e:
            progress.update(1)
            return {
                'success': False,
                'url': url,
                'error': str(e)
            }

        # Build the Shopee API URL
        api_url = f"https://shopee.tw/api/v4/pdp/get_rw?item_id={item_id}&shop_id={shop_id}"

        # Set random user agent for each request
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "application/json",
            "Referer": "https://shopee.tw/",
            "x-requested-with": "XMLHttpRequest"
        }

        # Add retry mechanism
        max_retries = 3
        for retry in range(max_retries):
            try:
                async with session.get(api_url, headers=headers, timeout=30) as response:
                    if response.status == 200:
                        data = await response.json()

                        if not data or not data.get("data") or not data.get("data", {}).get("item"):
                            progress.update(1)
                            return {
                                'success': False,
                                'url': url,
                                'error': "No results found."
                            }

                        # Extract product data
                        item_info = data.get("data", {}).get("item", {})

                        # Get product information
                        product_title = item_info.get("title", "Title not available")
                        product_description = item_info.get("description", "Description not available")

                        raw_price = item_info.get("price", None)
                        product_price = f"{int(raw_price) / 100}" if raw_price is not None else "Price not available"

                        # Clean the description - remove newlines to ensure it stays on one line
                        product_description = product_description.replace('\n', ' ').replace('\r', '')
                        product_title = product_title.replace('\n', ' ').replace('\r', '')

                        progress.update(1)
                        return {
                            'success': True,
                            'data': {
                                'shop_id': shop_id,
                                'item_id': item_id,
                                'title': product_title,
                                'description': product_description,
                                'price': product_price,
                                'url': url
                            }
                        }
                    elif response.status == 429:  # Too Many Requests
                        # Exponential backoff
                        await asyncio.sleep(2 ** retry)
                        continue
                    else:
                        progress.update(1)
                        return {
                            'success': False,
                            'url': url,
                            'error': f"HTTP Error: {response.status}"
                        }
            except asyncio.TimeoutError:
                if retry < max_retries - 1:
                    await asyncio.sleep(2 ** retry)
                    continue
                else:
                    progress.update(1)
                    return {
                        'success': False,
                        'url': url,
                        'error': "Timeout error"
                    }
            except Exception as e:
                if retry < max_retries - 1:
                    await asyncio.sleep(2 ** retry)
                    continue
                else:
                    progress.update(1)
                    return {
                        'success': False,
                        'url': url,
                        'error': str(e)
                    }

        # If we've exhausted all retries
        progress.update(1)
        return {
            'success': False,
            'url': url,
            'error': "Max retries exceeded"
        }


# Save results to CSV files
async def save_result(result):
    if result['success']:
        # Save successful result to output file
        with open(output_file, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames,
                                    quoting=csv.QUOTE_MINIMAL,
                                    doublequote=True)
            writer.writerow(result['data'])
        return True
    else:
        # Save failed URL to error file
        with open(error_file, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([result['url'], result['error']])
        return False


# Process URLs in batches to avoid memory issues
async def process_urls_in_batches(urls, batch_size=1000):
    total_urls = len(urls)
    successful_products = 0
    failed_products = 0

    # Process in batches
    for i in range(0, total_urls, batch_size):
        end = min(i + batch_size, total_urls)
        batch_urls = urls[i:end]

        print(
            f"Processing batch {i // batch_size + 1}/{(total_urls + batch_size - 1) // batch_size} ({len(batch_urls)} URLs)")

        # Create a TCP connector with limits
        connector = aiohttp.TCPConnector(limit=CONCURRENT_REQUESTS, ssl=False)

        # Use aiohttp client session
        async with aiohttp.ClientSession(connector=connector) as session:
            # Setup rate limiter
            semaphore = await setup_rate_limiter()

            # Create progress bar
            progress = tqdm(total=len(batch_urls), desc=f"Batch {i // batch_size + 1}")

            # Create tasks for all URLs in the batch
            tasks = [process_product(session, url, semaphore, progress) for url in batch_urls]

            # Process results as they complete
            for result in asyncio.as_completed(tasks):
                result_data = await result
                success = await save_result(result_data)

                if success:
                    successful_products += 1
                else:
                    failed_products += 1

            progress.close()

        # Print batch summary
        print(f"Batch {i // batch_size + 1} complete: {successful_products} successful, {failed_products} failed")

    return successful_products, failed_products


# Main function
async def main():
    start_time = time.time()

    # Setup output files
    setup_files()

    # Load URLs from CSV
    urls = load_urls()
    if not urls:
        print("No URLs to process. Exiting.")
        return

    # Process URLs in batches
    successful_products, failed_products = await process_urls_in_batches(urls)

    # Calculate elapsed time
    elapsed_time = time.time() - start_time
    hours, remainder = divmod(elapsed_time, 3600)
    minutes, seconds = divmod(remainder, 60)

    # Print summary
    print("\nProcessing complete!")
    print(f"Elapsed time: {int(hours)}h {int(minutes)}m {int(seconds)}s")
    print(f"Successful products: {successful_products}")
    print(f"Failed products: {failed_products}")
    print(f"Processing rate: {successful_products / (elapsed_time / 3600):.2f} products/hour")
    print(f"Estimated time for 1 million products: {1000000 / (successful_products / elapsed_time / 3600):.2f} hours")
    print(f"Successful products saved to: {output_file}")
    print(f"Failed links saved to: {error_file}")


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())