-- GPS and Family Safety Module
-- Location tracking, geofencing, and family protection features

-- GPS Locations Table
CREATE TABLE IF NOT EXISTS gps_locations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    accuracy DECIMAL(10, 2) DEFAULT 0,
    altitude DECIMAL(10, 2),
    speed DECIMAL(10, 2),
    heading DECIMAL(5, 2),
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_gps_locations_user ON gps_locations(user_id);
CREATE INDEX IF NOT EXISTS idx_gps_locations_recorded ON gps_locations(recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_gps_locations_user_recorded ON gps_locations(user_id, recorded_at DESC);

-- Geofences Table
CREATE TABLE IF NOT EXISTS geofences (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    radius_meters INTEGER NOT NULL DEFAULT 100,
    is_active BOOLEAN DEFAULT TRUE,
    alert_on_enter BOOLEAN DEFAULT FALSE,
    alert_on_exit BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_geofences_user ON geofences(user_id);
CREATE INDEX IF NOT EXISTS idx_geofences_active ON geofences(is_active);

-- Geofence Alerts Table
CREATE TABLE IF NOT EXISTS geofence_alerts (
    id SERIAL PRIMARY KEY,
    geofence_id INTEGER NOT NULL REFERENCES geofences(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    alert_type VARCHAR(20) NOT NULL, -- entered, exited
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_geofence_alerts_geofence ON geofence_alerts(geofence_id);
CREATE INDEX IF NOT EXISTS idx_geofence_alerts_user ON geofence_alerts(user_id);
CREATE INDEX IF NOT EXISTS idx_geofence_alerts_triggered ON geofence_alerts(triggered_at DESC);

-- Families Table
CREATE TABLE IF NOT EXISTS families (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    head_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_families_head ON families(head_user_id);
CREATE INDEX IF NOT EXISTS idx_families_active ON families(is_active);

-- Family Members Table
CREATE TABLE IF NOT EXISTS family_members (
    id SERIAL PRIMARY KEY,
    family_id INTEGER NOT NULL REFERENCES families(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(50) DEFAULT 'member', -- head, parent, child, member
    can_view_location BOOLEAN DEFAULT TRUE,
    can_view_alerts BOOLEAN DEFAULT TRUE,
    can_manage_members BOOLEAN DEFAULT FALSE,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(family_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_family_members_family ON family_members(family_id);
CREATE INDEX IF NOT EXISTS idx_family_members_user ON family_members(user_id);

-- Family Alerts Table
CREATE TABLE IF NOT EXISTS family_alerts (
    id SERIAL PRIMARY KEY,
    family_id INTEGER NOT NULL REFERENCES families(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    alert_type VARCHAR(50) NOT NULL, -- scam_detected, unsafe_location, suspicious_activity, etc.
    severity VARCHAR(20) NOT NULL, -- low, medium, high, critical
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    metadata JSONB,
    was_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_family_alerts_family ON family_alerts(family_id);
CREATE INDEX IF NOT EXISTS idx_family_alerts_user ON family_alerts(user_id);
CREATE INDEX IF NOT EXISTS idx_family_alerts_severity ON family_alerts(severity);
CREATE INDEX IF NOT EXISTS idx_family_alerts_created ON family_alerts(created_at DESC);

-- Family Location Sharing Table
CREATE TABLE IF NOT EXISTS family_location_sharing (
    id SERIAL PRIMARY KEY,
    family_id INTEGER NOT NULL REFERENCES families(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    is_enabled BOOLEAN DEFAULT TRUE,
    share_real_time BOOLEAN DEFAULT TRUE,
    share_history BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(family_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_family_location_sharing_family ON family_location_sharing(family_id);
CREATE INDEX IF NOT EXISTS idx_family_location_sharing_user ON family_location_sharing(user_id);

-- Function to calculate distance between two GPS coordinates (Haversine formula)
CREATE OR REPLACE FUNCTION calculate_distance(
    lat1 DECIMAL,
    lon1 DECIMAL,
    lat2 DECIMAL,
    lon2 DECIMAL
) RETURNS DECIMAL AS $$
DECLARE
    earth_radius DECIMAL := 6371000; -- Earth radius in meters
    dlat DECIMAL;
    dlon DECIMAL;
    a DECIMAL;
    c DECIMAL;
BEGIN
    dlat := radians(lat2 - lat1);
    dlon := radians(lon2 - lon1);
    
    a := sin(dlat / 2) * sin(dlat / 2) +
         cos(radians(lat1)) * cos(radians(lat2)) *
         sin(dlon / 2) * sin(dlon / 2);
    
    c := 2 * atan2(sqrt(a), sqrt(1 - a));
    
    RETURN earth_radius * c;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Function to check if location is within geofence
CREATE OR REPLACE FUNCTION check_geofence_breach(
    p_user_id INTEGER,
    p_latitude DECIMAL,
    p_longitude DECIMAL
) RETURNS TABLE(
    geofence_id INTEGER,
    geofence_name VARCHAR,
    alert_type VARCHAR,
    distance_meters DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        g.id,
        g.name,
        CASE 
            WHEN calculate_distance(g.latitude, g.longitude, p_latitude, p_longitude) <= g.radius_meters 
            THEN 'entered'
            ELSE 'exited'
        END as alert_type,
        calculate_distance(g.latitude, g.longitude, p_latitude, p_longitude) as distance_meters
    FROM geofences g
    WHERE g.user_id = p_user_id
    AND g.is_active = TRUE
    AND (
        (g.alert_on_enter = TRUE AND calculate_distance(g.latitude, g.longitude, p_latitude, p_longitude) <= g.radius_meters)
        OR
        (g.alert_on_exit = TRUE AND calculate_distance(g.latitude, g.longitude, p_latitude, p_longitude) > g.radius_meters)
    );
END;
$$ LANGUAGE plpgsql;

COMMENT ON TABLE gps_locations IS 'User GPS location history';
COMMENT ON TABLE geofences IS 'User-defined geofence zones';
COMMENT ON TABLE geofence_alerts IS 'Geofence breach alerts';
COMMENT ON TABLE families IS 'Family groups for protection features';
COMMENT ON TABLE family_members IS 'Members of family groups';
COMMENT ON TABLE family_alerts IS 'Family-wide threat alerts';
COMMENT ON TABLE family_location_sharing IS 'Location sharing preferences within families';
COMMENT ON FUNCTION calculate_distance IS 'Calculate distance between two GPS coordinates in meters';
COMMENT ON FUNCTION check_geofence_breach IS 'Check if location breaches any active geofences';
