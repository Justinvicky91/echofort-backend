"""
AI Internet Tools Module
Provides controlled internet access for EchoFort AI through safe external APIs.
All internet activity is logged for audit purposes.
"""

import os
import logging
import requests
from typing import List, Dict, Optional, Any
from datetime import datetime
from bs4 import BeautifulSoup
import psycopg
from psycopg.rows import dict_row

logger = logging.getLogger(__name__)

# Configuration
SEARCH_API_KEY = os.getenv("SEARCH_API_KEY", "")  # e.g., Serper API, SerpAPI, etc.
SEARCH_API_URL = os.getenv("SEARCH_API_URL", "https://google.serper.dev/search")
MAX_FETCH_SIZE = 500000  # 500KB max
FETCH_TIMEOUT = 10  # seconds
MAX_SEARCH_RESULTS = 10

class SearchResult:
    """Represents a single search result"""
    def __init__(self, title: str, summary: str, url: str, source: str, published_at: Optional[str] = None):
        self.title = title
        self.summary = summary
        self.url = url
        self.source = source
        self.published_at = published_at or datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "summary": self.summary,
            "url": self.url,
            "source": self.source,
            "published_at": self.published_at
        }

class FetchedPage:
    """Represents a fetched web page"""
    def __init__(self, url: str, title: str, text_snippet: str):
        self.url = url
        self.title = title
        self.text_snippet = text_snippet
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "text_snippet": self.text_snippet
        }

def log_web_search(user_id: int, query: str, category: Optional[str], results_count: int):
    """Log web search activity to database"""
    try:
        with psycopg.connect(os.getenv("DATABASE_URL")) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO ai_web_logs (user_id, query, category, results_count, created_at)
                    VALUES (%s, %s, %s, %s, %s)
                """, (user_id, query, category, results_count, datetime.utcnow()))
                conn.commit()
    except Exception as e:
        logger.error(f"Failed to log web search: {e}")

def web_search(query: str, category: Optional[str] = None, user_id: int = 1) -> List[SearchResult]:
    """
    Perform a web search using external API.
    
    Args:
        query: Search query string
        category: Optional category filter (scam_fraud, harassment, child_safety, extremism, marketing_competitor, generic)
        user_id: User ID for logging
    
    Returns:
        List of SearchResult objects
    """
    try:
        # Enhance query based on category
        enhanced_query = query
        if category == "scam_fraud":
            enhanced_query = f"{query} scam fraud India cybercrime"
        elif category == "harassment":
            enhanced_query = f"{query} harassment online safety India"
        elif category == "child_safety":
            enhanced_query = f"{query} child safety online protection India"
        elif category == "extremism":
            enhanced_query = f"{query} extremism radicalization online India"
        elif category == "marketing_competitor":
            enhanced_query = f"{query} Truecaller Life360 family safety app"
        
        # Use Serper API (Google Search API)
        headers = {
            "X-API-KEY": SEARCH_API_KEY,
            "Content-Type": "application/json"
        }
        
        payload = {
            "q": enhanced_query,
            "num": MAX_SEARCH_RESULTS,
            "gl": "in",  # India
            "hl": "en"
        }
        
        response = requests.post(
            SEARCH_API_URL,
            json=payload,
            headers=headers,
            timeout=FETCH_TIMEOUT
        )
        
        if response.status_code != 200:
            logger.error(f"Search API error: {response.status_code} - {response.text}")
            log_web_search(user_id, query, category, 0)
            return []
        
        data = response.json()
        results = []
        
        # Parse organic results
        for item in data.get("organic", [])[:MAX_SEARCH_RESULTS]:
            result = SearchResult(
                title=item.get("title", ""),
                summary=item.get("snippet", ""),
                url=item.get("link", ""),
                source=item.get("domain", ""),
                published_at=item.get("date", datetime.utcnow().isoformat())
            )
            results.append(result)
        
        # Parse news results if available
        for item in data.get("news", [])[:3]:
            result = SearchResult(
                title=item.get("title", ""),
                summary=item.get("snippet", ""),
                url=item.get("link", ""),
                source=item.get("source", ""),
                published_at=item.get("date", datetime.utcnow().isoformat())
            )
            results.append(result)
        
        log_web_search(user_id, query, category, len(results))
        return results
        
    except requests.exceptions.Timeout:
        logger.error(f"Search timeout for query: {query}")
        log_web_search(user_id, query, category, 0)
        return []
    except Exception as e:
        logger.error(f"Search error: {e}")
        log_web_search(user_id, query, category, 0)
        return []

def web_fetch(url: str, user_id: int = 1) -> Optional[FetchedPage]:
    """
    Fetch and extract content from a URL.
    
    Args:
        url: URL to fetch (must be https://)
        user_id: User ID for logging
    
    Returns:
        FetchedPage object or None if failed
    """
    try:
        # Security: Only allow HTTPS
        if not url.startswith("https://"):
            logger.warning(f"Blocked non-HTTPS URL: {url}")
            return None
        
        # Fetch with timeout and size limit
        response = requests.get(
            url,
            timeout=FETCH_TIMEOUT,
            headers={
                "User-Agent": "EchoFort-AI/1.0 (Security Research Bot)"
            },
            stream=True
        )
        
        # Check content length
        content_length = response.headers.get('content-length')
        if content_length and int(content_length) > MAX_FETCH_SIZE:
            logger.warning(f"Content too large: {url} ({content_length} bytes)")
            return None
        
        # Read content with size limit
        content = b""
        for chunk in response.iter_content(chunk_size=8192):
            content += chunk
            if len(content) > MAX_FETCH_SIZE:
                logger.warning(f"Content exceeded limit during download: {url}")
                return None
        
        # Parse HTML
        soup = BeautifulSoup(content, 'html.parser')
        
        # Extract title
        title = soup.title.string if soup.title else url
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
        
        # Get text content
        text = soup.get_text()
        
        # Clean up text
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        # Limit to first 3000 characters
        text_snippet = text[:3000] if len(text) > 3000 else text
        
        return FetchedPage(
            url=url,
            title=title,
            text_snippet=text_snippet
        )
        
    except requests.exceptions.Timeout:
        logger.error(f"Fetch timeout for URL: {url}")
        return None
    except Exception as e:
        logger.error(f"Fetch error for {url}: {e}")
        return None

def get_recent_web_logs(user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
    """Get recent web search logs for a user"""
    try:
        with psycopg.connect(os.getenv("DATABASE_URL")) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute("""
                    SELECT id, query, category, results_count, created_at
                    FROM ai_web_logs
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                """, (user_id, limit))
                return cur.fetchall()
    except Exception as e:
        logger.error(f"Failed to get web logs: {e}")
        return []
