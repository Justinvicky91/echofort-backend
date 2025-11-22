"""
EchoFort Load Testing with Locust
Tests API performance under load (1000+ concurrent users)
"""

from locust import HttpUser, task, between
import json
import random

class EchoFortUser(HttpUser):
    """Simulates a typical EchoFort user"""
    
    wait_time = between(1, 5)  # Wait 1-5 seconds between tasks
    host = "https://api.echofort.ai"
    
    def on_start(self):
        """Called when a user starts - authenticate"""
        self.access_token = None
        # In real scenario, authenticate here
        # For load testing, we'll test public endpoints
    
    @task(10)
    def health_check(self):
        """Test health check endpoint (most frequent)"""
        self.client.get("/health")
    
    @task(5)
    def get_legal_terms(self):
        """Test legal terms endpoint"""
        self.client.get("/legal/terms")
    
    @task(5)
    def get_legal_privacy(self):
        """Test privacy policy endpoint"""
        self.client.get("/legal/privacy")
    
    @task(3)
    def api_ping(self):
        """Test API ping"""
        self.client.get("/test/ping")
    
    @task(2)
    def get_public_stats(self):
        """Test public stats endpoint"""
        self.client.get("/api/public/stats")
    
    @task(1)
    def get_openapi_spec(self):
        """Test OpenAPI spec (least frequent)"""
        self.client.get("/openapi.json")


class AuthenticatedUser(HttpUser):
    """Simulates an authenticated user (requires JWT)"""
    
    wait_time = between(2, 8)
    host = "https://api.echofort.ai"
    
    def on_start(self):
        """Authenticate user"""
        # TODO: Implement actual authentication
        self.access_token = "test_token"
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    @task(5)
    def get_user_profile(self):
        """Test user profile endpoint"""
        self.client.get("/api/user/profile", headers=self.headers)
    
    @task(3)
    def get_subscription_status(self):
        """Test subscription status"""
        self.client.get("/subscription/status", headers=self.headers)
    
    @task(4)
    def save_gps_location(self):
        """Test GPS location save"""
        self.client.post(
            "/gps/location",
            headers=self.headers,
            json={
                "latitude": random.uniform(8.0, 37.0),
                "longitude": random.uniform(68.0, 97.0),
                "accuracy": random.uniform(5.0, 50.0)
            }
        )
    
    @task(2)
    def log_screen_time(self):
        """Test screen time logging"""
        apps = ["Instagram", "WhatsApp", "YouTube", "Facebook", "Twitter"]
        self.client.post(
            "/screentime/log",
            headers=self.headers,
            json={
                "app_name": random.choice(apps),
                "duration_minutes": random.randint(5, 120)
            }
        )
    
    @task(1)
    def get_family_members(self):
        """Test family members list"""
        self.client.get("/family/members", headers=self.headers)


# Load test scenarios
# Run with: locust -f locustfile.py --host=https://api.echofort.ai

# Scenario 1: Light load (100 users)
# locust -f locustfile.py --users 100 --spawn-rate 10 --run-time 5m

# Scenario 2: Medium load (500 users)
# locust -f locustfile.py --users 500 --spawn-rate 50 --run-time 10m

# Scenario 3: Heavy load (1000 users)
# locust -f locustfile.py --users 1000 --spawn-rate 100 --run-time 15m

# Scenario 4: Stress test (2000 users)
# locust -f locustfile.py --users 2000 --spawn-rate 200 --run-time 20m
