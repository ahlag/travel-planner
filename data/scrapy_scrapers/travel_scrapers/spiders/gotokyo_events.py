"""
Go Tokyo Events Spider
Migrated from standalone scraper to Scrapy spider
Scrapes event data from gotokyo.org and converts to unified POI schema
"""

import scrapy
import re
import hashlib
from datetime import datetime
from urllib.parse import urljoin
from travel_scrapers.items import POIItem, POIItemLoader


class GoTokyoEventsSpider(scrapy.Spider):
    name = 'gotokyo_events'
    allowed_domains = ['gotokyo.org']
    
    # Comprehensive URL list for maximum event discovery
    start_urls = [
        # Main event pages
        'https://www.gotokyo.org/en/event/index.html',
        'https://www.gotokyo.org/en/calendar/index.html',
        'https://www.gotokyo.org/en/spot/index.html',
        'https://www.gotokyo.org/en/',
        
        # Event categories
        'https://www.gotokyo.org/en/see-and-do/arts-and-design/art-and-exhibitions/index.html',
        'https://www.gotokyo.org/en/see-and-do/shopping/markets-and-festivals/index.html',
        'https://www.gotokyo.org/en/see-and-do/tradition-and-modern/temples-and-shrines/index.html',
        'https://www.gotokyo.org/en/see-and-do/nightlife/index.html',
        'https://www.gotokyo.org/en/see-and-do/outdoor-and-sports/parks-and-gardens/index.html',
        
        # Seasonal events
        'https://www.gotokyo.org/en/see-and-do/seasonal-highlights/index.html',
        'https://www.gotokyo.org/en/see-and-do/seasonal-highlights/spring/index.html',
        'https://www.gotokyo.org/en/see-and-do/seasonal-highlights/summer/index.html',
        'https://www.gotokyo.org/en/see-and-do/seasonal-highlights/autumn/index.html',
        'https://www.gotokyo.org/en/see-and-do/seasonal-highlights/winter/index.html',
        
        # District-specific event pages
        'https://www.gotokyo.org/en/destinations/central-tokyo/index.html',
        'https://www.gotokyo.org/en/destinations/northern-tokyo/index.html',
        'https://www.gotokyo.org/en/destinations/western-tokyo/index.html',
        'https://www.gotokyo.org/en/destinations/eastern-tokyo/index.html',
        'https://www.gotokyo.org/en/destinations/southern-tokyo/index.html',
        
        # Travel directory with event filters
        'https://www.gotokyo.org/en/travel-directory/result/index/genre_detail/8',  # Events & Festivals
        'https://www.gotokyo.org/en/travel-directory/result/index/genre_detail/1',  # Sightseeing
        'https://www.gotokyo.org/en/travel-directory/result/index/genre_detail/2',  # Entertainment
        'https://www.gotokyo.org/en/travel-directory/result/index/genre_detail/7',  # Culture
        
        # Special collections
        'https://www.gotokyo.org/en/see-and-do/tradition-and-modern/traditional-culture/index.html',
        'https://www.gotokyo.org/en/see-and-do/arts-and-design/museums/index.html',
        'https://www.gotokyo.org/en/see-and-do/nightlife/bars-and-restaurants/index.html',
        
        # Monthly calendar pages (current and upcoming months)
        'https://www.gotokyo.org/en/calendar/2025/01/index.html',
        'https://www.gotokyo.org/en/calendar/2025/02/index.html',
        'https://www.gotokyo.org/en/calendar/2025/03/index.html',
        'https://www.gotokyo.org/en/calendar/2025/04/index.html',
        'https://www.gotokyo.org/en/calendar/2025/05/index.html',
        'https://www.gotokyo.org/en/calendar/2025/06/index.html',
    ]
    
    custom_settings = {
        'DEPTH_LIMIT': 2,  # Increased for better discovery
        'DOWNLOAD_DELAY': 1,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 3,
        'CLOSESPIDER_PAGECOUNT': 150,  # Prevent runaway crawling
    }
    
    def parse(self, response):
        """Parse main listing pages to extract event cards"""
        self.logger.info(f'Parsing events page: {response.url}')
        
        # Enhanced event discovery with multiple strategies
        event_elements = []
        
        # Strategy 1: Look for specific event/spot containers
        event_selectors = [
            '.event-item', '.event-card', '.event-list-item',
            '.spot-item', '.spot-card', '.spot-list-item',
            '.list-item', '.item-card', '.content-item',
            'article[class*="item"]', 'article[class*="event"]',
            '.card', '.item', 'article'
        ]
        
        for selector in event_selectors:
            elements = response.css(selector)
            if elements and len(elements) >= 3:  # Need at least 3 for it to be a listing
                event_elements = elements
                self.logger.info(f'Found {len(elements)} events using selector: {selector}')
                break
        
        # Strategy 2: Look for event/spot links with good text
        if not event_elements:
            all_links = response.css('a[href]')
            event_links = []
            
            for link in all_links:
                href = link.css('::attr(href)').get()
                text = (link.css('::text').get() or '').strip()
                
                # More comprehensive URL patterns for events/spots
                url_patterns = ['/event/', '/spot/', '/ev', '/calendar/', '/see-and-do/']
                text_patterns = ['festival', 'exhibition', 'market', 'temple', 'shrine', 
                               'museum', 'park', 'garden', 'illumination', 'matsuri']
                
                if (href and any(pattern in href for pattern in url_patterns) and
                    (len(text) > 8 and len(text) < 100) and
                    (any(pattern in text.lower() for pattern in text_patterns) or 
                     len(text.split()) >= 3)):
                    event_links.append(link)
                    
            event_elements = event_links[:30]  # Increased limit
            self.logger.info(f'Found {len(event_elements)} potential events from links')
        
        # Strategy 3: Calendar page specific parsing
        if '/calendar/' in response.url:
            calendar_events = response.css('.calendar-event, .event-date, [class*="calendar"] a')
            if calendar_events:
                event_elements.extend(calendar_events)
                self.logger.info(f'Found {len(calendar_events)} calendar events')
        
        # Parse each event element
        events_yielded = 0
        for element in event_elements:
            poi_item = self.parse_event_card(element, response)
            if poi_item:
                # Follow detail link for more information
                detail_url = poi_item.get('source_url')
                if detail_url and detail_url != response.url:
                    yield response.follow(
                        detail_url, 
                        callback=self.parse_event_detail,
                        meta={'poi_item': poi_item},
                        priority=1
                    )
                else:
                    yield poi_item
                events_yielded += 1
        
        self.logger.info(f'Yielded {events_yielded} events from {response.url}')
        
        # Enhanced pagination and link following
        follow_links = []
        
        # Follow pagination
        pagination_selectors = [
            'a[href*="page="]::attr(href)',
            'a[href*="next"]::attr(href)',
            '.pagination a::attr(href)',
            '.pager a::attr(href)'
        ]
        for selector in pagination_selectors:
            links = response.css(selector).getall()
            follow_links.extend(links[:3])  # Limit per type
            
        # Follow category pages and sub-navigation
        if response.meta.get('depth', 0) < 1:  # Only follow from first level
            category_selectors = [
                'a[href*="/see-and-do/"]::attr(href)',
                'a[href*="/destinations/"]::attr(href)',
                'a[href*="/event/"]::attr(href)',
                'a[href*="/calendar/"]::attr(href)',
                'nav a::attr(href)'
            ]
            for selector in category_selectors:
                links = response.css(selector).getall()
                follow_links.extend(links[:5])  # Limit per category
        
        # Follow discovered links
        followed = 0
        for link_href in follow_links:
            if (link_href and link_href != response.url and 
                '/en/' in link_href and followed < 15):  # Overall limit
                yield response.follow(link_href, callback=self.parse, priority=0)
                followed += 1
    
    def parse_event_card(self, element, response):
        """Parse individual event card to extract basic event details"""
        loader = POIItemLoader(item=POIItem(), selector=element)
        
        try:
            # Extract event link
            link_elem = element.css('a::attr(href)').get()
            if not link_elem:
                return None
            
            event_url = urljoin(response.url, link_elem)
            loader.add_value('source_url', event_url)
            
            # Generate ID from URL
            poi_id = hashlib.md5(event_url.encode('utf-8')).hexdigest()[:12]
            loader.add_value('id', poi_id)
            
            # Extract event name
            name_selectors = [
                'h3::text', 'h4::text', '.event-title::text', 
                'a::text', '.title::text'
            ]
            name = None
            for selector in name_selectors:
                name_candidates = element.css(selector).getall()
                if name_candidates:
                    name = ' '.join(name_candidates).strip()
                    break
            
            if not name or len(name) < 3:
                return None
                
            loader.add_value('name', name)
            
            # Set type as event_venue
            loader.add_value('type', 'event_venue')
            
            # Extract description
            desc_selectors = [
                'p::text', '.description::text', '.event-desc::text',
                '.content::text', '.summary::text'
            ]
            description = ""
            for selector in desc_selectors:
                desc_parts = element.css(selector).getall()
                if desc_parts:
                    description = ' '.join(desc_parts).strip()
                    break
            
            if not description:
                description = name  # Fallback to name
                
            loader.add_value('short_description', description)
            
            # Extract date/time information
            date_selectors = [
                'time::text', '.date::text', '.event-date::text',
                '[class*="date"]::text'
            ]
            event_date = ""
            for selector in date_selectors:
                date_parts = element.css(selector).getall()
                if date_parts:
                    event_date = ' '.join(date_parts).strip()
                    break
            
            # Extract location/neighborhood
            location_selectors = [
                '.location::text', '.venue::text', '.area::text',
                '[class*="location"]::text', '[class*="area"]::text'
            ]
            neighborhood = "Tokyo"  # Default
            for selector in location_selectors:
                location_parts = element.css(selector).getall()
                if location_parts:
                    neighborhood = ' '.join(location_parts).strip()
                    break
                    
            loader.add_value('neighborhood', neighborhood)
            
            # Extract category tags from classes or nearby elements
            category_tags = []
            tag_selectors = [
                'span::text', '.tag::text', '.category::text',
                '[class*="tag"]::text', '[class*="category"]::text'
            ]
            
            for selector in tag_selectors:
                tag_parts = element.css(selector).getall()
                for tag_text in tag_parts:
                    tag_text = tag_text.strip()
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
            
            if not category_tags:
                category_tags = ['Event']
                
            loader.add_value('category_tags', category_tags)
            
            # Interest tags (similar to category but more descriptive)
            interest_tags = category_tags.copy()
            text_content = f"{name} {description}".lower()
            if 'family' in text_content:
                interest_tags.append('Family Friendly')
            if any(word in text_content for word in ['night', 'evening', 'illumination']):
                interest_tags.append('Nightlife')
            if 'free' in text_content:
                interest_tags.append('Free Entry')
                
            loader.add_value('interest_tags', interest_tags)
            
            # Determine best time of day
            time_text = f"{name} {description} {event_date}".lower()
            if any(word in time_text for word in ['morning', 'am', '朝']):
                loader.add_value('best_time_of_day', 'morning')
            elif any(word in time_text for word in ['afternoon', 'pm', '午後']):
                loader.add_value('best_time_of_day', 'afternoon')
            elif any(word in time_text for word in ['evening', 'night', '夜', 'illumination']):
                loader.add_value('best_time_of_day', 'evening')
            
            # Default values for event venues
            loader.add_value('halal', 'unknown')
            loader.add_value('price_range', None)
            
            return loader.load_item()
            
        except Exception as e:
            self.logger.error(f"Error parsing event card: {e}")
            return None
    
    def parse_event_detail(self, response):
        """Parse event detail page for additional information like coordinates"""
        poi_item = response.meta.get('poi_item')
        if not poi_item:
            return None
        
        # Extract coordinates from detail page
        coordinates = self.extract_coordinates(response)
        if coordinates:
            poi_item['coordinates'] = coordinates
        
        # Try to get more detailed description
        detailed_desc_selectors = [
            '.description p::text',
            '.content p::text', 
            '.detail p::text',
            'main p::text'
        ]
        
        for selector in detailed_desc_selectors:
            desc_parts = response.css(selector).getall()
            if desc_parts and len(desc_parts) > 1:  # More content than basic
                detailed_desc = ' '.join(desc_parts).strip()
                if len(detailed_desc) > len(poi_item.get('short_description', '')):
                    poi_item['short_description'] = self.clean_description(detailed_desc)
                break
        
        yield poi_item
    
    def extract_coordinates(self, response):
        """Extract coordinates from event detail page if available"""
        try:
            # Look for Google Maps links or coordinates
            map_links = response.css('a[href*="maps.google"]::attr(href), a[href*="google.com/maps"]::attr(href)').getall()
            
            for href in map_links:
                # Extract coordinates from Google Maps URL
                coord_match = re.search(r'[@,](-?\d+\.\d+),(-?\d+\.\d+)', href)
                if coord_match:
                    lat, lon = float(coord_match.group(1)), float(coord_match.group(2))
                    return {"lat": lat, "lon": lon}
            
            # Look for embedded coordinates in script tags
            scripts = response.css('script::text').getall()
            for script in scripts:
                if script:
                    coord_match = re.search(r'"lat":\s*(-?\d+\.\d+).*?"lng":\s*(-?\d+\.\d+)', script)
                    if coord_match:
                        lat, lon = float(coord_match.group(1)), float(coord_match.group(2))
                        return {"lat": lat, "lon": lon}
                        
        except Exception as e:
            self.logger.warning(f"Error extracting coordinates from {response.url}: {e}")
            
        return None
    
    def clean_description(self, description):
        """Clean and limit description length"""
        if not description:
            return ""
        
        # Remove extra whitespace
        desc = re.sub(r'\s+', ' ', description.strip())
        
        # Limit length to ~300 characters
        if len(desc) > 300:
            # Find last complete sentence within limit
            short = desc[:300]
            last_period = short.rfind('.')
            if last_period > 150:
                desc = short[:last_period + 1]
            else:
                desc = short + "..."
        
        return desc
