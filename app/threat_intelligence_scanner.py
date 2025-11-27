"""
Threat Intelligence Scanner - Block 15
Performs 12-hour internet scans to detect new scam patterns and threats
"""

import os
import re
import json
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging

import requests
from bs4 import BeautifulSoup
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db

logger = logging.getLogger(__name__)

# Scam type keywords for classification
SCAM_KEYWORDS = {
    "digital_arrest": ["digital arrest", "cyber police", "cbi call", "courier scam", "customs fraud", "parcel scam"],
    "upi_fraud": ["upi fraud", "payment link", "qr code scam", "refund scam", "wrong transfer", "paytm fraud"],
    "investment_scam": ["trading scam", "crypto fraud", "ponzi scheme", "investment fraud", "fake broker", "stock scam"],
    "impersonation": ["fake officer", "bank employee scam", "tech support fraud", "government impersonation"],
    "social_engineering": ["romance scam", "job fraud", "lottery scam", "prize scam", "donation fraud"],
    "phishing": ["phishing", "fake website", "clone site", "credential theft", "fake login"],
    "otp_fraud": ["otp scam", "otp sharing", "verification code", "one time password fraud"],
    "kyc_fraud": ["kyc update", "kyc verification scam", "aadhaar fraud", "pan card scam"]
}

# Phone number patterns
PHONE_PATTERNS = [
    r'\+91[\s-]?\d{10}',  # +91 followed by 10 digits
    r'91[\s-]?\d{10}',     # 91 followed by 10 digits
    r'\b[6-9]\d{9}\b',     # 10-digit Indian mobile number
    r'\d{3}[\s-]?\d{3}[\s-]?\d{4}'  # Formatted phone numbers
]

# URL patterns
URL_PATTERN = r'https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&/=]*)'


class ThreatIntelligenceScanner:
    """Main scanner class for threat intelligence collection"""
    
    def __init__(self, db: Session):
        self.db = db
        self.scan_id = None
        self.items_collected = 0
        self.new_patterns = 0
    
    async def run_12hour_scan(self) -> Dict[str, Any]:
        """
        Main orchestrator for 12-hour scan cycle
        Runs all configured sources and processes results
        """
        logger.info("Starting 12-hour threat intelligence scan")
        
        # Get enabled sources
        sources = self.get_enabled_sources()
        
        all_results = []
        
        for source in sources:
            try:
                logger.info(f"Scanning source: {source['source_name']}")
                
                # Create scan record
                scan_id = self.create_scan_record(source['source_name'], source['source_type'])
                self.scan_id = scan_id
                
                # Run appropriate scanner based on source type
                if source['source_type'] == 'twitter':
                    results = await self.scrape_twitter(source)
                elif source['source_type'] == 'news':
                    results = await self.scrape_news(source)
                elif source['source_type'] == 'government':
                    results = await self.scrape_government(source)
                elif source['source_type'] == 'reddit':
                    results = await self.scrape_reddit(source)
                else:
                    logger.warning(f"Unknown source type: {source['source_type']}")
                    continue
                
                # Process and store results
                await self.process_scan_results(scan_id, results, source)
                
                # Mark scan as completed
                self.complete_scan_record(scan_id, len(results))
                
                all_results.extend(results)
                
            except Exception as e:
                logger.error(f"Error scanning {source['source_name']}: {e}")
                if self.scan_id:
                    self.fail_scan_record(self.scan_id, str(e))
        
        # Detect patterns from all collected data
        await self.detect_patterns()
        
        # Generate alerts for new threats
        await self.generate_alerts()
        
        # Update statistics
        await self.update_statistics()
        
        logger.info(f"Scan complete. Collected {len(all_results)} items, detected {self.new_patterns} new patterns")
        
        return {
            "success": True,
            "items_collected": len(all_results),
            "new_patterns": self.new_patterns,
            "sources_scanned": len(sources)
        }
    
    def get_enabled_sources(self) -> List[Dict[str, Any]]:
        """Get list of enabled threat intelligence sources"""
        query = text("""
            SELECT id, source_name, source_type, source_url, source_config
            FROM threat_intel_sources
            WHERE is_enabled = TRUE
            ORDER BY source_name
        """)
        result = self.db.execute(query)
        return [dict(row._mapping) for row in result]
    
    def create_scan_record(self, source_name: str, source_type: str) -> int:
        """Create a new scan record and return scan_id"""
        query = text("""
            INSERT INTO threat_intelligence_scans (scan_source, scan_status, scan_timestamp)
            VALUES (:source, 'running', CURRENT_TIMESTAMP)
            RETURNING id
        """)
        result = self.db.execute(query, {"source": f"{source_type}:{source_name}"})
        self.db.commit()
        return result.scalar()
    
    def complete_scan_record(self, scan_id: int, items_count: int):
        """Mark scan as completed"""
        query = text("""
            UPDATE threat_intelligence_scans
            SET scan_status = 'completed',
                items_collected = :items,
                completed_at = CURRENT_TIMESTAMP,
                scan_duration_seconds = EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - scan_timestamp))
            WHERE id = :scan_id
        """)
        self.db.execute(query, {"scan_id": scan_id, "items": items_count})
        self.db.commit()
    
    def fail_scan_record(self, scan_id: int, error_message: str):
        """Mark scan as failed"""
        query = text("""
            UPDATE threat_intelligence_scans
            SET scan_status = 'failed',
                error_message = :error,
                completed_at = CURRENT_TIMESTAMP
            WHERE id = :scan_id
        """)
        self.db.execute(query, {"scan_id": scan_id, "error": error_message})
        self.db.commit()
    
    async def scrape_twitter(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Scrape Twitter/X for scam reports
        Note: This is a simplified version. Production would use Twitter API or advanced scraping.
        """
        results = []
        
        # In production, use Twitter API (tweepy) or advanced scraping
        # For now, return mock data structure
        logger.info("Twitter scraping would happen here (requires API key)")
        
        # Example structure of what would be returned:
        # results.append({
        #     "source_url": "https://twitter.com/user/status/123",
        #     "content_text": "Beware! Got a call from +91 9876543210 claiming to be CBI...",
        #     "timestamp": datetime.now(),
        #     "author": "@user"
        # })
        
        return results
    
    async def scrape_news(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Scrape news sites for cybercrime reports"""
        results = []
        
        try:
            # Google News search for Indian cybercrime
            search_url = "https://www.google.com/search?q=cybercrime+india+scam&tbm=nws&hl=en"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            response = requests.get(search_url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract news articles (simplified)
            articles = soup.find_all('div', class_='SoaBEf')
            
            for article in articles[:10]:  # Limit to 10 articles
                try:
                    title_elem = article.find('div', class_='mCBkyc')
                    link_elem = article.find('a')
                    
                    if title_elem and link_elem:
                        results.append({
                            "source_url": link_elem.get('href', ''),
                            "content_text": title_elem.get_text(strip=True),
                            "timestamp": datetime.now(),
                            "source": "Google News"
                        })
                except Exception as e:
                    logger.error(f"Error parsing article: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error scraping news: {e}")
        
        return results
    
    async def scrape_government(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Scrape government cybercrime portals"""
        results = []
        
        try:
            url = source.get('source_url')
            if not url:
                return results
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            response = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract alerts/advisories (structure depends on site)
            # This is a generic approach
            alerts = soup.find_all(['div', 'article'], class_=re.compile(r'alert|advisory|notice'))
            
            for alert in alerts[:20]:  # Limit to 20 items
                text = alert.get_text(strip=True)
                if len(text) > 50:  # Only meaningful content
                    results.append({
                        "source_url": url,
                        "content_text": text[:1000],  # Limit length
                        "timestamp": datetime.now(),
                        "source": source['source_name']
                    })
        
        except Exception as e:
            logger.error(f"Error scraping government site: {e}")
        
        return results
    
    async def scrape_reddit(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Scrape Reddit for scam reports
        Note: Production would use Reddit API (PRAW)
        """
        results = []
        
        # In production, use PRAW (Python Reddit API Wrapper)
        # For now, return mock structure
        logger.info("Reddit scraping would happen here (requires API credentials)")
        
        return results
    
    async def process_scan_results(self, scan_id: int, results: List[Dict[str, Any]], source: Dict[str, Any]):
        """Process and store scan results"""
        for item in results:
            try:
                # Extract phone numbers
                phones = self.extract_phone_numbers(item['content_text'])
                
                # Extract URLs
                urls = self.extract_urls(item['content_text'])
                
                # Extract keywords
                keywords = self.extract_keywords(item['content_text'])
                
                # Classify scam type
                scam_type = self.classify_scam_type(item['content_text'], keywords)
                
                # Calculate severity
                severity = self.calculate_severity(item['content_text'], phones, urls, scam_type)
                
                # Store item
                query = text("""
                    INSERT INTO threat_intelligence_items (
                        scan_id, source_url, source_type, content_text,
                        extracted_phone_numbers, extracted_urls, extracted_keywords,
                        scam_type, severity_score, confidence_score, created_at
                    ) VALUES (
                        :scan_id, :url, :source_type, :content,
                        :phones, :urls, :keywords,
                        :scam_type, :severity, :confidence, CURRENT_TIMESTAMP
                    )
                """)
                
                self.db.execute(query, {
                    "scan_id": scan_id,
                    "url": item.get('source_url', ''),
                    "source_type": source['source_type'],
                    "content": item['content_text'][:5000],  # Limit length
                    "phones": json.dumps(phones),
                    "urls": json.dumps(urls),
                    "keywords": json.dumps(keywords),
                    "scam_type": scam_type,
                    "severity": severity,
                    "confidence": 0.75  # Default confidence
                })
                
                self.items_collected += 1
            
            except Exception as e:
                logger.error(f"Error processing item: {e}")
                continue
        
        self.db.commit()
    
    def extract_phone_numbers(self, text: str) -> List[str]:
        """Extract phone numbers from text"""
        phones = []
        for pattern in PHONE_PATTERNS:
            matches = re.findall(pattern, text)
            phones.extend(matches)
        
        # Clean and deduplicate
        phones = list(set([re.sub(r'[\s-]', '', p) for p in phones]))
        return phones[:10]  # Limit to 10
    
    def extract_urls(self, text: str) -> List[str]:
        """Extract URLs from text"""
        urls = re.findall(URL_PATTERN, text)
        return list(set(urls))[:10]  # Limit to 10
    
    def extract_keywords(self, text: str) -> List[str]:
        """Extract scam-related keywords from text"""
        text_lower = text.lower()
        keywords = []
        
        for scam_type, keyword_list in SCAM_KEYWORDS.items():
            for keyword in keyword_list:
                if keyword in text_lower:
                    keywords.append(keyword)
        
        return list(set(keywords))
    
    def classify_scam_type(self, text: str, keywords: List[str]) -> Optional[str]:
        """Classify scam type based on keywords"""
        text_lower = text.lower()
        
        # Count matches for each scam type
        type_scores = {}
        for scam_type, keyword_list in SCAM_KEYWORDS.items():
            score = sum(1 for kw in keyword_list if kw in text_lower)
            if score > 0:
                type_scores[scam_type] = score
        
        # Return type with highest score
        if type_scores:
            return max(type_scores, key=type_scores.get)
        
        return None
    
    def calculate_severity(self, text: str, phones: List[str], urls: List[str], scam_type: Optional[str]) -> int:
        """Calculate severity score (1-10)"""
        severity = 5  # Base severity
        
        # Increase for specific scam types
        high_severity_types = ["digital_arrest", "investment_scam", "phishing"]
        if scam_type in high_severity_types:
            severity += 2
        
        # Increase if phone numbers present
        if phones:
            severity += 1
        
        # Increase if URLs present
        if urls:
            severity += 1
        
        # Increase for urgent language
        urgent_words = ["urgent", "immediately", "arrest", "legal action", "account blocked"]
        if any(word in text.lower() for word in urgent_words):
            severity += 1
        
        return min(severity, 10)  # Cap at 10
    
    async def detect_patterns(self):
        """Detect new patterns from collected threat intelligence"""
        # Get recent items (last 24 hours)
        query = text("""
            SELECT scam_type, extracted_phone_numbers, extracted_urls, extracted_keywords
            FROM threat_intelligence_items
            WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '24 hours'
            AND scam_type IS NOT NULL
        """)
        
        result = self.db.execute(query)
        items = [dict(row._mapping) for row in result]
        
        # Group by scam type and look for patterns
        scam_groups = {}
        for item in items:
            scam_type = item['scam_type']
            if scam_type not in scam_groups:
                scam_groups[scam_type] = []
            scam_groups[scam_type].append(item)
        
        # Detect patterns for each scam type
        for scam_type, group_items in scam_groups.items():
            if len(group_items) >= 3:  # Need at least 3 occurrences
                # Check if pattern already exists
                check_query = text("""
                    SELECT id FROM threat_patterns
                    WHERE scam_type = :scam_type AND is_active = TRUE
                    LIMIT 1
                """)
                existing = self.db.execute(check_query, {"scam_type": scam_type}).first()
                
                if not existing:
                    # Create new pattern
                    pattern_data = {
                        "scam_type": scam_type,
                        "occurrence_count": len(group_items),
                        "sample_keywords": list(set([kw for item in group_items for kw in json.loads(item['extracted_keywords'] or '[]')]))[:10]
                    }
                    
                    insert_query = text("""
                        INSERT INTO threat_patterns (
                            pattern_type, pattern_name, pattern_description, pattern_data,
                            scam_type, severity_level, confidence_score, occurrence_count
                        ) VALUES (
                            'scam_pattern', :name, :description, :data,
                            :scam_type, 'medium', 0.75, :count
                        )
                    """)
                    
                    self.db.execute(insert_query, {
                        "name": f"{scam_type.replace('_', ' ').title()} Pattern",
                        "description": f"Detected pattern for {scam_type} scams",
                        "data": json.dumps(pattern_data),
                        "scam_type": scam_type,
                        "count": len(group_items)
                    })
                    
                    self.new_patterns += 1
        
        self.db.commit()
    
    async def generate_alerts(self):
        """Generate alerts for new or escalating threats"""
        # Check for new patterns detected today
        query = text("""
            SELECT id, pattern_name, scam_type, severity_level, occurrence_count
            FROM threat_patterns
            WHERE DATE(first_seen) = CURRENT_DATE
            AND is_active = TRUE
        """)
        
        result = self.db.execute(query)
        new_patterns = [dict(row._mapping) for row in result]
        
        for pattern in new_patterns:
            # Create alert
            alert_query = text("""
                INSERT INTO threat_alerts (
                    pattern_id, alert_type, alert_title, alert_message,
                    alert_severity, affected_users_count, recommended_actions
                ) VALUES (
                    :pattern_id, 'new_pattern', :title, :message,
                    :severity, 0, :actions
                )
            """)
            
            self.db.execute(alert_query, {
                "pattern_id": pattern['id'],
                "title": f"New Threat Pattern Detected: {pattern['pattern_name']}",
                "message": f"A new {pattern['scam_type']} pattern has been detected with {pattern['occurrence_count']} occurrences.",
                "severity": pattern['severity_level'],
                "actions": json.dumps([
                    "Review threat intelligence items",
                    "Update call screening rules",
                    "Notify users via app"
                ])
            })
        
        self.db.commit()
    
    async def update_statistics(self):
        """Update daily statistics"""
        query = text("SELECT generate_threat_intel_daily_stats(CURRENT_DATE)")
        self.db.execute(query)
        self.db.commit()


async def run_scheduled_scan():
    """Entry point for scheduled 12-hour scan"""
    db = next(get_db())
    try:
        scanner = ThreatIntelligenceScanner(db)
        result = await scanner.run_12hour_scan()
        logger.info(f"Scheduled scan completed: {result}")
        return result
    except Exception as e:
        logger.error(f"Scheduled scan failed: {e}")
        raise
    finally:
        db.close()
