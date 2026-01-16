# Y Combinator Company Scraper

![Python](https://img.shields.io/badge/Python-3.7+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Playwright](https://img.shields.io/badge/Playwright-45ba4b?style=for-the-badge&logo=Playwright&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-150458?style=for-the-badge&logo=pandas&logoColor=white)

A high-performance, asynchronous web scraper designed to extract detailed data about startups from the [Y Combinator Companies Directory](https://www.ycombinator.com/companies). Built using **Python** and **Playwright**, this tool efficiently navigates the directory, handles infinite scrolling, and concurrently scrapes deep-level company profiles.

## 🚀 Key Features

*   **Asynchronous & Concurrent**: Uses `asyncio` and `playwright` to process multiple company profiles simultaneously (default: 3 concurrent tabs), significantly speeding up data collection.
*   **Infinite Scroll Handling**: Automatically scrolls through the main directory to load and collect target URLs.
*   **Resource Optimization**: Blocks heavy assets like images, fonts, and stylesheets to reduce bandwidth and load times.
*   **Data Persistence**:
    *   **Batch Saving**: Saves progress to `yc_scraping_progress.csv` every 50 companies to prevent data loss.
    *   **Final Export**: Generates a timestamped CSV file (e.g., `yc_scraping_20260116.csv`) upon completion.
*   **Smart Parsing**:
    *   Extracts company credentials, batches (e.g., W24, S22), and descriptions.
    *   Discover founder names and LinkedIn profiles using heuristic selectors.
*   **Resilience**: Implements retry logic for network stability and random delays to mimic human behavior.

## 📋 Prerequisites

*   Python 3.7 or higher
*   pip (Python package installer)

## 🛠️ Installation

1.  **Clone the repository** (if applicable) or download the source code.

2.  **Set up a virtual environment** (Recommended):
    ```bash
    # Windows
    python -m venv .venv
    .venv\Scripts\activate

    # macOS/Linux
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install required Python packages**:
    ```bash
    pip install playwright pandas
    ```

4.  **Install Playwright browsers**:
    ```bash
    playwright install chromium
    ```

## ⚙️ Configuration

You can adjust key parameters directly in the `yc_scraper.py` file under the `CONFIGURATION` section:

```python
TARGET_COUNT = 500          # Goal: Number of unique startups to scrape
CONCURRENCY_LIMIT = 3       # Max number of concurrent browser tabs
BATCH_SIZE = 50             # Save progress to CSV after every N companies
```

## 🏃 Usage

Run the scraper using Python:

```bash
python yc_scraper.py
```

### Execution Flow
1.  **Phase 1**: The script navigates to the YC directory and scrolls to collect the target number of company URLs.
2.  **Phase 2**: It visits each collected URL to extract detailed information, displaying progress in the console.
3.  **Completion**: A final CSV file is generated in the root directory.

## 📊 Output Data

The generated CSV file contains the following columns:

| Column Name             | Description |
|-------------------------|-------------|
| **Company Name**        | The name of the startup. |
| **Batch**               | The YC batch the company participated in (e.g., W24). |
| **Short Description**   | A brief tagline or description of what the company does. |
| **Founder Name(s)**     | Detected names of the founders. |
| **Founder LinkedIn URL(s)** | Direct links to the founders' LinkedIn profiles. |

## ⚠️ Disclaimer

This tool is for **educational purposes only**. Web scraping should be done responsibly and in accordance with the target website's Terms of Service and `robots.txt` policies. The authors are not responsible for any misuse of this software.