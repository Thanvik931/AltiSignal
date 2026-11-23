"""
Management command: seed the database with realistic synthetic data
for the Gachibowli–Kondapur corridor in Hyderabad.

Usage: python manage.py seed_data [--count 500]
"""
import random
from datetime import datetime, timezone, timedelta
from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point
from django.conf import settings

from apps.accounts.models import Contributor, ContributorRole
from apps.measurements.models import Measurement
from apps.cells.models import CellStat
from apps.cells.tasks import _aggregate_cell
from apps.cells.h3_utils import latlng_to_cell


# Gachibowli to Kondapur bounding box
LAT_MIN, LAT_MAX = 17.420, 17.470
LON_MIN, LON_MAX = 78.330, 78.380

ALTITUDE_BANDS = ["0", "30", "60", "90", "120"]
OPERATORS = ["Airtel", "Jio", "BSNL", "Vi"]
DEVICES = ["Pixel 7", "Pixel 6a", "Samsung S23", "OnePlus 11", "Redmi Note 12"]
BANDS = ["B3", "B40", "B41", "n78", "B1"]
NETWORK_TYPES = ["LTE", "LTE", "LTE", "NR"]  # LTE is more common

# Signal gets worse at higher altitudes in some cells (simulating dead patches)
def _rsrp_for_band(altitude_band: str) -> float:
    """Synthetic RSRP: ground is better, 90m has dead patches."""
    base = random.gauss(-85, 12)
    degradation = {
        "0": 0,
        "30": random.gauss(-2, 3),
        "60": random.gauss(-5, 5),
        "90": random.gauss(-12, 8),   # Noticeable degradation
        "120": random.gauss(-15, 10),
    }.get(altitude_band, 0)
    return max(-140.0, min(-40.0, base + degradation))


class Command(BaseCommand):
    help = "Seed the database with synthetic AltiSignal measurements for Hyderabad."

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=500, help="Number of measurements to create.")
        parser.add_argument("--contributors", type=int, default=5, help="Number of contributor accounts.")

    def handle(self, *args, **options):
        n_measurements = options["count"]
        n_contributors = options["contributors"]

        self.stdout.write("Creating contributors...")
        contributors = []
        for i in range(n_contributors):
            username = f"contributor_{i+1}"
            if Contributor.objects.filter(username=username).exists():
                contributors.append(Contributor.objects.get(username=username))
                continue
            c = Contributor.objects.create_user(
                username=username,
                email=f"{username}@altisignal.dev",
                password="AltiSignal2026!",
                organisation="KL University" if i == 0 else random.choice(["NCC Cadet", "GITAM", "IIIT-H"]),
                role=ContributorRole.CONTRIBUTOR,
            )
            contributors.append(c)
            self.stdout.write(f"  Created: {username}")

        # Create admin
        if not Contributor.objects.filter(username="admin").exists():
            Contributor.objects.create_superuser(
                username="admin",
                email="admin@altisignal.dev",
                password="AltiAdmin2026!",
                role=ContributorRole.ADMIN,
            )
            self.stdout.write("  Created: admin (superuser)")

        self.stdout.write(f"\nCreating {n_measurements} measurements...")
        base_time = datetime.now(timezone.utc) - timedelta(days=7)
        measurements = []

        for i in range(n_measurements):
            lat = random.uniform(LAT_MIN, LAT_MAX)
            lon = random.uniform(LON_MIN, LON_MAX)
            altitude_band = random.choice(ALTITUDE_BANDS)
            altitude_m = {
                "0": random.uniform(0, 15),
                "30": random.uniform(15, 45),
                "60": random.uniform(45, 75),
                "90": random.uniform(75, 105),
                "120": random.uniform(105, 150),
            }[altitude_band]

            rsrp = _rsrp_for_band(altitude_band)
            rsrq = random.gauss(-10, 3)
            rsrq = max(-20.0, min(0.0, rsrq))
            sinr = random.gauss(5, 8)
            sinr = max(-20.0, min(40.0, sinr))

            resolution = getattr(settings, "H3_RESOLUTION", 8)
            h3_idx = latlng_to_cell(lat, lon, resolution)

            m = Measurement(
                contributor=random.choice(contributors),
                timestamp=base_time + timedelta(seconds=i * 2),
                location=Point(lon, lat, srid=4326),
                altitude=altitude_m,
                altitude_band=altitude_band,
                h3_index=h3_idx,
                rsrp=round(rsrp, 1),
                rsrq=round(rsrq, 1),
                sinr=round(sinr, 1),
                cell_id=str(random.randint(100000, 999999)),
                pci=random.randint(0, 503),
                band=random.choice(BANDS),
                network_type=random.choice(NETWORK_TYPES),
                device_model=random.choice(DEVICES),
                operator=random.choice(OPERATORS),
            )
            measurements.append(m)

        Measurement.objects.bulk_create(measurements, batch_size=200)

        # Aggregate measurements into CellStat
        self.stdout.write("Aggregating measurements into H3 cells...")
        threshold = getattr(settings, "LINK_LOSS_RSRP_THRESHOLD", -110)
        unique_cells = {(m.h3_index, m.altitude_band) for m in measurements if m.h3_index}
        for h3_idx, band in unique_cells:
            _aggregate_cell(h3_idx, band, threshold, Measurement, CellStat)

        self.stdout.write(self.style.SUCCESS(
            f"\n✅ Seeded {n_measurements} measurements ({len(unique_cells)} H3 cell-band pairs) from {n_contributors} contributors."
        ))
        self.stdout.write("   Login: admin / AltiAdmin2026!")
        self.stdout.write("   Login: contributor_1 / AltiSignal2026!")
