"""
Threat Intelligence Scanner - Block 15 v2
Performs 12-hour internet scans to detect new scam patterns and threats
"""

import os
import re
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging

import requests
from bs4 import BeautifulSoup
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

# Database connection helper
def get_db_connection():
    """Get database connection using DATABASE_URL environment variable"""
    return psycopg2.connect(os.getenv("DATABASE_URL"))

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
    
    def __init__(self):
        """Initialize scanner"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def run_scan(self) -> Dict[str, Any]:
        """
        Run a complete threat intelligence scan cycle
        Returns scan results summary
        """
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            # Create new scan record
            cur.execute("""
                INSERT INTO threat_intelligence_scans (scan_status, scan_timestamp, scan_source)
                VALUES ('running', CURRENT_TIMESTAMP, 'internal')
                RETURNING id
            """)
            scan_id = cur.fetchone()['id']
            conn.commit()
            
            logger.info(f"Starting threat intelligence scan {scan_id}")
            
            # Get active sources
            cur.execute("""
                SELECT id, name, source_type, url, keywords
                FROM threat_intel_sources
                WHERE is_active = true
                ORDER BY priority DESC
            """)
            sources = cur.fetchall()
            
            total_items = 0
            total_patterns = 0
            total_alerts = 0
            
            # Scan each source
            for source in sources:
                try:
                    items = self._scan_source(source, scan_id, conn)
                    total_items += len(items)
                    logger.info(f"Scanned {source['name']}: {len(items)} items")
                except Exception as e:
                    logger.error(f"Error scanning {source['name']}: {str(e)}")
            
            # Detect patterns
            patterns = self._detect_patterns(scan_id, conn)
            total_patterns = len(patterns)
            
            # Generate alerts
            alerts = self._generate_alerts(scan_id, patterns, conn)
            total_alerts = len(alerts)
            
            # Update scan record
            cur.execute("""
                UPDATE threat_intelligence_scans
                SET scan_status = 'completed',
                    completed_at = CURRENT_TIMESTAMP,
                    items_collected = %s,
                    new_patterns_detected = %s
                WHERE id = %s
            """, (total_items, total_patterns, scan_id))
            conn.commit()
            
            cur.close()
            conn.close()
            
            logger.info(f"Scan {scan_id} completed: {total_items} items, {total_patterns} patterns, {total_alerts} alerts")
            
            return {
                "scan_id": scan_id,
                "status": "completed",
                "items_collected": total_items,
                "patterns_detected": total_patterns,
                "alerts_generated": total_alerts
            }
            
        except Exception as e:
            logger.error(f"Scan failed: {str(e)}")
            if 'conn' in locals():
                conn.rollback()
                conn.close()
            raise
    
    def _scan_source(self, source: Dict, scan_id: int, conn) -> List[Dict]:
        """Scan a single source and extract threat data"""
        items = []
        
        try:
            # Fetch content
            response = self.session.get(source['url'], timeout=30)
            response.raise_for_status()
            
            # Parse content
            soup = BeautifulSoup(response.text, 'html.parser')
            text_content = soup.get_text()
            
            # Extract phone numbers
            phones = []
            for pattern in PHONE_PATTERNS:
                phones.extend(re.findall(pattern, text_content))
            phones = list(set(phones))[:10]  # Limit to 10 unique numbers
            
            # Extract URLs
            urls = re.findall(URL_PATTERN, text_content)
            urls = list(set(urls))[:10]  # Limit to 10 unique URLs
            
            # Classify scam type
            scam_type = self._classify_scam_type(text_content)
            
            # Extract keywords
            keywords = self._extract_keywords(text_content, source.get('keywords', []))
            
            # Calculate severity (1-10)
            severity = self._calculate_severity(scam_type, len(phones), len(urls))
            
            # Store item
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("""
                INSERT INTO threat_intelligence_items 
                (scan_id, source_id, scam_type, severity, confidence_score,
                 phone_numbers, urls, keywords, raw_data, collected_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                RETURNING id
            """, (
                scan_id,
                source['id'],
                scam_type,
                severity,
                0.75,  # Default confidence
                json.dumps(phones),
                json.dumps(urls),
                json.dumps(keywords),
                text_content[:5000]  # Limit raw data size
            ))
            item_id = cur.fetchone()['id']
            conn.commit()
            
            items.append({"id": item_id, "scam_type": scam_type, "severity": severity})
            
        except Exception as e:
            logger.error(f"Error scanning source {source['name']}: {str(e)}")
        
        return items
    
    def _classify_scam_type(self, text: str) -> str:
        """Classify scam type based on keywords"""
        text_lower = text.lower()
        
        for scam_type, keywords in SCAM_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return scam_type
        
        return "unknown"
    
    def _extract_keywords(self, text: str, source_keywords: List[str]) -> List[str]:
        """Extract relevant keywords from text"""
        keywords = []
        text_lower = text.lower()
        
        # Check source-specific keywords
        for keyword in source_keywords:
            if keyword.lower() in text_lower:
                keywords.append(keyword)
        
        # Check scam keywords
        for scam_type, scam_keywords in SCAM_KEYWORDS.items():
            for keyword in scam_keywords:
                if keyword in text_lower and keyword not in keywords:
                    keywords.append(keyword)
        
        return keywords[:20]  # Limit to 20 keywords
    
    def _calculate_severity(self, scam_type: str, phone_count: int, url_count: int) -> int:
        """Calculate severity score (1-10)"""
        base_severity = {
            "digital_arrest": 9,
            "upi_fraud": 8,
            "investment_scam": 8,
            "impersonation": 7,
            "social_engineering": 6,
            "phishing": 7,
            "otp_fraud": 8,
            "kyc_fraud": 7,
            "unknown": 5
        }
        
        severity = base_severity.get(scam_type, 5)
        
        # Adjust based on evidence
        if phone_count > 5:
            severity = min(10, severity + 1)
        if url_count > 5:
            severity = min(10, severity + 1)
        
        return severity
    
    def _detect_patterns(self, scan_id: int, conn) -> List[Dict]:
        """Detect recurring patterns in threat data"""
        patterns = []
        
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            # Find recurring phone numbers
            cur.execute("""
                SELECT 
                    jsonb_array_elements_text(phone_numbers::jsonb) as phone,
                    COUNT(*) as occurrence_count,
                    array_agg(DISTINCT scam_type) as scam_types
                FROM threat_intelligence_items
                WHERE scan_id = %s AND phone_numbers != '[]'
                GROUP BY phone
                HAVING COUNT(*) >= 3
            """, (scan_id,))
            
            phone_patterns = cur.fetchall()
            
            for pattern in phone_patterns:
                cur.execute("""
                    INSERT INTO threat_patterns
                    (pattern_type, pattern_value, occurrence_count, scam_types, 
                     first_seen, last_seen, is_active)
                    VALUES ('phone_number', %s, %s, %s, CURRENT_TIMESTAMP, 
                            CURRENT_TIMESTAMP, true)
                    ON CONFLICT (pattern_type, pattern_value) 
                    DO UPDATE SET 
                        occurrence_count = threat_patterns.occurrence_count + EXCLUDED.occurrence_count,
                        last_seen = CURRENT_TIMESTAMP
                    RETURNING id
                """, (pattern['phone'], pattern['occurrence_count'], 
                      json.dumps(pattern['scam_types'])))
                
                pattern_id = cur.fetchone()['id']
                patterns.append({"id": pattern_id, "type": "phone_number"})
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Error detecting patterns: {str(e)}")
        
        return patterns
    
    def _generate_alerts(self, scan_id: int, patterns: List[Dict], conn) -> List[Dict]:
        """Generate alerts for new threats"""
        alerts = []
        
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            # Generate alerts for high-severity items
            cur.execute("""
                SELECT id, scam_type, severity, phone_numbers, urls
                FROM threat_intelligence_items
                WHERE scan_id = %s AND severity >= 8
            """, (scan_id,))
            
            high_severity_items = cur.fetchall()
            
            for item in high_severity_items:
                cur.execute("""
                    INSERT INTO threat_alerts
                    (alert_type, severity, title, description, related_item_ids, 
                     status, created_at)
                    VALUES ('high_severity_threat', %s, %s, %s, %s, 'new', CURRENT_TIMESTAMP)
                    RETURNING id
                """, (
                    item['severity'],
                    f"High Severity {item['scam_type'].replace('_', ' ').title()} Detected",
                    f"New {item['scam_type']} threat detected with severity {item['severity']}",
                    json.dumps([item['id']])
                ))
                
                alert_id = cur.fetchone()['id']
                alerts.append({"id": alert_id, "type": "high_severity_threat"})
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Error generating alerts: {str(e)}")
        
        return alerts


# Standalone function for scheduler
def run_threat_intelligence_scan():
    """Run threat intelligence scan (called by scheduler)"""
    try:
        scanner = ThreatIntelligenceScanner()
        result = scanner.run_scan()
        logger.info(f"Scheduled scan completed: {result}")
        return result
    except Exception as e:
        logger.error(f"Scheduled scan failed: {str(e)}")
        return {"status": "failed", "error": str(e)}
