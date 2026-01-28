from flask import Flask, render_template, request, jsonify
import requests
import time
from collections import deque

app = Flask(__name__)

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


def get_links(title):
    """Get outgoing links from an article (namespace 0 only)."""
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


def get_backlinks(title):
    """Get incoming links to an article (limit 500, namespace 0 only)."""
    links = []
    params = {
        "action": "query",
        "list": "backlinks",
        "bltitle": title,
        "bllimit": 500,
        "blnamespace": 0,
        "format": "json"
    }

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

    # Same article
    if start == end:
        return [start], {"articles_explored": 1, "time_taken": 0}

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
            links = get_links(article)
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
                "time_taken": round(time.time() - start_time, 2)
            }

        # Expand backward frontier
        new_backward_frontier = set()
        for article in backward_frontier:
            links = get_backlinks(article)
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
                "time_taken": round(time.time() - start_time, 2)
            }

        # Check if we can continue
        if not forward_frontier and not backward_frontier:
            break

    return None, {
        "articles_explored": articles_explored,
        "time_taken": round(time.time() - start_time, 2)
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
