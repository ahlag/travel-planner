# Define here the models for your spider middleware
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/spider-middleware.html

import time
import random
from scrapy.downloadermiddlewares.retry import RetryMiddleware


class PoliteRetryMiddleware(RetryMiddleware):
    """
    Enhanced retry middleware with longer delays for rate limiting
    """
    
    def process_response(self, request, response, spider):
        if response.status in [429, 503]:  # Rate limited or service unavailable
            spider.logger.info(f"Rate limited for {request.url}, waiting longer...")
            time.sleep(10)  # Wait 10 seconds before retry
            
        return super().process_response(request, response, spider)


class RandomDelayMiddleware:
    """
    Add random delays between requests to appear more human-like
    """
    
    def __init__(self, delay_range=(0.5, 2.0)):
        self.delay_range = delay_range
    
    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            delay_range=crawler.settings.getfloat('RANDOM_DELAY_RANGE', (0.5, 2.0))
        )
    
    def process_request(self, request, spider):
        delay = random.uniform(*self.delay_range)
        time.sleep(delay)
        return None
