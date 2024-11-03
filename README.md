# VeertjeBot

### A bot to adjust metadata in recent uploads of 1Veertje

This bot is designed to enrich and adjust metadata for recent uploads on Wikimedia Commons by the user **1Veertje**. It performs tasks such as adding structured data claims, categorizing videos based on YouTube metadata, updating author information, and managing categories based on specific metadata fields.

## Features

- **YouTube Metadata Integration**: Uses the YouTube Data API to fetch and add video details, such as title, description, and publication date.
- **Author Information Updates**: Adjusts author details to reflect accurate information, using structured data claims.
- **Category Management**: Automatically adds categories based on `depicts` statements and YouTube channel information.
- **Structured Data Claims**: Removes or updates specific structured data claims (such as creator or license) as needed.
- **CSV Integration for Channel Metadata**: Loads YouTube channel metadata from a CSV file for categorization.

## Requirements

- **Python 3.x**
- **Wikimedia Pywikibot**: `pip install pywikibot`
- **YouTube Data API Client**: `pip install google-api-python-client`
- **Other Libraries**:
  - `requests`
  - `csv`
  - `feedparser`

Ensure that you have a valid API key for the YouTube Data API and the necessary permissions to edit on Wikimedia Commons.

## Setup

1. **Clone the repository** or download `VeertjeBot.py` and other necessary files.
   
2. **Install dependencies**:
   ```bash
   pip install pywikibot google-api-python-client requests feedparser

   ## Usage

1. **Run the Bot**:
   - Execute the script from the command line:
     ```bash
     python VeertjeBot.py
     ```

2. **Bot Actions**:
   - The bot automatically checks recent uploads by **1Veertje** on Wikimedia Commons.
   - For each file, it fetches metadata, adjusts author information, adds categories based on YouTube data, and updates structured data claims as specified.

## Functions and Code Structure

- **Initialization**:
  - The bot loads configuration from `config.json` and initializes Pywikibot and the YouTube API client.
  
- **Primary Method** (`run`):
  - Starts the bot's operations by processing recent uploads of 1Veertje, adjusting metadata as needed.

- **Helper Functions**:
  - `load_youtube_channels`: Loads YouTube channel metadata from `youtube_channels.csv`.
  - `getYTdescription`: Fetches YouTube video details and updates the file description on Commons.
  - `changeAuthor`: Updates the author information in the structured data.
  - `categorizeVideos`: Adds categories based on the YouTube channel and publication date.
  - `createVideoCategory`: Creates a category if it doesn’t already exist.

## License

This bot is released under the MIT License.
