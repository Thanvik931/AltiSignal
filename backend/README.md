# AltiSignal Backend

## Development Setup

### Quick Start (Docker)
```bash
# From repo root
docker-compose up --build

# Wait for services to start, then run migrations and seed data
docker-compose exec backend python manage.py migrate
docker-compose exec backend python manage.py seed_data --count 500
```

### Services
| Service | URL |
|---------|-----|
| API | http://localhost:8000/api/v1/ |
| Swagger Docs | http://localhost:8000/api/docs/ |
| ReDoc | http://localhost:8000/api/redoc/ |
| Django Admin | http://localhost:8000/admin/ |

### Default Credentials (after seed_data)
- **Admin**: `admin` / `AltiAdmin2026!`
- **Contributor**: `contributor_1` / `AltiSignal2026!`

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register/` | Register contributor |
| POST | `/api/v1/auth/token/` | Get JWT tokens |
| POST | `/api/v1/measurements/` | Upload measurement batch |
| GET | `/api/v1/measurements/list/?bbox=&altitude=` | Query measurements |
| GET | `/api/v1/cells/?bbox=&altitude=` | H3 cell stats |
| GET | `/api/v1/cells/gap/?bbox=&altitude=` | Gap detection |
| GET | `/api/v1/gap/?bbox=&altitude=` | Direct PRD path for gap detection |
| POST | `/api/v1/predictions/route-risk/` | Route risk prediction |
| POST | `/api/v1/route-risk/` | Direct PRD path for route risk |

### Running Tests
```bash
docker-compose exec backend pytest
```

### Local Development (without Docker)
```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
# Edit .env to point to local PostgreSQL+PostGIS
python manage.py migrate
python manage.py seed_data
python manage.py runserver
```
