#!/usr/bin/env python3
"""
Go Tokyo Event Calendar Scraper
Scrapes event data from gotokyo.org and converts to unified POI schema
"""

import requests
import json
import csv
import hashlib
import time
from datetime import datetime
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re


class GoTokyoEventScraper:
    def __init__(self):
        self.base_url = "https://www.gotokyo.org"
        self.events_url = "https://www.gotokyo.org/en/spot/index.html"  # Using spots page as it has more content
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        self.scraped_events = []
        
    def generate_poi_id(self, url: str) -> str:
        """Generate unique ID from source URL"""
        return hashlib.md5(url.encode('utf-8')).hexdigest()[:12]
    
    def extract_coordinates(self, event_detail_url: str) -> Dict[str, Optional[float]]:
        """Extract coordinates from event detail page if available"""
        try:
            response = self.session.get(event_detail_url)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for Google Maps links or coordinates
            map_links = soup.find_all('a', href=re.compile(r'maps\.google|google\.com/maps'))
            for link in map_links:
                href = link.get('href', '')
                # Extract coordinates from Google Maps URL
                coord_match = re.search(r'[@,](-?\d+\.\d+),(-?\d+\.\d+)', href)
                if coord_match:
                    lat, lon = float(coord_match.group(1)), float(coord_match.group(2))
                    return {"lat": lat, "lon": lon}
            
            # Look for embedded coordinates in script tags or data attributes
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string:
                    coord_match = re.search(r'"lat":\s*(-?\d+\.\d+).*?"lng":\s*(-?\d+\.\d+)', script.string)
                    if coord_match:
                        lat, lon = float(coord_match.group(1)), float(coord_match.group(2))
                        return {"lat": lat, "lon": lon}
                        
        except Exception as e:
            print(f"Error extracting coordinates from {event_detail_url}: {e}")
            
        return {"lat": None, "lon": None}
    
    def parse_event_card(self, event_element) -> Optional[Dict]:
        """Parse individual event card to extract event details"""
        try:
            # Extract event link
            link_elem = event_element.find('a')
            if not link_elem:
                return None
                
            event_url = urljoin(self.base_url, link_elem.get('href', ''))
            
            # Extract event name
            name_elem = event_element.find(['h3', 'h4', '.event-title']) or link_elem
            name = name_elem.get_text().strip() if name_elem else "Unnamed Event"
            
            # Extract description
            desc_elem = event_element.find(['p', '.description', '.event-desc'])
            description = desc_elem.get_text().strip() if desc_elem else name
            
            # Extract date/time information
            date_elem = event_element.find(['time', '.date', '.event-date'])
            event_date = date_elem.get_text().strip() if date_elem else ""
            
            # Extract location/neighborhood
            location_elem = event_element.find(['.location', '.venue', '.area'])
            neighborhood = location_elem.get_text().strip() if location_elem else "Tokyo"
            
            # Extract image for additional context
            img_elem = event_element.find('img')
            image_url = urljoin(self.base_url, img_elem.get('src', '')) if img_elem else ""
            
            # Extract category tags from classes or nearby elements
            category_tags = []
            tag_elements = event_element.find_all(['span', '.tag', '.category'])
            for tag_elem in tag_elements:
                tag_text = tag_elem.get_text().strip()
                if tag_text and len(tag_text) < 50:  # Reasonable tag length
                    category_tags.append(tag_text)
            
            # If no explicit tags, infer from event name and description
            if not category_tags:
                text_content = f"{name} {description}".lower()
                if any(word in text_content for word in ['festival', 'matsuri']):
                    category_tags.append('Festival')
                if any(word in text_content for word in ['museum', 'exhibition', 'art']):
                    category_tags.append('Exhibition')
                if any(word in text_content for word in ['temple', 'shrine', 'traditional']):
                    category_tags.append('Traditional')
                if any(word in text_content for word in ['food', 'market', 'culinary']):
                    category_tags.append('Food')
                if any(word in text_content for word in ['music', 'concert', 'performance']):
                    category_tags.append('Music')
                if any(word in text_content for word in ['sakura', 'cherry', 'flower']):
                    category_tags.append('Seasonal')
                    
            # Interest tags (similar to category but more descriptive)
            interest_tags = category_tags.copy()
            if 'family' in f"{name} {description}".lower():
                interest_tags.append('Family Friendly')
            if any(word in f"{name} {description}".lower() for word in ['night', 'evening', 'illumination']):
                interest_tags.append('Nightlife')
            if 'free' in f"{name} {description}".lower():
                interest_tags.append('Free Entry')
                
            # Extract coordinates (this might be slow, so we'll do it selectively)
            coordinates = self.extract_coordinates(event_url)
            
            # Determine best time of day
            best_time = None
            time_text = f"{name} {description} {event_date}".lower()
            if any(word in time_text for word in ['morning', 'am', '朝']):
                best_time = 'morning'
            elif any(word in time_text for word in ['afternoon', 'pm', '午後']):
                best_time = 'afternoon'
            elif any(word in time_text for word in ['evening', 'night', '夜', 'illumination']):
                best_time = 'evening'
            
            # Create POI object according to schema
            poi = {
                "id": self.generate_poi_id(event_url),
                "name": name,
                "type": "event_venue",  # All events are event venues per schema
                "category_tags": list(set(category_tags)) if category_tags else ["Event"],
                "neighborhood": self.clean_neighborhood(neighborhood),
                "price_range": None,  # Usually not specified for events
                "halal": "unknown",  # Usually not specified for events
                "cuisine": None,  # Not applicable for events
                "interest_tags": list(set(interest_tags)) if interest_tags else ["Event"],
                "coordinates": coordinates,
                "typical_duration_minutes": self.estimate_duration(name, description),
                "best_time_of_day": best_time,
                "short_description": self.create_short_description(description, event_date),
                "source_url": event_url,
                "last_updated_ts": datetime.now().isoformat()
            }
            
            return poi
            
        except Exception as e:
            print(f"Error parsing event card: {e}")
            return None
    
    def clean_neighborhood(self, location_text: str) -> str:
        """Clean and standardize neighborhood names"""
        if not location_text:
            return "Tokyo"
            
        # Common neighborhood mappings
        neighborhood_map = {
            'shibuya': 'Shibuya',
            'shinjuku': 'Shinjuku', 
            'harajuku': 'Harajuku',
            'asakusa': 'Asakusa',
            'ginza': 'Ginza',
            'roppongi': 'Roppongi',
            'akihabara': 'Akihabara',
            'ueno': 'Ueno',
            'tokyo station': 'Tokyo Station',
            'ikebukuro': 'Ikebukuro',
            'odaiba': 'Odaiba',
            'tsukiji': 'Tsukiji'
        }
        
        location_lower = location_text.lower()
        for key, value in neighborhood_map.items():
            if key in location_lower:
                return value
                
        # If no mapping found, return cleaned version
        return location_text.strip().title()
    
    def estimate_duration(self, name: str, description: str) -> Optional[int]:
        """Estimate event duration in minutes based on event type"""
        text = f"{name} {description}".lower()
        
        if any(word in text for word in ['festival', 'matsuri']):
            return 180  # 3 hours for festivals
        elif any(word in text for word in ['exhibition', 'museum']):
            return 90   # 1.5 hours for exhibitions
        elif any(word in text for word in ['concert', 'performance', 'show']):
            return 120  # 2 hours for performances
        elif any(word in text for word in ['market', 'fair']):
            return 60   # 1 hour for markets
        elif any(word in text for word in ['ceremony', 'ritual']):
            return 45   # 45 minutes for ceremonies
        else:
            return 90   # Default 1.5 hours
    
    def create_short_description(self, description: str, event_date: str) -> str:
        """Create a 2-3 sentence summary"""
        # Clean up description
        desc = description.strip()
        if len(desc) > 200:
            # Take first 200 characters and find last complete sentence
            short = desc[:200]
            last_period = short.rfind('.')
            if last_period > 100:
                desc = short[:last_period + 1]
            else:
                desc = short + "..."
                
        # Add date information if available
        if event_date and event_date not in desc:
            desc = f"{desc} {event_date}".strip()
            
        return desc
    
    def scrape_events_page(self, url: str) -> List[Dict]:
        """Scrape events from a single page"""
        try:
            print(f"Scraping: {url}")
            response = self.session.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            events = []
            
            # Look for event cards with various possible selectors
            event_selectors = [
                '.event-item',
                '.event-card', 
                '.list-item',
                '.spot-item',
                'article',
                '.item'
            ]
            
            event_elements = []
            for selector in event_selectors:
                elements = soup.select(selector)
                if elements:
                    event_elements = elements
                    print(f"Found {len(elements)} events using selector: {selector}")
                    break
            
            # If no specific event elements found, look for any links that might be events
            if not event_elements:
                # Look for links containing event-related keywords
                all_links = soup.find_all('a', href=True)
                event_links = []
                for link in all_links:
                    href = link.get('href', '')
                    text = link.get_text().strip()
                    if (('/event/' in href or '/spot/' in href) and 
                        len(text) > 5 and len(text) < 200):
                        event_links.append(link.parent or link)
                        
                event_elements = event_links[:20]  # Limit to prevent overloading
                print(f"Found {len(event_elements)} potential events from links")
            
            for element in event_elements:
                poi = self.parse_event_card(element)
                if poi:
                    events.append(poi)
                    print(f"✓ Scraped: {poi['name']}")
                
                # Be respectful with delays
                time.sleep(0.5)
            
            return events
            
        except Exception as e:
            print(f"Error scraping {url}: {e}")
            return []
    
    def scrape_all_events(self) -> List[Dict]:
        """Main scraping function"""
        print("Starting Go Tokyo Events scraping...")
        
        # Enhanced URL list including travel directory
        urls_to_scrape = [
            self.events_url,
            "https://www.gotokyo.org/en/",
            "https://www.gotokyo.org/en/event/index.html",
            "https://www.gotokyo.org/en/travel-directory/result/index/genre_detail/8",  # Events & Festivals (user specified)
            "https://www.gotokyo.org/en/calendar/index.html"  # Calendar page
        ]
        
        all_events = []
        seen_urls = set()  # Track unique events by URL
        
        for url in urls_to_scrape:
            page_events = self.scrape_events_page(url)
            
            # Filter out duplicates and low-quality entries
            for event in page_events:
                if (event['source_url'] not in seen_urls and 
                    len(event['name']) > 5 and
                    event['name'] not in ['More details here', 'Beyond Tokyo'] and
                    not event['source_url'].endswith(('/spot/index.html', '/event/index.html', '/tourists/spot/suburbs/fromtokyo/index.html'))):  # Avoid generic landing pages only
                    
                    all_events.append(event)
                    seen_urls.add(event['source_url'])
            
            time.sleep(1)  # Be respectful
        
        events = all_events
        print(f"Found {len(events)} real events from Go Tokyo website")
        
        # Look for pagination or additional event pages
        try:
            response = self.session.get(self.events_url)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for pagination links
            pagination_links = soup.find_all('a', href=re.compile(r'page=\d+|/\d+\.html'))
            additional_urls = []
            
            for link in pagination_links[:5]:  # Limit to first 5 pages
                href = link.get('href')
                if href:
                    full_url = urljoin(self.base_url, href)
                    if full_url not in [self.events_url] + additional_urls:
                        additional_urls.append(full_url)
            
            # Scrape additional pages
            for url in additional_urls:
                additional_events = self.scrape_events_page(url)
                events.extend(additional_events)
                time.sleep(1)  # Longer delay between pages
                
        except Exception as e:
            print(f"Error finding additional pages: {e}")
        
        self.scraped_events = events
        return events
    
    def save_to_csv(self, events: List[Dict], filename: str):
        """Save events to CSV file"""
        if not events:
            print("No events to save")
            return
            
        # Define CSV fieldnames based on POI schema
        fieldnames = [
            'id', 'name', 'type', 'category_tags', 'neighborhood',
            'price_range', 'halal', 'cuisine', 'interest_tags',
            'coordinates_lat', 'coordinates_lon', 'typical_duration_minutes',
            'best_time_of_day', 'short_description', 'source_url', 'last_updated_ts'
        ]
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for event in events:
                # Flatten the coordinates and convert lists to strings
                row = event.copy()
                coords = row.pop('coordinates', {})
                row['coordinates_lat'] = coords.get('lat')
                row['coordinates_lon'] = coords.get('lon')
                row['category_tags'] = ','.join(row.get('category_tags', []))
                row['interest_tags'] = ','.join(row.get('interest_tags', []))
                if row.get('cuisine'):
                    row['cuisine'] = ','.join(row['cuisine'])
                
                writer.writerow(row)
        
        print(f"✓ Saved {len(events)} events to {filename}")
    

    def save_to_json(self, events: List[Dict], filename: str):
        """Save events to JSON file for debugging"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(events, f, indent=2, ensure_ascii=False)
        print(f"✓ Saved {len(events)} events to {filename}")


def main():
    """Main execution function"""
    scraper = GoTokyoEventScraper()
    
    try:
        # Scrape all events
        events = scraper.scrape_all_events()
        
        if events:
            print(f"\n✓ Successfully scraped {len(events)} events")
            
            # Save to both CSV and JSON
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_filename = f"gotokyo_events_{timestamp}.csv"
            json_filename = f"gotokyo_events_{timestamp}.json"
            
            scraper.save_to_csv(events, csv_filename)
            scraper.save_to_json(events, json_filename)
            
            # Print summary
            print(f"\n📊 Scraping Summary:")
            print(f"   Total events: {len(events)}")
            print(f"   Unique neighborhoods: {len(set(e['neighborhood'] for e in events))}")
            print(f"   Events with coordinates: {sum(1 for e in events if e['coordinates']['lat'])}")
            
            # Print sample events
            print(f"\n📋 Sample Events:")
            for i, event in enumerate(events[:3]):
                print(f"   {i+1}. {event['name']} ({event['neighborhood']})")
                print(f"      Tags: {', '.join(event['category_tags'])}")
                print(f"      URL: {event['source_url']}")
                print()
            
        else:
            print("❌ No events were scraped")
            
    except Exception as e:
        print(f"❌ Scraping failed: {e}")
        raise


if __name__ == "__main__":
    main()
