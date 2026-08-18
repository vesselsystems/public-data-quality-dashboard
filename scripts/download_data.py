"""Download the pinned public source snapshot used by the dashboard."""

from datetime import datetime, timezone
from pathlib import Path

from data_quality_dashboard.data import DATA_URL, download_dataset, write_provenance

if __name__ == "__main__":
    destination = Path(__file__).parents[1] / "data" / "raw" / "seattle_weather.csv"
    download_dataset(destination)
    provenance = write_provenance(
        destination,
        source_url=DATA_URL,
        retrieved_at=datetime.now(timezone.utc),
    )
    print(f"Downloaded source data to {destination}")
    print(f"Wrote provenance metadata to {provenance}")
