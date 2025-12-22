# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy
from itemloaders.processors import TakeFirst, MapCompose, Join
from scrapy.loader import ItemLoader


class POIItem(scrapy.Item):
    """
    Unified POI (Point of Interest) Item for travel planner data
    """
    # Core fields
    id = scrapy.Field()
    name = scrapy.Field()
    type = scrapy.Field()  # "attraction" | "restaurant" | "shop" | "event_venue"
    
    # Classification
    category_tags = scrapy.Field()
    neighborhood = scrapy.Field()
    interest_tags = scrapy.Field()
    
    # Restaurant-specific
    price_range = scrapy.Field()  # 1-4 scale
    halal = scrapy.Field()  # "true" | "false" | "unknown"
    cuisine = scrapy.Field()
    
    # Location and timing
    coordinates = scrapy.Field()  # {"lat": float, "lon": float}
    typical_duration_minutes = scrapy.Field()
    best_time_of_day = scrapy.Field()  # "morning" | "afternoon" | "evening" | "night"
    
    # Content
    short_description = scrapy.Field()
    
    # Metadata
    source_url = scrapy.Field()
    last_updated_ts = scrapy.Field()


class POIItemLoader(ItemLoader):
    """
    Custom ItemLoader for POI data
    """
    default_item_class = POIItem
    default_output_processor = TakeFirst()
    
    # Clean text fields
    name_in = MapCompose(str.strip)
    neighborhood_in = MapCompose(str.strip)
    short_description_in = MapCompose(str.strip)
    type_in = MapCompose(str.strip, str.lower)
