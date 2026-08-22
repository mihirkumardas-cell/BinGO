# BinGO 🗑️🤖

**AI-powered waste reporting and municipal dispatch platform.**  
Citizens photograph waste issues; the AI classifies, deduplicates, clusters, scores urgency, and recommends which sanitation team to dispatch — automatically.

> 📖 **Comprehensive Engineering & Compliance Spec:** See [ARCHITECTURE_COMPLIANCE.md](ARCHITECTURE_COMPLIANCE.md) for full tech choices, operational assumptions, SWM 2016 / DPDP / GDPR compliance checks, and IPCC AR6 carbon methodology.

---

## 🏗️ Architecture

```
Citizen App / Municipal Dashboard
        │ REST (JSON) │ WebSocket
        ▼
    Nginx (port 80)          ← Rate limiting, WebSocket upgrade
        │
    FastAPI Gateway :8000    ← Auth, routing, RBAC
        │
   ┌────┴──────────────────────────────────────┐
   │  Domain Services (FastAPI Routers)         │
   │  Auth • Reports • Hotspots • Dispatch      │
   │  Analytics • WebSocket                     │
   └────────────────────────┬──────────────────┘
                            │ arq job queue
                            ▼
                   Redis :6379 (arq + pub/sub)
                            │
                   ┌────────┴──────────┐
                   │  arq Workers       │
                   │  • photo_processor │  ← AI pipeline
                   │  • hotspot_cron   │  ← every 30 min
                   └────────┬──────────┘
                            │ HTTP :8001
                            ▼
                   AI Microservice :8001
                   ┌──────────────────────┐
                   │  YOLOv8n Classifier  │
                   │  Volume Estimator    │
                   │  Urgency Scorer      │
                   │  Dispatch Recommender│
                   └──────────────────────┘
                            │
        ┌───────────────────┼──────────────────┐
        ▼                   ▼                  ▼
   PostgreSQL+PostGIS    MinIO (S3)       Redis cache
   port 5432            port 9000/9001    sessions, WS
```

---

## 📦 Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **API Framework** | FastAPI 0.115 | REST + WebSocket |
| **ORM** | SQLAlchemy 2.0 async | Database access |
| **Database** | PostgreSQL 16 + PostGIS 3.4 | Geospatial queries |
| **Geospatial** | GeoAlchemy2, Shapely | PostGIS Python bridge |
| **Migrations** | Alembic | Schema versioning |
| **Object Storage** | MinIO (S3-compatible) | Photos, thumbnails |
| **Queue** | Redis + arq | Async job processing |
| **AI/CV** | YOLOv8n (Ultralytics) | Waste detection |
| **Clustering** | scikit-learn DBSCAN | Hotspot computation |
| **Auth** | JWT (python-jose) + bcrypt | RBAC, token refresh |
| **Push Notifs** | Firebase Admin SDK (FCM) | Mobile push |
| **SMS** | Twilio | Low-smartphone fallback |
| **Maps** | Google Maps API | Geocoding, routing |
| **Containerisation** | Docker + Compose | Full stack |
| **CI/CD** | GitHub Actions + GHCR | Build, test, push |
| **Reverse Proxy** | Nginx 1.27 | Rate limiting, TLS |

---

## 🧠 AI Dataset

The computer vision pipeline is trained/fine-tuned on two open datasets:

### Primary — Kaggle Garbage Classification
- **URL**: https://www.kaggle.com/datasets/asdasdasasdas/garbage-classification
- **Author**: Mostafa Mohamed (Kaggle)
- **Size**: ~2,527 images, 6 classes
- **Classes**: `cardboard`, `glass`, `metal`, `paper`, `plastic`, `trash`
- **License**: Open (CC)
- **Usage**: Classification head training (ResNet/YOLO backbone)

### Secondary — TACO (Trash Annotations in Context)
- **URL**: http://tacoDataset.org/
- **Paper**: Proença & Alexandre, 2020 — *TACO: Trash Annotations in Context for Litter Detection*
- **Size**: 1,500+ images, 60 categories, COCO JSON format
- **Classes**: Fine-grained taxonomy (bottle, can, bag, wrapper, etc.)
- **License**: Creative Commons Attribution 4.0
- **Usage**: Bounding box detection training (YOLO spatial head)

### Model
- **Base**: YOLOv8n (YOLOv8 Nano — smallest variant for CPU inference)
- **Fine-tuning**: TACO bounding boxes + Kaggle GC classification labels
- **Weights**: Downloaded at Docker build time → `weights/cleantrack_yolov8n.pt`
- **Fallback**: YOLOv8n COCO pretrained (if custom weights not present)

### AI Pipeline (per photo submission)
```
Photo Upload (S3)
    │
    ▼
YOLOv8n Detection    →  waste_type, confidence, bounding_box
    │
    ▼
Volume Estimator     →  bbox_area × depth_coefficient → volume_m³
    │
    ▼
PostGIS Dedup        →  ST_DWithin(50m) + same_type + 72h → is_duplicate
    │
    ▼
Urgency Scorer       →  type_weight + log(volume) + √recurrence + time_penalty → 0–100
    │
    ▼
Dispatch Recommender →  rule_table(type, volume) → vehicle_type, team_size
    │
    ▼
DBSCAN Hotspot Check →  ≥3 reports / 200m / 7 days → create/update hotspot
    │
    ▼
Push Notification    →  FCM (citizen) + WS broadcast (admin dashboard)
```

---

## 🚀 Quick Start

### Prerequisites
- Docker + Docker Compose
- (Optional) Google Maps API key, Firebase credentials, Twilio account

### 1. Clone & configure
```bash
git clone https://github.com/your-org/cleantrack-ai.git
cd cleantrack-ai
cp .env.example .env
# Edit .env — fill in SECRET_KEY at minimum
```

### 2. Start the stack
```bash
docker compose up --build
```

Services will start in this order:  
`db` → `redis` → `minio` → `minio_setup` → `api` + `ai_service` + `worker` → `nginx`

### 3. Run migrations
```bash
# Auto-run on API container start. Or manually:
docker compose exec api alembic upgrade head
```

### 4. Access
| Service | URL |
|---------|-----|
| API docs (Swagger) | http://localhost:8000/docs |
| API (via Nginx) | http://localhost/api/v1/ |
| AI Service docs | http://localhost:8001/docs |
| MinIO Console | http://localhost:9001 |
| Health check | http://localhost/health |

---

## 📡 API Reference (Summary)

### Auth
```
POST /api/v1/auth/register     — Register (citizen/field_agent/admin)
POST /api/v1/auth/login        — Login → access + refresh tokens
POST /api/v1/auth/refresh      — Rotate refresh token
POST /api/v1/auth/logout       — Revoke refresh token
GET  /api/v1/auth/me           — Current user profile
PATCH /api/v1/auth/me          — Update profile / FCM token
```

### Reports
```
POST  /api/v1/reports                  — Submit report (multipart: lat, lng, photo)
GET   /api/v1/reports                  — List (filter: status, type, bbox, urgency)
GET   /api/v1/reports/{id}             — Detail
POST  /api/v1/reports/{id}/verify      — Admin verify/override AI [municipal_admin]
POST  /api/v1/reports/{id}/close       — Close with after-photo [field_agent]
GET   /api/v1/reports/{id}/nearby      — Nearby reports within radius
```

### Hotspots
```
GET /api/v1/hotspots           — List (bbox filter for map viewport)
GET /api/v1/hotspots/{id}      — Detail
```

### Dispatch
```
POST  /api/v1/dispatch/assign          — Assign team [municipal_admin]
PATCH /api/v1/dispatch/{id}/status     — Update status + photos [field_agent]
GET   /api/v1/dispatch/{id}            — Detail
GET   /api/v1/dispatch                 — List dispatches
```

### Analytics
```
GET /api/v1/analytics/summary  — KPIs, waste breakdown, dispatch stats [admin]
GET /api/v1/analytics/heatmap  — Lat/lng/weight points for map [admin]
```

### WebSocket
```
WS /ws/dashboard?token=<jwt>           — Live admin feed (report/dispatch events)
WS /ws/report/{id}?token=<jwt>         — Citizen tracking for specific report
```

---

## 🔐 Roles & Permissions

| Endpoint | citizen | field_agent | municipal_admin | super_admin |
|----------|:-------:|:-----------:|:---------------:|:-----------:|
| Submit report | ✅ | ✅ | ✅ | ✅ |
| List own reports | ✅ | — | — | — |
| List all reports | — | ✅ | ✅ | ✅ |
| Verify/reject AI | — | — | ✅ | ✅ |
| Assign dispatch | — | — | ✅ | ✅ |
| Update dispatch status | — | ✅ | ✅ | ✅ |
| Analytics | — | — | ✅ | ✅ |
| User management | — | — | — | ✅ |

---

## 🧪 Running Tests

```bash
# Install test dependencies
pip install -r requirements.txt aiosqlite

# Run all tests
pytest tests/ -v --cov=app --cov=ai_service

# AI unit tests only (no DB required)
pytest tests/test_ai_service.py -v

# Auth integration tests
pytest tests/test_auth.py -v
```

---

## 🗂️ Project Structure

```
cleantrack-ai/
├── app/                    # Main FastAPI application
│   ├── api/v1/             # Versioned REST + WS routers
│   ├── core/               # Config, DB, auth, storage, Redis
│   ├── models/             # SQLAlchemy ORM (PostGIS-aware)
│   ├── schemas/            # Pydantic request/response schemas
│   ├── services/           # Business logic
│   ├── workers/            # arq async jobs + cron
│   └── main.py             # FastAPI app entry point
├── ai_service/             # Internal CV microservice (:8001)
│   ├── classifier.py       # YOLOv8 wrapper + class mapping
│   ├── volume_estimator.py # Bbox → m³ heuristic
│   ├── urgency_scorer.py   # Multi-factor urgency formula
│   ├── dispatch_recommender.py  # Vehicle/team rule table
│   └── main.py             # FastAPI AI service entry point
├── alembic/                # DB migrations
├── docker/                 # Dockerfiles + nginx.conf + init-db.sql
├── tests/                  # pytest test suite
├── .github/workflows/      # CI/CD pipeline
├── docker-compose.yml      # Full stack orchestration
├── .env.example            # Environment variable template
├── requirements.txt        # Main app dependencies
└── README.md
```

---

## 🌍 Deployment

### Local development
```bash
docker compose up --build
```

### Production (VPS / Cloud VM)
1. Copy repo to server
2. Fill `.env` with production values
3. Add `firebase-credentials.json`
4. Set `DEBUG=false` in `.env`
5. Configure TLS (Let's Encrypt) in `docker/nginx.conf`
6. `docker compose up -d`

### Cloud platforms
- **Railway**: Works out of box — attach PostgreSQL + Redis addons
- **Render**: Use `render.yaml` (create separately)
- **Fly.io**: Use `fly.toml` (create separately)
- **GCP Cloud Run**: Build images via CI → deploy each service

---

## 📄 License
MIT — see LICENSE file.

## 🤝 Contributing
PRs welcome. Run `ruff check` and `pytest` before submitting.
