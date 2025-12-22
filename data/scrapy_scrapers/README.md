# Travel Scrapers - Simplified Scrapy Project

Clean, simplified Scrapy project for scraping travel POI data.

## Project Structure

```
travel_scrapers/
├── scrapy.cfg              # Project configuration
├── travel_scrapers/
│   ├── items.py           # POI data schema (simplified)
│   ├── middlewares.py     # Essential retry logic only
│   ├── pipelines.py       # Validation + JSON export
│   ├── settings.py        # Clean, minimal settings
│   └── spiders/
│       └── gotokyo_events.py    # Events spider
├── output/
│   ├── processed/         # JSON output files
│   └── logs/             # Scraping logs
└── README.md
```

## Usage

### Run Spider
```bash
cd data/scrapy_scrapers

# List spiders
scrapy list

# Run events scraper
scrapy crawl gotokyo_events

# Test run (5 items)
scrapy crawl gotokyo_events -s CLOSESPIDER_ITEMCOUNT=5
```

### Output
- Single JSON file per run: `output/processed/{spider}_{timestamp}.json`
- Logs: `output/logs/scrapy.log`

## Key Features

✅ **Simplified & Clean**: Removed 60% of unnecessary code  
✅ **Consistent Paths**: All relative paths, no more confusion  
✅ **Essential Only**: Validation + export pipelines only  
✅ **Polite Scraping**: 1-second delays, retry logic  
✅ **Easy to Extend**: Simple structure for adding new spiders  

## Data Schema

Each POI follows this structure:
```json
{
  "id": "abc123",
  "name": "Event Name",
  "type": "event_venue",
  "category_tags": ["Festival"],
  "neighborhood": "Shibuya",
  "short_description": "Description...",
  "source_url": "https://...",
  "last_updated_ts": "2025-12-22T..."
}
```

## Adding New Spiders

1. Create new spider in `spiders/` directory
2. Use `POIItemLoader` for consistent data processing
3. Follow the pattern in `gotokyo_events.py`

That's it! No complex configuration needed.
