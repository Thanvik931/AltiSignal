# AltiSignal 🚁📶

> **Crowdsourced altitude-aware 4G/5G coverage and link-loss prediction for drone operators.**

Ground-level coverage maps are misleading for BVLOS drone operations. AltiSignal collects real signal measurements at multiple altitude bands (30/60/90/120 m) and predicts link-loss probability on any planned route — before takeoff.

---

## Milestones

| Weekend | Status | Deliverable |
|---------|--------|-------------|
| 1 | ✅ | Docker + Django + PostGIS + `POST /measurements` + seed data |
| 2 | ⏳ | Kotlin Android agent |
| 3 | ⏳ | H3 aggregation + Next.js map |
| 4 | ⏳ | Altitude slider + gap view |
| 5 | ⏳ | ML model + `/route-risk` |
| 6 | ⏳ | Tests, CI, deployment |

## Quick Start

```bash
git clone https://github.com/Thanvik931/AltiSignal.git
cd AltiSignal
docker-compose up --build
```

Then in a new terminal:
```bash
docker-compose exec backend python manage.py migrate
docker-compose exec backend python manage.py seed_data --count 500
```

| Service | URL |
|---------|-----|
| API | http://localhost:8000/api/v1/ |
| Swagger | http://localhost:8000/api/docs/ |
| Admin | http://localhost:8000/admin/ |

## Tech Stack

- **Android Agent**: Kotlin, TelephonyManager, Fused Location, Barometer
- **Backend**: Django, DRF, GeoDjango, PostGIS, Celery, Redis
- **Frontend**: Next.js, MapLibre GL JS, deck.gl (Weekend 3)
- **ML**: XGBoost, scikit-learn (Weekend 5)
- **DevOps**: Docker, docker-compose, GitHub Actions

## Advisory

> AltiSignal results are advisory only. Always comply with local aviation regulations and perform independent safety checks before any flight.

---

*Author: Sama Thanvik Reddy | v1.0 | Hyderabad focus: Gachibowli–Kondapur corridor*
