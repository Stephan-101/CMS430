from flask import Flask, render_template, request, jsonify
import requests
import time
import sqlite3
from datetime import datetime, timedelta
from collections import deque

app = Flask(__name__)

# Database configuration
DATABASE_FILE = "links_cache.db"
CACHE_EXPIRY_DAYS = 90


def get_db_connection():
    """Get a database connection with row factory."""
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """Create database and tables if they don't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create pages table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT UNIQUE NOT NULL,
            last_fetched TIMESTAMP NOT NULL
        )
    ''')

    # Create index on pages.title
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_pages_title ON pages(title)
    ''')

    # Create links table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_page_id INTEGER NOT NULL,
            target_page_title TEXT NOT NULL,
            FOREIGN KEY (source_page_id) REFERENCES pages(id) ON DELETE CASCADE
        )
    ''')

    # Create index on links.source_page_id
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_links_source ON links(source_page_id)
    ''')

    conn.commit()
    conn.close()


# Initialize database on startup
init_database()

WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
MAX_DEPTH = 4  # Max depth per direction
REQUEST_TIMEOUT = 10
HEADERS = {
    "User-Agent": "WikipediaChainFinder/1.0 (Educational project; contact@example.com)"
}


def make_api_request(params):
    """Make a request to the Wikipedia API with proper headers."""
    response = requests.get(WIKIPEDIA_API, params=params, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def normalize_title(title):
    """Validate article exists and resolve redirects. Returns normalized title or None."""
    params = {
        "action": "query",
        "titles": title,
        "redirects": 1,
        "format": "json"
    }
    try:
        data = make_api_request(params)
        pages = data.get("query", {}).get("pages", {})
        for page_id, page_data in pages.items():
            if page_id == "-1":
                return None  # Page doesn't exist
            return page_data.get("title")
    except requests.RequestException:
        return None


def fetch_links_from_api(title):
    """Fetch outgoing links from Wikipedia API (namespace 0 only)."""
    links = []
    params = {
        "action": "query",
        "titles": title,
        "prop": "links",
        "pllimit": "max",
        "plnamespace": 0,
        "format": "json"
    }

    try:
        while True:
            data = make_api_request(params)
            pages = data.get("query", {}).get("pages", {})
            for page_data in pages.values():
                for link in page_data.get("links", []):
                    links.append(link["title"])

            if "continue" in data:
                params["plcontinue"] = data["continue"]["plcontinue"]
            else:
                break
    except requests.RequestException:
        pass

    return links


def get_cached_links(title):
    """
    Get links from cache if available and not stale.
    Returns (links, cache_hit) where cache_hit is True if found in cache.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if page exists in cache
        cursor.execute("SELECT id, last_fetched FROM pages WHERE title = ?", (title,))
        row = cursor.fetchone()

        if row:
            page_id = row["id"]
            last_fetched = datetime.fromisoformat(row["last_fetched"])
            is_stale = (datetime.now() - last_fetched) > timedelta(days=CACHE_EXPIRY_DAYS)

            if not is_stale:
                # Cache hit - get links from cache
                cursor.execute(
                    "SELECT target_page_title FROM links WHERE source_page_id = ?",
                    (page_id,)
                )
                links = [r["target_page_title"] for r in cursor.fetchall()]
                conn.close()
                return links, True
            else:
                # Stale entry - will need to refresh
                conn.close()
                return None, False
        else:
            conn.close()
            return None, False

    except Exception:
        return None, False


def cache_links(title, links):
    """Store links in cache. Handles both new entries and stale refreshes."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if page already exists
        cursor.execute("SELECT id FROM pages WHERE title = ?", (title,))
        row = cursor.fetchone()

        cursor.execute("BEGIN TRANSACTION")

        if row:
            # Update existing (stale) entry
            page_id = row["id"]
            cursor.execute("DELETE FROM links WHERE source_page_id = ?", (page_id,))
            cursor.execute(
                "UPDATE pages SET last_fetched = ? WHERE id = ?",
                (datetime.now().isoformat(), page_id)
            )
        else:
            # Insert new entry
            cursor.execute(
                "INSERT INTO pages (title, last_fetched) VALUES (?, ?)",
                (title, datetime.now().isoformat())
            )
            page_id = cursor.lastrowid

        # Insert all links
        link_data = [(page_id, link_title) for link_title in links]
        cursor.executemany(
            "INSERT INTO links (source_page_id, target_page_title) VALUES (?, ?)",
            link_data
        )

        conn.commit()
        conn.close()

    except Exception:
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass


def get_links(title, stats=None):
    """
    Get outgoing links from an article with caching.
    stats dict is updated with cache_hits, cache_misses, api_calls if provided.
    """
    # Try cache first
    cached_links, cache_hit = get_cached_links(title)

    if cache_hit:
        if stats is not None:
            stats["cache_hits"] = stats.get("cache_hits", 0) + 1
        return cached_links

    # Cache miss - fetch from API
    if stats is not None:
        stats["cache_misses"] = stats.get("cache_misses", 0) + 1
        stats["api_calls"] = stats.get("api_calls", 0) + 1

    links = fetch_links_from_api(title)

    # Store in cache
    if links:
        cache_links(title, links)

    return links


def get_backlinks(title, stats=None):
    """Get incoming links to an article (limit 500, namespace 0 only). Never cached."""
    links = []
    params = {
        "action": "query",
        "list": "backlinks",
        "bltitle": title,
        "bllimit": 500,
        "blnamespace": 0,
        "format": "json"
    }

    if stats is not None:
        stats["api_calls"] = stats.get("api_calls", 0) + 1

    try:
        data = make_api_request(params)
        for link in data.get("query", {}).get("backlinks", []):
            links.append(link["title"])
    except requests.RequestException:
        pass

    return links


def reconstruct_path(meeting_point, forward_parents, backward_parents):
    """Reconstruct the path from start to end through the meeting point."""
    # Build forward path (start -> meeting point)
    forward_path = []
    current = meeting_point
    while current is not None:
        forward_path.append(current)
        current = forward_parents.get(current)
    forward_path.reverse()

    # Build backward path (meeting point -> end)
    backward_path = []
    current = backward_parents.get(meeting_point)
    while current is not None:
        backward_path.append(current)
        current = backward_parents.get(current)

    return forward_path + backward_path


def bidirectional_search(start, end):
    """
    Perform bidirectional iterative deepening search.
    Returns (path, stats) where path is list of titles or None if not found.
    """
    start_time = time.time()
    articles_explored = 0

    # Initialize cache statistics
    stats = {
        "cache_hits": 0,
        "cache_misses": 0,
        "api_calls": 0
    }

    # Same article
    if start == end:
        return [start], {
            "articles_explored": 1,
            "time_taken": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "api_calls": 0
        }

    # Initialize frontiers and visited sets
    forward_frontier = {start}
    backward_frontier = {end}
    forward_visited = {start}
    backward_visited = {end}
    forward_parents = {start: None}
    backward_parents = {end: None}

    for depth in range(MAX_DEPTH):
        # Expand forward frontier
        new_forward_frontier = set()
        for article in forward_frontier:
            links = get_links(article, stats)
            articles_explored += 1

            for link in links:
                if link not in forward_visited:
                    forward_visited.add(link)
                    forward_parents[link] = article
                    new_forward_frontier.add(link)

        forward_frontier = new_forward_frontier

        # Check for meeting point after forward expansion
        meeting_points = forward_visited & backward_visited
        if meeting_points:
            meeting_point = next(iter(meeting_points))
            path = reconstruct_path(meeting_point, forward_parents, backward_parents)
            return path, {
                "articles_explored": articles_explored,
                "time_taken": round(time.time() - start_time, 2),
                "cache_hits": stats["cache_hits"],
                "cache_misses": stats["cache_misses"],
                "api_calls": stats["api_calls"]
            }

        # Expand backward frontier
        new_backward_frontier = set()
        for article in backward_frontier:
            links = get_backlinks(article, stats)
            articles_explored += 1

            for link in links:
                if link not in backward_visited:
                    backward_visited.add(link)
                    backward_parents[link] = article
                    new_backward_frontier.add(link)

        backward_frontier = new_backward_frontier

        # Check for meeting point after backward expansion
        meeting_points = forward_visited & backward_visited
        if meeting_points:
            meeting_point = next(iter(meeting_points))
            path = reconstruct_path(meeting_point, forward_parents, backward_parents)
            return path, {
                "articles_explored": articles_explored,
                "time_taken": round(time.time() - start_time, 2),
                "cache_hits": stats["cache_hits"],
                "cache_misses": stats["cache_misses"],
                "api_calls": stats["api_calls"]
            }

        # Check if we can continue
        if not forward_frontier and not backward_frontier:
            break

    return None, {
        "articles_explored": articles_explored,
        "time_taken": round(time.time() - start_time, 2),
        "cache_hits": stats["cache_hits"],
        "cache_misses": stats["cache_misses"],
        "api_calls": stats["api_calls"]
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/search", methods=["POST"])
def search():
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    start_title = data.get("start", "").strip()
    end_title = data.get("end", "").strip()

    if not start_title or not end_title:
        return jsonify({"error": "Both start and end articles are required"}), 400

    # Normalize titles
    normalized_start = normalize_title(start_title)
    if not normalized_start:
        return jsonify({"error": f"Article not found: {start_title}"}), 404

    normalized_end = normalize_title(end_title)
    if not normalized_end:
        return jsonify({"error": f"Article not found: {end_title}"}), 404

    # Perform search
    try:
        path, stats = bidirectional_search(normalized_start, normalized_end)

        if path:
            return jsonify({
                "path": path,
                "stats": stats
            })
        else:
            return jsonify({
                "error": f"No path found within {MAX_DEPTH} links in each direction",
                "stats": stats
            }), 404
    except Exception as e:
        return jsonify({"error": f"Search failed: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=True)
