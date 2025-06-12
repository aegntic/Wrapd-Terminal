#!/usr/bin/env python3
"""
Crawl all documentation from https://docs.warp.dev/ using crawl4ai
"""

import asyncio
import json
import os
import re
from urllib.parse import urljoin, urlparse
from pathlib import Path
from crawl4ai import AsyncWebCrawler
import aiohttp

class WarpDocsCrawler:
    def __init__(self, base_url="https://docs.warp.dev/", output_dir="warp_docs"):
        self.base_url = base_url
        self.output_dir = Path(output_dir)
        self.crawled_urls = set()
        self.all_links = set()
        
        # Create output directory
        self.output_dir.mkdir(exist_ok=True)
        
    def is_docs_url(self, url):
        """Check if URL belongs to warp docs"""
        parsed = urlparse(url)
        return parsed.netloc == 'docs.warp.dev'
    
    def sanitize_filename(self, url):
        """Convert URL to safe filename"""
        parsed = urlparse(url)
        path = parsed.path.strip('/')
        if not path:
            path = 'index'
        # Replace special characters
        filename = re.sub(r'[^\w\-_/]', '_', path)
        return filename + '.md'
    
    async def extract_links(self, html_content, base_url):
        """Extract all documentation links from HTML content"""
        # Simple regex to find links - could be improved with BeautifulSoup
        link_pattern = r'href=["\']([^"\']+)["\']'
        links = re.findall(link_pattern, html_content)
        
        valid_links = set()
        for link in links:
            if link.startswith('/'):
                full_url = urljoin(base_url, link)
            elif link.startswith('http'):
                full_url = link
            else:
                full_url = urljoin(base_url, link)
            
            if self.is_docs_url(full_url) and '#' not in full_url:
                valid_links.add(full_url)
        
        return valid_links
    
    async def crawl_page(self, crawler, url):
        """Crawl a single page and extract content"""
        if url in self.crawled_urls:
            return
        
        print(f"Crawling: {url}")
        self.crawled_urls.add(url)
        
        try:
            result = await crawler.arun(
                url=url,
                word_count_threshold=10,
                bypass_cache=True
            )
            
            if result.success:
                # Extract links for further crawling
                new_links = await self.extract_links(result.html, url)
                self.all_links.update(new_links)
                
                # Save content
                filename = self.sanitize_filename(url)
                file_path = self.output_dir / filename
                
                # Create subdirectories if needed
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Prepare content with metadata
                content = f"# {url}\n\n"
                content += f"**Crawled on:** {asyncio.get_event_loop().time()}\n\n"
                content += f"## Content\n\n{result.markdown}\n\n"
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print(f"Saved: {filename}")
                
            else:
                print(f"Failed to crawl {url}: {result.error_message}")
                
        except Exception as e:
            print(f"Error crawling {url}: {e}")
    
    async def crawl_all(self, max_pages=100):
        """Crawl all documentation pages"""
        async with AsyncWebCrawler(verbose=True) as crawler:
            # Start with the main page
            await self.crawl_page(crawler, self.base_url)
            
            # Crawl discovered links
            pages_crawled = 1
            while self.all_links and pages_crawled < max_pages:
                # Get next uncrawled URL
                remaining_links = self.all_links - self.crawled_urls
                if not remaining_links:
                    break
                
                url = remaining_links.pop()
                await self.crawl_page(crawler, url)
                pages_crawled += 1
                
                # Small delay to be respectful
                await asyncio.sleep(1)
            
            print(f"\nCrawling complete! Processed {pages_crawled} pages")
            print(f"Output saved to: {self.output_dir}")
            
            # Save crawling summary
            summary = {
                'base_url': self.base_url,
                'pages_crawled': pages_crawled,
                'urls_crawled': list(self.crawled_urls),
                'total_links_found': len(self.all_links)
            }
            
            with open(self.output_dir / 'crawl_summary.json', 'w') as f:
                json.dump(summary, f, indent=2)

async def main():
    crawler = WarpDocsCrawler()
    await crawler.crawl_all(max_pages=200)  # Adjust as needed

if __name__ == "__main__":
    asyncio.run(main())