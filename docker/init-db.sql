-- CleanTrack AI — Database initialisation
-- This runs once when the PostgreSQL container first starts.
-- The PostGIS image already enables the extension, but we make it explicit.

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- for fuzzy text search on addresses
