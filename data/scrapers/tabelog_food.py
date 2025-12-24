#!/usr/bin/env python3
"""
Tabelog Tokyo Scraper
Scrapes restaurant data from tabelog.com/en/tokyo and converts to unified POI schema.
"""

import requests
import json
import csv
import hashlib
import time
import random
import re
import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup
from urllib.parse import urljoin

class TabelogScraper:
    def __init__(self):
        self.base_url = "https://tabelog.com"
        self.tokyo_url = "https://tabelog.com/en/tokyo/"
        self.session = requests.Session()
        # Use realistic headers to avoid blocking
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,ja;q=0.8',
        })
        
        # Category mapping as per plan
        self.categories = {
            "Sushi": "rstLst/sushi/",
            "Ramen": "rstLst/ramen/",
            "Yakiniku": "rstLst/yakiniku/",
            "Izakaya": "rstLst/izakaya/",
            "Tempura": "rstLst/tempura/",
            "Udon": "rstLst/udon/", 
            "Soba": "rstLst/soba/",
            "Unagi": "rstLst/unagi/",
            "Curry": "rstLst/curry/",
            "Tonkatsu": "rstLst/tonkatsu/",
            "Cafe": "rstLst/cafe/",
            "Sweets": "rstLst/sweets/"
        }

    def generate_poi_id(self, url: str) -> str:
        """Generate unique ID from source URL"""
        return hashlib.md5(url.encode('utf-8')).hexdigest()[:12]

    def random_delay(self, min_seconds=2.0, max_seconds=5.0):
        """Random delay to be respectful and avoid blocking"""
        time.sleep(random.uniform(min_seconds, max_seconds))

    def clean_text(self, text: Optional[str]) -> str:
        """Clean whitespace and newlines"""
        if not text:
            return ""
        return " ".join(text.strip().split())

    def parse_rating(self, rating_str: str) -> float:
        """Parse rating string to float"""
        try:
            return float(rating_str)
        except (ValueError, TypeError):
            try:
                # Handle "3.52" logic if slightly malformed
                match = re.search(r'\d+\.\d+', str(rating_str))
                if match:
                    return float(match.group(0))
            except:
                pass
            return 0.0

    def parse_price(self, price_str: str) -> Optional[int]:
        """Normalize price range to 1-4 scale
        Tabelog usually shows: "Dinner: ¥10,000~¥14,999"
        1: < ¥1,000
        2: ¥1,000 - ¥3,999
        3: ¥4,000 - ¥9,999
        4: ¥10,000+
        """
        if not price_str:
            return None
        
        # Extract max price if range, or single price
        prices = re.findall(r'[¥￥,0-9]+', price_str)
        if not prices:
            return None
            
        # Clean and convert largest found number
        try:
            max_val = 0
            for p in prices:
                val = int(p.replace('¥', '').replace('￥', '').replace(',', ''))
                if val > max_val:
                    max_val = val
            
            if max_val == 0: return None
            if max_val < 1000: return 1
            if max_val < 4000: return 2
            if max_val < 10000: return 3
            return 4
        except:
            return None

    def get_lat_lon(self, soup: BeautifulSoup) -> Dict[str, Optional[float]]:
        """Try to extract coordinates from scripts or map links"""
        # Strategy 1: embedded JSON-LD or similar in scripts
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string:
                # Look for standard lat/lon patterns
                # "latitude":35.6895,"longitude":139.6917
                lat_match = re.search(r'["\']latitude["\']\s*:\s*(-?\d+\.\d+)', script.string)
                lon_match = re.search(r'["\']longitude["\']\s*:\s*(-?\d+\.\d+)', script.string)
                if lat_match and lon_match:
                    return {"lat": float(lat_match.group(1)), "lon": float(lon_match.group(1))}

        # Strategy 2: Map link
        map_link = soup.find('a', class_='js-map-link') or soup.find('a', href=re.compile(r'maps\.google'))
        if map_link:
            href = map_link.get('href', '')
            match = re.search(r'q=(-?\d+\.\d+),(-?\d+\.\d+)', href)
            if match:
                return {"lat": float(match.group(1)), "lon": float(match.group(2))}
                
        return {"lat": None, "lon": None}

    def parse_restaurant_card(self, item: BeautifulSoup, category: str) -> Optional[Dict]:
        """Parse a single restaurant list item"""
        try:
            # Name and Link
            name_tag = item.select_one('.list-rst__rst-name-target') or item.select_one('a.list-rst__name-main')
            if not name_tag:
                return None
                
            name = self.clean_text(name_tag.get_text())
            detail_url = name_tag.get('href', '')
            if not detail_url.startswith('http'):
                detail_url = urljoin(self.base_url, detail_url)

            # Rating
            rating_tag = item.select_one('.list-rst__rating-val') or item.select_one('.c-rating__val')
            rating = self.parse_rating(rating_tag.get_text()) if rating_tag else 0.0

            # Price / Budget (Dinner usually listed first, or check icons)
            # .c-rating-v3__val--dinner / .c-rating-v3__val--lunch
            price_tag = item.select_one('.c-rating-v3__val--dinner') or item.select_one('.list-rst__budget-val')
            price_range = self.parse_price(price_tag.get_text()) if price_tag else None

            # Area / Neighborhood
            area_tag = item.select_one('.list-rst__area-genre')
            neighborhood = "Tokyo"
            if area_tag:
                # Format is usually "Neighborhood / Category"
                parts = area_tag.get_text().split('/')
                if parts:
                    neighborhood = self.clean_text(parts[0])

            # Description/Catchphrase
            desc_tag = item.select_one('.list-rst__catch') or item.select_one('.list-rst__pr-title')
            short_desc = self.clean_text(desc_tag.get_text()) if desc_tag else f"{category} restaurant in {neighborhood}"
            
            # Additional tags
            tags = [category]
            if rating >= 3.5:
                tags.append("Popular")
            if rating >= 3.7:
                tags.append("Highly Rated")
                
            # Construct POI
            poi = {
                "id": self.generate_poi_id(detail_url),
                "name": name,
                "type": "restaurant",
                "category_tags": [category], # Primary category
                "neighborhood": neighborhood,
                "price_range": price_range,
                "halal": "unknown",
                "cuisine": [category],
                "interest_tags": tags,
                "coordinates": {"lat": None, "lon": None}, # Hard to get from list view
                "typical_duration_minutes": 60, # Default for dining
                "best_time_of_day": "night" if price_range and price_range > 2 else "afternoon",
                "short_description": short_desc,
                "source_url": detail_url,
                "last_updated_ts": datetime.now().isoformat()
            }
            
            return poi

        except Exception as e:
            print(f"Error parsing item: {e}")
            return None

    def parse_detail_page(self, url: str) -> Dict:
        """Parse restaurant detail page for rich metadata"""
        try:
            # Random delay before detail page
            self.random_delay(1.0, 2.5)
            
            resp = self.session.get(url, timeout=10)
            if resp.status_code != 200:
                print(f"    Failed to fetch detail: {resp.status_code}")
                return {}
                
            soup = BeautifulSoup(resp.content, 'html.parser')
            details = {}
            
            # 1. Parse "Restaurant information" table
            # The table usually has class "c-table c-table--form rstinfo-table__table"
            info_table = soup.select_one('.rstinfo-table__table')
            if info_table:
                rows = info_table.find_all('tr')
                for row in rows:
                    header = row.find('th')
                    data = row.find('td')
                    if header and data:
                        h_text = self.clean_text(header.get_text()).lower()
                        d_text = self.clean_text(data.get_text())
                        
                        if 'average price' in h_text:
                            details['price_text'] = d_text
                        elif 'awards' in h_text:
                            details['awards'] = d_text
                        elif 'categories' in h_text:
                            details['categories'] = d_text
                        elif 'remarks' in h_text:
                            details['remarks'] = d_text
                        elif 'private rooms' in h_text:
                            details['private_rooms'] = d_text
                        elif 'address' in h_text:
                            details['address'] = d_text
            
            # 2. Get Coordinates from map link on detail page if missing
            if not details.get('lat'):
                coords = self.get_lat_lon(soup)
                if coords['lat']:
                    details['coordinates'] = coords

            # 3. Description Generation
            short_desc = ""
            
            # Priority 1: "PR Comment" (Narrative text)
            pr_comment_wrap = soup.select_one(".pr-comment-wrap")
            if pr_comment_wrap:
                pr_title = pr_comment_wrap.select_one(".pr-comment-title")
                pr_body = pr_comment_wrap.select_one(".pr-comment__body")
                
                title_text = self.clean_text(pr_title.get_text()) if pr_title else ""
                body_text = self.clean_text(pr_body.get_text()) if pr_body else ""
                
                if title_text and body_text:
                    short_desc = f"{title_text} {body_text}"
                elif title_text:
                    short_desc = title_text
                elif body_text:
                    short_desc = body_text

            # Priority 2: Fallback to constructed string
            if not short_desc:
                desc_parts = []
                
                # Awards (Simplified: first 3 only)
                if details.get('awards'):
                    # Awards string is usually "The Tabelog Award 2025... Selected for..."
                    # It's hard to split perfectly without regex, but let's just truncate if too long
                    # or just use first sentence.
                    # Simple heuristic: Take first 100 chars or split by "winner"/"Selected"
                    awards_text = details['awards']
                    # Use a simple truncation for now to avoid massive lists
                    if len(awards_text) > 150:
                        awards_text = awards_text[:147] + "..."
                    desc_parts.append(f"Awards: {awards_text}")

                if details.get('remarks'):
                    remarks = details['remarks']
                    if len(remarks) > 100: remarks = remarks[:100] + "..."
                    desc_parts.append(f"Remarks: {remarks}")
                
                if details.get('private_rooms') and 'available' in details['private_rooms'].lower():
                    desc_parts.append("Private rooms available.")
                
                if details.get('categories'):
                    desc_parts.append(f"Specializes in {details['categories']}.")

                short_desc = ". ".join(desc_parts)
                
            details['generated_description'] = short_desc
            
            return details
            
        except Exception as e:
            print(f"    Error parsing detail page: {e}")
            return {}

    def scrape_category(self, category_name: str, url_suffix: str, limit: int = 50) -> List[Dict]:
        """Scrape a specific category with detail page visits"""
        print(f"\n--- Scraping Category: {category_name} ---")
        base_cat_url = urljoin(self.tokyo_url, url_suffix)
        start_url = f"{base_cat_url}?SrtT=rt" # Ranking sort
        
        items = []
        page = 1
        
        while len(items) < limit:
            target_url = f"{start_url}&pg={page}" if page > 1 else start_url
            print(f"Fetching list page {page}: {target_url}")
            
            try:
                resp = self.session.get(target_url, timeout=10)
                if resp.status_code != 200:
                    break
                    
                soup = BeautifulSoup(resp.content, 'html.parser')
                list_items = soup.select('.list-rst') or soup.select('.js-rst-list-item')
                
                if not list_items:
                    print("No items found on page")
                    break
                
                print(f"Found {len(list_items)} items. Scraping details...")
                
                for item in list_items:
                    # Parse basic info from list
                    poi = self.parse_restaurant_card(item, category_name)
                    if not poi:
                        continue
                        
                    # Skip duplication check for speed, relying on set later if needed
                    if any(x['id'] == poi['id'] for x in items):
                        continue

                    # FETCH DETAIL PAGE
                    print(f"  > Fetching details for: {poi['name']}")
                    details = self.parse_detail_page(poi['source_url'])
                    
                    # Update POI with detail info
                    if details:
                        # Update Price from detail page (more accurate)
                        if details.get('price_text'):
                            new_price = self.parse_price(details['price_text'])
                            if new_price:
                                poi['price_range'] = new_price
                        
                        # Update Description
                        if details.get('generated_description'):
                             # Use generated description if robust, else fallback/append
                             poi['short_description'] = details['generated_description']
                        elif details.get('remarks'):
                             poi['short_description'] = details['remarks']

                        # Update Coordinates
                        if details.get('coordinates'):
                            poi['coordinates'] = details['coordinates']

                    items.append(poi)
                    if len(items) >= limit:
                        break
                        
                # Next page check
                next_link = soup.select_one('.c-pagination__arrow--next')
                if not next_link or 'is-disabled' in next_link.get('class', []):
                    break
                    
                page += 1
                self.random_delay()
                
            except Exception as e:
                print(f"Error scraping page {page}: {e}")
                break
                
        return items

    def run(self, max_per_category: int = 55):
        """Main execution method"""
        all_pois = []
        # Randomize category order to avoid patterns
        cat_items = list(self.categories.items())
        random.shuffle(cat_items)
        
        for cat_name, url_suffix in cat_items:
            pois = self.scrape_category(cat_name, url_suffix, limit=max_per_category)
            all_pois.extend(pois)
            self.random_delay(5, 8)
            
        return all_pois

    def save_data(self, pois: List[Dict]):
        """Save results to CSV and JSON in src/data/scrapers/"""
        if not pois:
            print("No data to save.")
            return
            
        # Ensure output directory exists (it should, but good practice)
        output_dir = "src/data/scrapers"
        import os
        os.makedirs(output_dir, exist_ok=True)
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # JSON
        json_file = os.path.join(output_dir, f"tabelog_restaurants_{timestamp}.json")
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(pois, f, indent=2, ensure_ascii=False)
        print(f"Saved JSON to {json_file}")
        
        # CSV
        csv_file = os.path.join(output_dir, f"tabelog_restaurants_{timestamp}.csv")
        fieldnames = [
            'id', 'name', 'type', 'category_tags', 'neighborhood',
            'price_range', 'halal', 'cuisine', 'interest_tags',
            'coordinates_lat', 'coordinates_lon', 'typical_duration_minutes',
            'best_time_of_day', 'short_description', 'source_url', 'last_updated_ts'
        ]
        
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for poi in pois:
                row = poi.copy()
                # Flatten complex fields
                row['coordinates_lat'] = row['coordinates'].get('lat')
                row['coordinates_lon'] = row['coordinates'].get('lon')
                del row['coordinates']
                
                row['category_tags'] = "|".join(row['category_tags'])
                row['cuisine'] = "|".join(row['cuisine']) if row.get('cuisine') else ""
                row['interest_tags'] = "|".join(row['interest_tags'])
                
                writer.writerow(row)
        print(f"Saved CSV to {csv_file}")

def main():
    limit = 50
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        limit = 5
        print("Running in TEST mode (limit 5 per category)")
        
    scraper = TabelogScraper()
    data = scraper.run(max_per_category=limit)
    scraper.save_data(data)
    
if __name__ == "__main__":
    main()
