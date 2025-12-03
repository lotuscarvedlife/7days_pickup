# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based arXiv paper aggregation and summarization system called "七日拾遗" (7-Day Pickup) that automatically fetches papers from the `eess.AS` (Audio and Speech Processing) category, summarizes them using AI, and presents them through a Gradio web interface.

## Core Architecture

The system consists of four main components that work in sequence:

1. **Data Fetching (`arxiv_daily_fetcher.py`)** - Fetches papers from arXiv API based on categories and dates
2. **Pipeline Orchestration (`run_pipeline.py`)** - Coordinates the end-to-end workflow
3. **AI Summarization (`summarize_by_zai.py`)** - Generates Chinese summaries using ZhipuAI's glm-4.5-flash model
4. **Web Interface (`app.py`)** - Gradio-based web UI for displaying results

### Data Flow

1. `app.py` calculates the 7-day date range (excluding weekends) based on arXiv's update schedule
2. `run_pipeline.py` calls `arxiv_daily_fetcher.py` to fetch papers for each day
3. `summarize_by_zai.py` processes the fetched papers to add AI-generated summaries
4. Results are stored as CSV files and displayed through the Gradio interface

## Common Development Commands

### Running the Application

```bash
# Main web interface (Gradio)
python app.py

# Or use the batch file for Windows
start.bat
```

### Individual Component Operations

```bash
# Fetch papers for specific date and category
python arxiv_daily_fetcher.py --categories eess.AS --date 2025-12-01

# Run full pipeline for date range
python run_pipeline.py --categories eess.AS --date 2025-12-01:2025-12-07

# Generate AI summaries for existing CSV files
python summarize_by_zai.py --categories eess.AS --date 2025-12-01
```

### Dependencies Installation

```bash
pip install -r requirements.txt
```

## Configuration Requirements

### API Key Setup
- Create `zhipu_api_key.txt` file with your ZhipuAI API key from https://www.bigmodel.cn/usercenter/proj-mgmt/apikeys
- The system will create this file automatically if it doesn't exist

### Deployment Options in `app.py`
- Local only: `app.launch()`
- Network sharing: `app.launch(server_name='0.0.0.0')`

## File Naming Conventions

Generated CSV files follow this pattern:
- Base: `arxiv_{categories}_{date}.csv` (e.g., `arxiv_eessAS_2025-12-01.csv`)
- With keywords: `arxiv_{categories}_keywords_{keywords}_{date}.csv`

## Key Business Logic

### Date Calculation (`app.py:get_arxiv_dates()`)
The system implements arXiv's actual update schedule:
- Updates occur Monday-Friday at 2:00 PM Eastern Time
- Weekends are excluded from the 7-day count
- Current ET time determines whether to include today's papers

### Category Processing
- Currently configured for `eess.AS` (Audio and Speech Processing)
- Supports multiple categories but designed for single-category operation
- Categories are joined with hyphens for filenames (dots removed)

### AI Summarization Integration
- Uses ZhipuAI's glm-4.5-flash free model
- Processes papers that don't already have summaries
- Skips previously summarized content to save API calls