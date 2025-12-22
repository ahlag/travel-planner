# Scrapy settings for travel_scrapers project

BOT_NAME = 'travel_scrapers'

SPIDER_MODULES = ['travel_scrapers.spiders']
NEWSPIDER_MODULE = 'travel_scrapers.spiders'

# Obey robots.txt rules
ROBOTSTXT_OBEY = True

# Configure delays and concurrency
DOWNLOAD_DELAY = 1
CONCURRENT_REQUESTS = 4
CONCURRENT_REQUESTS_PER_DOMAIN = 2

# Disable cookies and telnet
COOKIES_ENABLED = False
TELNETCONSOLE_ENABLED = False

# Request headers
DEFAULT_REQUEST_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9,ja;q=0.8',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
}

# Enable middlewares (simplified)
DOWNLOADER_MIDDLEWARES = {
    'travel_scrapers.middlewares.PoliteRetryMiddleware': 543,
}

# Configure item pipelines (simplified)
ITEM_PIPELINES = {
    'travel_scrapers.pipelines.ValidationPipeline': 200,
    'travel_scrapers.pipelines.POINormalizationPipeline': 300,
    'travel_scrapers.pipelines.FieldOrderPipeline': 350,
    'travel_scrapers.pipelines.JSONExportPipeline': 400,
}

# Enable auto-throttling
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1
AUTOTHROTTLE_MAX_DELAY = 5
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.0

# HTTP caching
HTTPCACHE_ENABLED = True
HTTPCACHE_EXPIRATION_SECS = 3600  # 1 hour
HTTPCACHE_DIR = 'output/.httpcache'

# Depth limit for following links
DEPTH_LIMIT = 1

# Logging
LOG_LEVEL = 'INFO'
LOG_FILE = 'output/logs/scrapy.log'

# Retry settings
RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]

# Memory limits
MEMUSAGE_ENABLED = True
MEMUSAGE_LIMIT_MB = 1024
MEMUSAGE_WARNING_MB = 512
