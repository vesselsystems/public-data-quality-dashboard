"""Download the public source dataset used by the dashboard."""

from pathlib import Path

from data_quality_dashboard.data import download_dataset

if __name__ == "__main__":
    destination = Path(__file__).parents[1] / "data" / "raw" / "seattle_weather.csv"
    download_dataset(destination)
    print(f"Downloaded source data to {destination}")
