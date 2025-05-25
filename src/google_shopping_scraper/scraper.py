"""
    Module for scraping Google Shopping.
"""

import logging
import time
import random
import re
import base64
import os
import json
from urllib.parse import urlparse

from typing import List

from pydantic import ValidationError
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager

from google_shopping_scraper.conf import google_shopping_scraper_settings
from google_shopping_scraper.models import ShoppingItem


logging.getLogger("WDM").setLevel(logging.ERROR)


class ConsentFormAcceptError(BaseException):
    message = "Unable to accept Google consent form."


class DriverInitializationError(BaseException):
    message = "Unable to initialize Chrome webdriver for scraping."


class DriverGetShoppingDataError(BaseException):
    message = "Unable to get Google Shopping data with Chrome webdriver."


class GoogleShoppingScraper:
    """Class for scraping Google Shopping"""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger if logger else logging.getLogger(__name__)
        self._consent_button_xpath = "/html/body/c-wiz/div/div/div/div[2]/div[1]/div[3]/div[1]/div[1]/form[2]/div/div/button/span"
        self._last_request_time = 0
        
        # Create debug directory if it doesn't exist
        self.debug_dir = "debug"
        if not os.path.exists(self.debug_dir):
            os.makedirs(self.debug_dir)
            self._logger.info(f"Created debug directory: {self.debug_dir}")

    def _add_random_delay(self, min_delay: float = 1.0, max_delay: float = 3.0) -> None:
        """Adds a random delay to avoid being detected as a bot"""
        current_time = time.time()
        time_since_last_request = current_time - self._last_request_time
        
        # Ensure minimum time between requests
        min_time_between_requests = 2.0
        if time_since_last_request < min_time_between_requests:
            additional_delay = min_time_between_requests - time_since_last_request
            time.sleep(additional_delay)
        
        # Add random delay
        delay = random.uniform(min_delay, max_delay)
        self._logger.debug(f"Adding random delay of {delay:.2f} seconds")
        time.sleep(delay)
        
        self._last_request_time = time.time()

    def _init_chrome_driver(self, proxy: str = None) -> webdriver.Chrome:
        """Initializes Chrome webdriver with stealth options"""
        chrome_options = Options()
        
        # Basic stealth options
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        # Re-enabled images for better page rendering
        # chrome_options.add_argument("--disable-images")  # Commented out to allow images
        # Removed --disable-javascript as it breaks Google Shopping functionality
        
        # Window and display options
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--start-maximized")
        
        # Network and security options
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--disable-ipc-flooding-protection")
        
        # Clear browser data for fresh session
        chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_argument("--disable-backgrounding-occluded-windows")
        chrome_options.add_argument("--disable-renderer-backgrounding")
        chrome_options.add_argument("--disable-features=TranslateUI")
        chrome_options.add_argument("--disable-default-apps")
        chrome_options.add_argument("--no-first-run")
        chrome_options.add_argument("--no-default-browser-check")
        
        # Proxy support
        if proxy:
            chrome_options.add_argument(f"--proxy-server={proxy}")
            self._logger.info(f"Using proxy: {proxy}")
        
        # User agent rotation - use a recent, common user agent
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]
        chrome_options.add_argument(f"--user-agent={random.choice(user_agents)}")
        
        # Disable automation flags and features
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Additional prefs to appear more human-like
        prefs = {
            "profile.default_content_setting_values": {
                "notifications": 2,
                "geolocation": 2,
            },
            "profile.default_content_settings.popups": 0,
            # Re-enabled images for better page rendering
            # "profile.managed_default_content_settings.images": 2,  # Commented out to allow images
            "profile.password_manager_enabled": False,
            "credentials_enable_service": False,
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Execute stealth scripts
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})")
        driver.execute_script("Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})")
        driver.execute_script("Object.defineProperty(navigator, 'permissions', {get: () => ({query: () => Promise.resolve({state: 'granted'})})})")
        
        # Set a more realistic viewport
        driver.execute_script("Object.defineProperty(screen, 'width', {get: () => 1920})")
        driver.execute_script("Object.defineProperty(screen, 'height', {get: () => 1080})")
        
        # Additional stealth measures
        driver.execute_script("Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 4})")
        driver.execute_script("Object.defineProperty(navigator, 'deviceMemory', {get: () => 8})")
        
        return driver

    def _click_consent_button(self, driver: webdriver.Chrome, query: str) -> None:
        """Clicks google consent form with selenium Chrome webdriver using human-like behavior"""
        self._logger.info("Accepting consent form..")
        url = google_shopping_scraper_settings.get_shopping_url(query)
        try:
            driver.get(url)
            
            # Random delay to simulate human reading time
            time.sleep(random.uniform(2, 4))
            
            # Try to find and click consent button with human-like behavior
            try:
                consent_button = driver.find_element(
                    By.XPATH,
                    self._consent_button_xpath,
                )
                
                # Scroll to the button if needed
                driver.execute_script("arguments[0].scrollIntoView(true);", consent_button)
                time.sleep(random.uniform(0.5, 1.5))
                
                # Move mouse to button and click (more human-like)
                actions = ActionChains(driver)
                actions.move_to_element(consent_button)
                time.sleep(random.uniform(0.2, 0.8))
                actions.click()
                actions.perform()
                
                self._logger.info("Consent form accepted successfully")
                
            except NoSuchElementException:
                self._logger.warning("Consent form button not found - may not be required")
                
        except Exception as e:
            raise ConsentFormAcceptError from e

        # Random delay after consent
        time.sleep(random.uniform(2, 4))

    def _get_data_from_item_div(self, div) -> ShoppingItem:
        """Retrieves shopping item data from a div element and returns it as a ShoppingItem object."""
        try:
            # Extract title from the known structure
            title = None
            try:
                title_element = div.find_element(By.CSS_SELECTOR, ".gkQHve.SsM98d.RmEs5b")
                title = title_element.text.strip()
            except:
                return None
            
            if not title:
                return None

            # Extract price from the known structure
            price = None
            try:
                price_element = div.find_element(By.CSS_SELECTOR, ".lmQWe")
                # Try text first
                price_text = price_element.text.strip()
                if price_text:
                    price = price_text
                else:
                    # Try aria-label
                    aria_label = price_element.get_attribute("aria-label")
                    if aria_label and "price" in aria_label.lower():
                        # Extract price from aria-label like "Current price: ₹24.50"
                        price_match = re.search(r'[₹$€£¥]\s*[\d,]+\.?\d*', aria_label)
                        if price_match:
                            price = price_match.group()
            except:
                return None

            if not price:
                return None

            # Extract image URL (no local saving)
            image_url = None
            try:
                # Small delay to allow images to load
                time.sleep(random.uniform(0.1, 0.3))
                
                # Look for images in multiple ways
                all_imgs = []
                
                # Strategy 1: Images in current container
                try:
                    imgs = div.find_elements(By.XPATH, ".//img")
                    all_imgs.extend(imgs)
                except:
                    pass
                
                # Strategy 2: Images in sibling containers
                try:
                    imgs = div.find_elements(By.XPATH, "./preceding-sibling::*/descendant::img | ./following-sibling::*/descendant::img")
                    all_imgs.extend(imgs)
                except:
                    pass
                
                # Strategy 3: Images in parent container
                try:
                    parent = div.find_element(By.XPATH, "./..")
                    imgs = parent.find_elements(By.XPATH, ".//img")
                    all_imgs.extend(imgs)
                except:
                    pass
                
                # Priority 1: Base64 images (often highest quality)
                for img in all_imgs:
                    src = img.get_attribute("src")
                    if src and src.startswith("data:image/"):
                        image_url = src
                        break
                
                # Priority 2: Google Shopping encrypted URLs
                if not image_url:
                    for img in all_imgs:
                        src = img.get_attribute("src")
                        if src and "encrypted-tbn" in src and "shopping?q=tbn:" in src:
                            image_url = src
                            break
                
                # Priority 3: Any encrypted-tbn URL
                if not image_url:
                    for img in all_imgs:
                        src = img.get_attribute("src")
                        if src and "encrypted-tbn" in src:
                            image_url = src
                            break
                        
                        # Also check data-src for lazy loaded
                        data_src = img.get_attribute("data-src")
                        if data_src and "encrypted-tbn" in data_src:
                            image_url = data_src
                            break
                
                # Priority 4: Any reasonable HTTP image URL
                if not image_url:
                    for img in all_imgs:
                        src = img.get_attribute("src")
                        if src and src.startswith("http") and not any(x in src.lower() for x in ["favicon", "icon", "logo"]):
                            image_url = src
                            break
                        
            except Exception as e:
                self._logger.debug(f"Error extracting image: {e}")
                pass

            # Extract delivery info - optional
            delivery_price = "N/A"
            try:
                delivery_element = div.find_element(By.CSS_SELECTOR, ".ybnj7e")
                delivery_price = delivery_element.text.strip()
            except:
                pass

            # Extract review rating - optional
            review = None
            try:
                review_element = div.find_element(By.CSS_SELECTOR, ".yi40Hd")
                review_text = review_element.text.strip()
                if review_text and review_text.replace('.', '').isdigit():
                    review = review_text
            except:
                pass

            # Extract URL - try to find a link
            url = "N/A"
            try:
                link_element = div.find_element(By.CSS_SELECTOR, "a[href]")
                url = link_element.get_attribute("href")
            except:
                pass

            return ShoppingItem(
                price=price,
                delivery_price=delivery_price,
                title=title,
                review=review,
                url=url,
                image_url=image_url,
                saved_image_path=None,
            )

        except Exception as e:
            self._logger.debug(f"Error extracting data from item: {e}")
            return None

    def _save_html_for_debug(self, driver: webdriver.Chrome, query: str) -> None:
        """Saves the current page HTML to a file for debugging purposes."""
        try:
            html_content = driver.page_source
            filename = f"debug_google_shopping_{query.replace(' ', '_')}.html"
            filepath = os.path.join(self.debug_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
            self._logger.info(f"HTML content saved to {filepath} for debugging")
            
            # Check if we hit a CAPTCHA
            if "recaptcha" in html_content.lower() or "unusual traffic" in html_content.lower():
                self._logger.warning("CAPTCHA detected! Google is blocking automated requests.")
                self._logger.info("You may need to:")
                self._logger.info("1. Wait some time before trying again")
                self._logger.info("2. Use a VPN or different IP address")
                self._logger.info("3. Solve the CAPTCHA manually in the browser window")
                
        except Exception as e:
            self._logger.error(f"Failed to save HTML for debugging: {e}")

    def _get_items_for_query(self, driver: webdriver.Chrome, query: str = "") -> List[ShoppingItem]:
        """Retrieves shopping item data from a Google Shopping page with human-like behavior."""
        self._logger.info("Scraping Google shopping page..")
        
        # Random delay to simulate human browsing
        time.sleep(random.uniform(3, 7))

        # Save HTML for debugging
        self._save_html_for_debug(driver, query)

        # Smart scrolling - only scroll until we find enough products
        item_data = self._smart_scroll_and_extract(driver)
        
        if item_data:
            self._logger.info(f"Successfully extracted {len(item_data)} product items")
            return item_data

        # Fallback: if smart scrolling didn't work, try the old method
        self._logger.warning("Smart scrolling didn't find products, trying fallback method")
        
        # Find product containers - look for divs that contain both title and price
        items = []
        try:
            # Find all elements with titles first
            title_elements = driver.find_elements(By.CSS_SELECTOR, ".gkQHve.SsM98d.RmEs5b")
            self._logger.info(f"Found {len(title_elements)} title elements")
            
            # For each title, find its parent container that should contain the full product info
            for title_elem in title_elements:
                try:
                    # Navigate up to find the container that has both title and price
                    current = title_elem
                    for _ in range(5):  # Look up to 5 levels up
                        parent = current.find_element(By.XPATH, "./..")
                        try:
                            # Check if this parent contains a price element
                            parent.find_element(By.CSS_SELECTOR, ".lmQWe")
                            # If we found both title and price in this container, use it
                            if parent not in items:
                                items.append(parent)
                            break
                        except:
                            current = parent
                            continue
                except:
                    continue
                    
        except Exception as e:
            self._logger.warning(f"Error finding items: {e}")
            return []
        
        if not items:
            self._logger.warning("No product containers found")
            return []

        # Limit the number of items to process
        max_items = min(15, len(items))  # Process max 15 items to find top 5
        items = items[:max_items]
        self._logger.info(f"Processing {len(items)} product containers")

        item_data = []
        processed_count = 0
        
        for i, container in enumerate(items):
            try:
                # Random delay between processing items (shorter delays)
                if i > 0:
                    time.sleep(random.uniform(0.05, 0.2))
                
                item = self._get_data_from_item_div(container)
                if item:
                    item_data.append(item)
                    processed_count += 1
                    self._logger.debug(f"Successfully processed item {processed_count}: {item.title[:50]}...")
                
                # Stop if we have enough items - limit to top 5
                if len(item_data) >= 5:  # Limit to 5 actual products
                    self._logger.info(f"Reached limit of 5 products, stopping processing")
                    break
                
            except ValidationError:
                self._logger.error("Data missing from shopping item div. Skipping..")
                continue
            except Exception as e:
                self._logger.warning(f"Error processing item {i}: {e}")
                continue

        self._logger.info(f"Successfully extracted {len(item_data)} product items")
        return item_data

    def _is_product_item(self, div) -> bool:
        """Check if the div element contains a product item"""
        try:
            # Must have both title and price to be considered a product
            has_title = False
            has_price = False
            
            # Check for title
            title_selectors = [".gkQHve", ".tAxDx", ".sh-dgr__title"]
            for selector in title_selectors:
                try:
                    title_elem = div.find_element(By.CSS_SELECTOR, selector)
                    if title_elem.text.strip():
                        has_title = True
                        break
                except:
                    continue
            
            # Check for price
            price_selectors = [".lmQWe", ".XrAfOe", ".FG68Ac", "[aria-label*='Current price']"]
            for selector in price_selectors:
                try:
                    price_elem = div.find_element(By.CSS_SELECTOR, selector)
                    price_text = price_elem.text.strip()
                    aria_label = price_elem.get_attribute("aria-label") or ""
                    
                    # Check if it contains price indicators
                    if (price_text and any(symbol in price_text for symbol in ['₹', '$', '€', '£', '¥'])) or \
                       ("price" in aria_label.lower()):
                        has_price = True
                        break
                except:
                    continue
            
            # Must have both title and price
            result = has_title and has_price
            if result:
                self._logger.debug(f"Valid product item found with title and price")
            
            return result
            
        except Exception as e:
            self._logger.debug(f"Error checking if item is product: {e}")
            return False

    def _smart_scroll_and_extract(self, driver: webdriver.Chrome) -> List[ShoppingItem]:
        """Smart scrolling that stops when we find enough products"""
        try:
            item_data = []
            viewport_height = driver.execute_script("return window.innerHeight")
            current_position = 0
            scroll_increment = viewport_height // 3
            max_scrolls = 10  # Limit scrolling attempts
            scroll_count = 0
            
            self._logger.info("Starting smart scrolling to find products...")
            
            while len(item_data) < 5 and scroll_count < max_scrolls:
                # Check for products at current position
                try:
                    title_elements = driver.find_elements(By.CSS_SELECTOR, ".gkQHve.SsM98d.RmEs5b")
                    
                    # Process visible products
                    for title_elem in title_elements:
                        if len(item_data) >= 5:
                            break
                            
                        try:
                            # Navigate up to find the container that has both title and price
                            current = title_elem
                            container = None
                            
                            for _ in range(5):  # Look up to 5 levels up
                                parent = current.find_element(By.XPATH, "./..")
                                try:
                                    # Check if this parent contains a price element
                                    parent.find_element(By.CSS_SELECTOR, ".lmQWe")
                                    container = parent
                                    break
                                except:
                                    current = parent
                                    continue
                            
                            if container:
                                # Check if we already processed this container
                                container_id = container.get_attribute("data-hveid") or str(hash(container.text[:100]))
                                processed_ids = [getattr(item, '_container_id', None) for item in item_data]
                                
                                if container_id not in processed_ids:
                                    item = self._get_data_from_item_div(container)
                                    if item:
                                        item._container_id = container_id  # Mark as processed
                                        item_data.append(item)
                                        self._logger.info(f"Found product {len(item_data)}/5: {item.title[:50]}...")
                                        
                                        # Small delay between processing
                                        time.sleep(random.uniform(0.1, 0.3))
                        except:
                            continue
                
                except Exception as e:
                    self._logger.debug(f"Error checking products at position {current_position}: {e}")
                
                # If we have enough products, stop scrolling
                if len(item_data) >= 5:
                    self._logger.info("Found 5 products, stopping smart scroll")
                    break
                
                # Scroll down a bit more
                scroll_amount = random.randint(scroll_increment - 50, scroll_increment + 50)
                current_position += scroll_amount
                driver.execute_script(f"window.scrollTo(0, {current_position});")
                
                # Random pause between scrolls
                time.sleep(random.uniform(0.8, 1.5))
                scroll_count += 1
                
                # Check if we've reached the bottom
                page_height = driver.execute_script("return document.body.scrollHeight")
                if current_position >= page_height:
                    self._logger.info("Reached bottom of page")
                    break
            
            if len(item_data) > 0:
                self._logger.info(f"Smart scrolling found {len(item_data)} products after {scroll_count} scrolls")
            else:
                self._logger.warning(f"Smart scrolling found no products after {scroll_count} scrolls")
            
            return item_data
            
        except Exception as e:
            self._logger.warning(f"Error during smart scrolling: {e}")
            return []

    def _simulate_human_scrolling(self, driver: webdriver.Chrome) -> None:
        """Simulates human-like scrolling behavior (fallback method)"""
        try:
            # Get page height
            page_height = driver.execute_script("return document.body.scrollHeight")
            viewport_height = driver.execute_script("return window.innerHeight")
            
            # Scroll down in chunks like a human would
            current_position = 0
            scroll_increment = viewport_height // 3
            
            while current_position < page_height:
                # Random scroll amount
                scroll_amount = random.randint(scroll_increment - 50, scroll_increment + 50)
                current_position += scroll_amount
                
                driver.execute_script(f"window.scrollTo(0, {current_position});")
                
                # Random pause between scrolls
                time.sleep(random.uniform(0.5, 1.5))
                
                # Update page height in case content loaded dynamically
                page_height = driver.execute_script("return document.body.scrollHeight")
                
                # Break if we've scrolled past the page
                if current_position >= page_height:
                    break
            
            # Scroll back to top
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(random.uniform(1, 2))
            
        except Exception as e:
            self._logger.warning(f"Error during scrolling simulation: {e}")



    def get_shopping_data_for_query(self, query: str, max_retries: int = 3, proxy: str = None) -> List[ShoppingItem]:
        """
        Retrieves a list of shopping items in Google Shopping for a query with stealth measures.

        Args:
            query: The search query string
            max_retries: Maximum number of retry attempts if scraping fails
            proxy: Optional proxy server (format: "ip:port" or "protocol://ip:port")

        Returns:
            List[ShoppingItem]: A list of ShoppingItem objects.
        Raises:
            ConsentFormAcceptError: If the Google consent form cannot be accepted.
            DriverInitializationError: If the Chrome webdriver cannot be initialized.
            DriverGetShoppingDataError: If the shopping data cannot be scraped from the Google Shopping site.
        """
        self._logger.info(f"Retrieving shopping items for query '{query}' with stealth measures..")
        
        for attempt in range(max_retries):
            try:
                # Add delay before each attempt
                if attempt > 0:
                    self._logger.info(f"Retry attempt {attempt + 1}/{max_retries}")
                    self._add_random_delay(5.0, 10.0)  # Longer delay for retries
                else:
                    self._add_random_delay(1.0, 3.0)
                
                driver = self._init_chrome_driver(proxy=proxy)
                
                try:
                    self._click_consent_button(driver, query)
                    items = self._get_items_for_query(driver, query)
                    
                    if items:
                        self._logger.info(f"Successfully scraped {len(items)} items")
                        return items
                    else:
                        self._logger.warning("No items found, this might indicate detection")
                        if attempt < max_retries - 1:
                            continue
                        
                except Exception as e:
                    self._logger.error(f"Error during scraping attempt {attempt + 1}: {e}")
                    if attempt < max_retries - 1:
                        continue
                    raise DriverGetShoppingDataError from e
                finally:
                    try:
                        driver.quit()  # Use quit() instead of close() for cleaner shutdown
                    except:
                        pass
                        
            except Exception as e:
                if attempt < max_retries - 1:
                    self._logger.warning(f"Attempt {attempt + 1} failed, retrying...")
                    continue
                else:
                    if "DriverInitializationError" in str(type(e)):
                        raise e
                    raise DriverInitializationError from e
        
        # If we get here, all attempts failed
        raise DriverGetShoppingDataError("All retry attempts failed")
