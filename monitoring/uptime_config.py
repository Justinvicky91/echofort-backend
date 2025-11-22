"""
EchoFort Uptime Monitoring Configuration
Monitors API availability and response times
"""

import requests
import time
from datetime import datetime
import json
import os

class UptimeMonitor:
    """Monitor API uptime and performance"""
    
    def __init__(self):
        self.base_url = os.getenv("API_BASE_URL", "https://api.echofort.ai")
        self.alert_webhook = os.getenv("ALERT_WEBHOOK_URL")
        self.check_interval = 60  # Check every 60 seconds
        self.timeout = 10  # 10 second timeout
        
        self.endpoints_to_monitor = [
            {
                "name": "Health Check",
                "path": "/health",
                "method": "GET",
                "expected_status": 200,
                "critical": True,
            },
            {
                "name": "API Ping",
                "path": "/test/ping",
                "method": "GET",
                "expected_status": 200,
                "critical": True,
            },
            {
                "name": "Legal Terms",
                "path": "/legal/terms",
                "method": "GET",
                "expected_status": 200,
                "critical": False,
            },
            {
                "name": "OpenAPI Spec",
                "path": "/openapi.json",
                "method": "GET",
                "expected_status": 200,
                "critical": False,
            },
        ]
        
        self.status_history = []
        self.downtime_start = None
    
    def check_endpoint(self, endpoint):
        """Check a single endpoint"""
        url = f"{self.base_url}{endpoint['path']}"
        
        try:
            start_time = time.time()
            
            if endpoint['method'] == 'GET':
                response = requests.get(url, timeout=self.timeout)
            elif endpoint['method'] == 'POST':
                response = requests.post(url, json={}, timeout=self.timeout)
            else:
                return None
            
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            
            status = {
                "name": endpoint['name'],
                "path": endpoint['path'],
                "status_code": response.status_code,
                "response_time_ms": round(response_time, 2),
                "timestamp": datetime.now().isoformat(),
                "is_up": response.status_code == endpoint['expected_status'],
                "critical": endpoint['critical'],
            }
            
            return status
        
        except requests.exceptions.Timeout:
            return {
                "name": endpoint['name'],
                "path": endpoint['path'],
                "status_code": 0,
                "response_time_ms": self.timeout * 1000,
                "timestamp": datetime.now().isoformat(),
                "is_up": False,
                "critical": endpoint['critical'],
                "error": "Timeout",
            }
        
        except requests.exceptions.ConnectionError:
            return {
                "name": endpoint['name'],
                "path": endpoint['path'],
                "status_code": 0,
                "response_time_ms": 0,
                "timestamp": datetime.now().isoformat(),
                "is_up": False,
                "critical": endpoint['critical'],
                "error": "Connection Error",
            }
        
        except Exception as e:
            return {
                "name": endpoint['name'],
                "path": endpoint['path'],
                "status_code": 0,
                "response_time_ms": 0,
                "timestamp": datetime.now().isoformat(),
                "is_up": False,
                "critical": endpoint['critical'],
                "error": str(e),
            }
    
    def check_all_endpoints(self):
        """Check all monitored endpoints"""
        results = []
        
        for endpoint in self.endpoints_to_monitor:
            status = self.check_endpoint(endpoint)
            if status:
                results.append(status)
                self.status_history.append(status)
        
        # Keep only last 1000 checks
        if len(self.status_history) > 1000:
            self.status_history = self.status_history[-1000:]
        
        return results
    
    def send_alert(self, message, severity="warning"):
        """Send alert to webhook"""
        if not self.alert_webhook:
            print(f"⚠️  Alert: {message}")
            return
        
        try:
            payload = {
                "text": f"🚨 EchoFort Alert [{severity.upper()}]",
                "attachments": [{
                    "color": "danger" if severity == "critical" else "warning",
                    "text": message,
                    "ts": int(time.time())
                }]
            }
            
            requests.post(self.alert_webhook, json=payload, timeout=5)
        
        except Exception as e:
            print(f"Failed to send alert: {e}")
    
    def analyze_results(self, results):
        """Analyze check results and send alerts if needed"""
        critical_down = [r for r in results if not r['is_up'] and r['critical']]
        
        if critical_down:
            if not self.downtime_start:
                self.downtime_start = datetime.now()
            
            downtime_duration = (datetime.now() - self.downtime_start).total_seconds()
            
            message = f"Critical endpoints down for {downtime_duration:.0f} seconds:\n"
            for result in critical_down:
                error = result.get('error', 'Unknown error')
                message += f"- {result['name']} ({result['path']}): {error}\n"
            
            self.send_alert(message, severity="critical")
        
        else:
            if self.downtime_start:
                downtime_duration = (datetime.now() - self.downtime_start).total_seconds()
                message = f"✅ All critical endpoints back online after {downtime_duration:.0f} seconds downtime"
                self.send_alert(message, severity="info")
                self.downtime_start = None
        
        # Check response times
        slow_endpoints = [r for r in results if r.get('response_time_ms', 0) > 2000]
        if slow_endpoints:
            message = "⚠️  Slow response times detected:\n"
            for result in slow_endpoints:
                message += f"- {result['name']}: {result['response_time_ms']:.0f}ms\n"
            self.send_alert(message, severity="warning")
    
    def get_uptime_percentage(self, hours=24):
        """Calculate uptime percentage for last N hours"""
        if not self.status_history:
            return 100.0
        
        cutoff_time = datetime.now().timestamp() - (hours * 3600)
        recent_checks = [
            s for s in self.status_history
            if datetime.fromisoformat(s['timestamp']).timestamp() > cutoff_time
        ]
        
        if not recent_checks:
            return 100.0
        
        up_count = sum(1 for s in recent_checks if s['is_up'])
        return (up_count / len(recent_checks)) * 100
    
    def get_average_response_time(self, hours=24):
        """Calculate average response time for last N hours"""
        if not self.status_history:
            return 0.0
        
        cutoff_time = datetime.now().timestamp() - (hours * 3600)
        recent_checks = [
            s for s in self.status_history
            if datetime.fromisoformat(s['timestamp']).timestamp() > cutoff_time
            and s['is_up']
        ]
        
        if not recent_checks:
            return 0.0
        
        total_time = sum(s['response_time_ms'] for s in recent_checks)
        return total_time / len(recent_checks)
    
    def run_continuous_monitoring(self):
        """Run continuous monitoring loop"""
        print(f"🔍 Starting uptime monitoring for {self.base_url}")
        print(f"📊 Monitoring {len(self.endpoints_to_monitor)} endpoints")
        print(f"⏱️  Check interval: {self.check_interval} seconds\n")
        
        while True:
            try:
                results = self.check_all_endpoints()
                self.analyze_results(results)
                
                # Print status
                up_count = sum(1 for r in results if r['is_up'])
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                      f"Status: {up_count}/{len(results)} endpoints up | "
                      f"Uptime: {self.get_uptime_percentage():.2f}% | "
                      f"Avg Response: {self.get_average_response_time():.0f}ms")
                
                time.sleep(self.check_interval)
            
            except KeyboardInterrupt:
                print("\n\n✅ Monitoring stopped")
                break
            
            except Exception as e:
                print(f"❌ Monitoring error: {e}")
                time.sleep(self.check_interval)


# Monitoring configuration for different services

MONITORING_CONFIG = {
    "uptime_robot": {
        "name": "UptimeRobot",
        "url": "https://uptimerobot.com",
        "monitors": [
            {
                "name": "EchoFort API Health",
                "url": "https://api.echofort.ai/health",
                "type": "HTTP",
                "interval": 300,  # 5 minutes
            },
            {
                "name": "EchoFort Website",
                "url": "https://echofort.ai",
                "type": "HTTP",
                "interval": 300,
            },
        ]
    },
    
    "pingdom": {
        "name": "Pingdom",
        "url": "https://pingdom.com",
        "checks": [
            {
                "name": "API Health Check",
                "url": "https://api.echofort.ai/health",
                "interval": 60,  # 1 minute
                "locations": ["us-east", "eu-west", "asia-south"],
            }
        ]
    },
    
    "betteruptime": {
        "name": "Better Uptime",
        "url": "https://betteruptime.com",
        "monitors": [
            {
                "name": "EchoFort API",
                "url": "https://api.echofort.ai/health",
                "interval": 30,  # 30 seconds
                "expected_status_codes": [200],
            }
        ]
    }
}


if __name__ == "__main__":
    monitor = UptimeMonitor()
    monitor.run_continuous_monitoring()
