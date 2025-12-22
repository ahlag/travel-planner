# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

import json
import hashlib
from datetime import datetime
from itemadapter import ItemAdapter


class POINormalizationPipeline:
    """
    Pipeline to normalize POI data according to original format schema
    """
    
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        
        # Generate ID if not present
        if not adapter.get('id'):
            source_url = adapter.get('source_url', '')
            name = adapter.get('name', 'unnamed')
            adapter['id'] = hashlib.md5((source_url or name).encode('utf-8')).hexdigest()[:12]
        
        # Ensure valid type
        poi_type = adapter.get('type', '').lower().strip()
        if poi_type not in ['attraction', 'restaurant', 'shop', 'event_venue']:
            adapter['type'] = 'event_venue'  # Default for events
        
        # Clean tags - ensure they are lists
        for tag_field in ['category_tags', 'interest_tags']:
            tags = adapter.get(tag_field, [])
            if isinstance(tags, str):
                adapter[tag_field] = [tag.strip() for tag in tags.split(',') if tag.strip()]
            elif not isinstance(tags, list):
                adapter[tag_field] = []
        
        # Set cuisine as null (not list for this field in original)
        if not adapter.get('cuisine'):
            adapter['cuisine'] = None
        
        # Set defaults
        if not adapter.get('neighborhood'):
            adapter['neighborhood'] = 'Tokyo'
        if not adapter.get('halal'):
            adapter['halal'] = 'unknown'
        
        # Add missing fields with proper null values to match original format
        if not adapter.get('price_range'):
            adapter['price_range'] = None
            
        if not adapter.get('coordinates'):
            adapter['coordinates'] = {"lat": None, "lon": None}
            
        # Set typical_duration_minutes based on category
        if not adapter.get('typical_duration_minutes'):
            category_tags = adapter.get('category_tags', [])
            if any('festival' in tag.lower() for tag in category_tags):
                adapter['typical_duration_minutes'] = 180  # 3 hours for festivals
            else:
                adapter['typical_duration_minutes'] = 90   # 1.5 hours for general events
        
        # Set best_time_of_day if not present
        if not adapter.get('best_time_of_day'):
            adapter['best_time_of_day'] = None
        
        # Set timestamp
        adapter['last_updated_ts'] = datetime.now().isoformat()
        
        return item


class ValidationPipeline:
    """
    Pipeline to validate required fields
    """
    
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        
        # Check required fields
        required_fields = ['id', 'name', 'type']
        for field in required_fields:
            if not adapter.get(field):
                spider.logger.warning(f"Missing required field '{field}' - dropping item")
                return None
        
        # Check name quality
        name = adapter.get('name', '').strip()
        if len(name) < 3:
            spider.logger.warning(f"Name too short: {name} - dropping item")
            return None
        
        return item


class FieldOrderPipeline:
    """
    Pipeline to reorder fields to match original format exactly
    """
    
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        
        # Define the exact field order from original format
        field_order = [
            'id', 'name', 'type', 'category_tags', 'neighborhood', 
            'price_range', 'halal', 'cuisine', 'interest_tags', 
            'coordinates', 'typical_duration_minutes', 'best_time_of_day',
            'short_description', 'source_url', 'last_updated_ts'
        ]
        
        # Create new ordered dict
        ordered_item = {}
        for field in field_order:
            if field in adapter:
                ordered_item[field] = adapter[field]
        
        # Add any remaining fields not in the order (shouldn't happen, but just in case)
        for field, value in adapter.items():
            if field not in ordered_item:
                ordered_item[field] = value
        
        # Replace the item with ordered version
        adapter.clear()
        adapter.update(ordered_item)
        
        return item


class JSONExportPipeline:
    """
    JSON export pipeline that matches original format
    """
    
    def __init__(self):
        self.items = []
        self.file = None
    
    def open_spider(self, spider):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"output/processed/{spider.name}_{timestamp}.json"
        self.file = open(filename, 'w', encoding='utf-8')
        spider.logger.info(f"Saving items to: {filename}")
        self.items = []
    
    def close_spider(self, spider):
        if self.file:
            # Write all items as a proper JSON array
            json.dump(self.items, self.file, ensure_ascii=False, indent=2)
            self.file.close()
    
    def process_item(self, item, spider):
        # Convert to dict and add to items list
        self.items.append(dict(ItemAdapter(item)))
        return item
