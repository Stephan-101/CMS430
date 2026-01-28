# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Wikipedia Chain Finder** - A web application that finds the shortest chain of Wikipedia articles connecting two given articles using bidirectional iterative deepening search.

The full specification is in `specs.md`.

## Project Structure

```
/workspaces/CMS430/
├── app.py                 # Flask backend with Wikipedia API integration & search algorithm
├── templates/
│   └── index.html         # Frontend HTML
├── static/
│   ├── style.css          # Responsive styles
│   └── script.js          # Frontend JavaScript
├── requirements.txt       # Python dependencies (Flask, requests)
└── specs.md               # Original project specification
```

## How to Run

```bash
pip install -r requirements.txt
flask run
```

Then open http://localhost:5000 (or use the Codespace port forwarding URL).

## Key Features

- **Bidirectional search**: Searches from both start and end articles simultaneously
- **Wikipedia API integration**: Fetches article links in real-time
- **Max depth 4**: Limits search to 4 links in each direction (8 total)
- **Responsive UI**: Works on desktop and mobile

## Architecture

- `normalize_title()` - Validates articles exist and resolves redirects
- `get_links()` - Gets outgoing links from an article (namespace 0 only)
- `get_backlinks()` - Gets incoming links to an article (limit 500)
- `bidirectional_search()` - Main search algorithm with meeting point detection
- `POST /api/search` - API endpoint that accepts `{start, end}` and returns path + stats
