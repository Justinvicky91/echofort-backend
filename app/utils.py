import jwt, hashlib
from .deps import get_settings

def jwt_encode(payload: dict) -> str:
    s = get_settings()
    return jwt.encode(payload, s.JWT_SECRET, algorithm="HS256")

def jwt_decode(token: str) -> dict:
    s = get_settings()
    return jwt.decode(token, s.JWT_SECRET, algorithms=["HS256"])

def trial_fingerprint(device_id: str, identity: str, payment_last4: str, ip_block: str) -> str:
    raw = f"{device_id}|{identity}|{payment_last4}|{ip_block}"
    return hashlib.sha256(raw.encode()).hexdigest()

def ai_cost_ok(monthly_so_far_rs: float, estimated_rs: float) -> bool:
    s = get_settings()
    return (monthly_so_far_rs + estimated_rs) <= s.AI_MONTHLY_CAP_RS

def is_admin(user_id: int) -> bool:
    s = get_settings()
    return str(user_id) in set(x.strip() for x in s.ADMIN_USER_IDS_CSV.split(","))
