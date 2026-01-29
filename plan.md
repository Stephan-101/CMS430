11# Wikipedia Chain Finder - Complete Project Specification (Parts 1 & 2)

## Overview
Create a web application that finds the shortest chain of Wikipedia articles connecting two given articles using bidirectional iterative deepening search. Part 2 adds persistent caching of page links to significantly improve performance.

---

# PART 1: Core Application

## Architecture

### Frontend
- **Technology**: HTML, CSS, vanilla JavaScript
- **Components**:
  - Two input boxes for start and end article titles
  - Submit/Search button (disabled during search with loading indicator)
  - Results display area showing:
    - The path as clickable links to Wikipedia articles
    - Search statistics (articles explored, time taken)
    - Error messages when applicable

### Backend
- **Technology**: Python Flask
- **API Endpoint**:
```
  POST /api/search
  
  Request:
  {
    "start": "Article Title",
    "end": "Article Title"
  }
  
  Response (Success):
  {
    "success": true,
    "path": ["Article1", "Article2", "Article3", ...],
    "stats": {
      "articles_explored": 150,
      "search_time": 2.5,
      "cache_hits": 45,        // Part 2 only
      "cache_misses": 12,      // Part 2 only
      "api_calls": 12          // Part 2 only
    },
    "message": "Path found successfully"
  }
  
  Response (Failure):
  {
    "success": false,
    "path": null,
    "stats": {
      "articles_explored": 500,
      "search_time": 5.2,
      "cache_hits": 0,         // Part 2 only
      "cache_misses": 500,     // Part 2 only
      "api_calls": 500         // Part 2 only
    },
    "message": "No path found within depth limit"
  }
```

## Search Algorithm

### Bidirectional Iterative Deepening Search
- Run two simultaneous iterative deepening searches:
  - **Forward search**: Starting from source article, following outgoing links
  - **Backward search**: Starting from target article, following incoming links (backlinks)
- **Alternating strategy**: Complete one depth level forward, then one depth level backward, repeat
- **Meeting condition**: Check for common articles between frontiers after each depth level completes
- **Path reconstruction**: Store parent pointers during search to rebuild the complete path when searches meet

### Search Parameters
- **Maximum depth**: 4 per direction
- **Maximum chain length**: 7 articles (corresponds to depth 3 per direction meeting in middle)
- **Backlinks limit**: 500 per article maximum
- **Namespace filter**: Only namespace 0 (main Wikipedia articles)

### Algorithm Details
1. Initialize two frontiers (forward and backward), each starting with their respective article at depth 0
2. Initialize two visited sets to track explored articles in each direction
3. For depth = 0 to 4:
   - Expand forward frontier by one depth level:
     - For each article at current depth, fetch its outgoing links (via cache in Part 2, or API in Part 1)
     - Filter to namespace 0 only
     - Add unvisited links to next depth level
     - Mark articles as visited
   - Check if any forward articles exist in backward visited set (meeting point found)
   - Expand backward frontier by one depth level:
     - For each article at current depth, fetch its backlinks via Wikipedia API
     - Limit to first 500 backlinks per article
     - Filter to namespace 0 only
     - Add unvisited backlinks to next depth level
     - Mark articles as visited
   - Check if any backward articles exist in forward visited set (meeting point found)
4. If meeting point found, reconstruct path using parent pointers
5. If depth limit reached without finding path, return failure

### Path Reconstruction
When searches meet at a common article:
1. Trace backward from meeting point to source using forward parent pointers
2. Trace backward from meeting point to target using backward parent pointers
3. Combine paths: [source → ... → meeting point → ... → target]
4. Return complete path

## Wikipedia API Integration

### API Endpoints to Use
- **Get article links** (forward search):
```
  https://en.wikipedia.org/w/api.php?action=query&titles={title}&prop=links&pllimit=500&format=json
```
- **Get backlinks** (backward search):
```
  https://en.wikipedia.org/w/api.php?action=query&titles={title}&prop=linkshere&lhlimit=500&format=json
```
- **Normalize/validate titles and handle redirects**:
```
  https://en.wikipedia.org/w/api.php?action=query&titles={title}&redirects=1&format=json
```

### API Handling
- Normalize article titles at the start using the API to validate and resolve redirects
- Filter all results to namespace 0 (ns=0 in API responses)
- Implement respectful rate limiting (small delay between requests if needed)
- Handle API errors gracefully with appropriate error messages
- Track total number of API calls/articles explored for statistics

## Implementation Requirements

### Deduplication and Cycle Prevention
- Maintain separate visited sets for forward and backward searches
- Never revisit an article in the same direction
- This prevents cycles and redundant API calls

### Meeting Point Detection
- Check after completing each depth level in both directions
- If multiple meeting points exist at the same depth, return the first valid path found
- Meeting point becomes part of the final path

### Error Handling
Provide clear error messages for:
- "Article '[title]' not found" - when input article doesn't exist
- "No path found within depth limit" - when searches reach max depth without meeting
- "Wikipedia API error: [details]" - when API calls fail
- Display errors in the frontend results area

### No Caching (Part 1 Only)
- Part 1: Do not implement caching of article links or search results
- Each search queries the Wikipedia API fresh
- This keeps the first version simple
- **Part 2 adds caching** - see below

### Single-Threaded
- Use a single thread to manage the search
- No parallel processing required

## Frontend Requirements

### User Interface
- Clean, simple design
- Two labeled input fields for article titles
- Search button that:
  - Disables during search
  - Shows loading indicator (spinner or text)
- Results area that displays:
  - Success: Clickable article chain (links to Wikipedia)
  - Statistics: "Explored X articles in Y seconds"
  - Part 2: Cache statistics (optional but recommended)
  - Errors: Clear error message
- Responsive layout that works on desktop and mobile

### User Experience
- Validate that both input fields are non-empty before allowing search
- Clear previous results when starting new search
- Make article names in results clickable links to their Wikipedia pages
- Format links as: `https://en.wikipedia.org/wiki/{Article_Title}`

---

# PART 2: Link Caching Enhancement

## Overview
Add a persistent SQLite database to cache page links, significantly improving performance for repeated searches by reducing Wikipedia API calls.

## Caching Strategy

### What to Cache
- **Forward links**: All outgoing links from a page (used in forward search)
- **Backlinks**: NOT cached - always fetched from API
- **Rationale**: Forward links are complete when fetched; cached backlinks would be incomplete without crawling most of Wikipedia

### Cache Benefits
- First search for any article pair: Same speed as Part 1
- Subsequent searches: 50-90% faster depending on page overlap
- Popular articles (e.g., "United States", "World War II"): Fetched once, reused indefinitely

## Database Design

### Database File
- **Filename**: `links_cache.db`
- **Location**: Project root directory
- **Type**: SQLite 3
- **Initialization**: Auto-create on first run if doesn't exist

### Table 1: `pages`
Stores metadata about cached Wikipedia pages.
```sql
CREATE TABLE pages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT UNIQUE NOT NULL,
    last_fetched TIMESTAMP NOT NULL
);

CREATE INDEX idx_pages_title ON pages(title);
```

**Columns**:
- `id`: Primary key, auto-incremented integer
- `title`: Wikipedia article title (exact match, case-sensitive), must be unique
- `last_fetched`: Timestamp when links were last fetched from API (ISO 8601 format)

**Purpose**: Tracks which pages have been cached and when, enabling staleness checks.

### Table 2: `links`
Stores forward links from cached pages.
```sql
CREATE TABLE links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_page_id INTEGER NOT NULL,
    target_page_title TEXT NOT NULL,
    FOREIGN KEY (source_page_id) REFERENCES pages(id) ON DELETE CASCADE
);

CREATE INDEX idx_links_source ON links(source_page_id);
```

**Columns**:
- `id`: Primary key, auto-incremented integer
- `source_page_id`: Foreign key to `pages.id`, identifies which page contains these links
- `target_page_title`: Title of the page being linked to (stored as text, not foreign key)

**Purpose**: Stores all outgoing links from each cached page. Each link creates one row.

**Example**: If "Python (programming language)" links to 437 other articles, there will be:
- 1 row in `pages` table for "Python (programming language)"
- 437 rows in `links` table, all with the same `source_page_id`

### Database Indexes
- **`idx_pages_title`**: Fast lookup to check if page is cached
- **`idx_links_source`**: Fast retrieval of all links from a given page

### Relationship Diagram
```
pages                          links
┌──────────────────┐          ┌────────────────────────┐
│ id (PK)          │◄─────────│ source_page_id (FK)    │
│ title (UNIQUE)   │          │ target_page_title      │
│ last_fetched     │          └────────────────────────┘
└──────────────────┘
      1                              many
```

## Staleness Policy

### Cache Expiration
- **Threshold**: 90 days
- **Check**: When querying a cached page, compare `last_fetched` to current timestamp
- **Action on stale entry**:
  1. Fetch fresh links from Wikipedia API
  2. Begin transaction
  3. Delete old links: `DELETE FROM links WHERE source_page_id = ?`
  4. Insert new links
  5. Update timestamp: `UPDATE pages SET last_fetched = CURRENT_TIMESTAMP WHERE id = ?`
  6. Commit transaction

### Rationale
- Wikipedia's link structure is relatively stable
- 90 days balances freshness with cache efficiency
- Automatic updates keep cache current without manual intervention

## Modified Search Algorithm

### Forward Search with Caching

For each article that needs link expansion:
```
1. Check cache:
   query = "SELECT id, last_fetched FROM pages WHERE title = ?"
   
2. If found in cache:
   a. Check staleness:
      is_stale = (current_time - last_fetched) > 90 days
   
   b. If NOT stale:
      - Query: "SELECT target_page_title FROM links WHERE source_page_id = ?"
      - Use cached links for frontier expansion
      - Increment cache_hits counter
      - Skip API call (PERFORMANCE WIN!)
   
   c. If stale:
      - Fetch fresh links from Wikipedia API
      - Increment api_calls counter
      - Begin transaction:
        * DELETE FROM links WHERE source_page_id = ?
        * INSERT INTO links (source_page_id, target_page_title) VALUES (?, ?) [for each link]
        * UPDATE pages SET last_fetched = CURRENT_TIMESTAMP WHERE id = ?
      - Commit transaction
      - Use fresh links for frontier expansion

3. If NOT found in cache:
   - Fetch links from Wikipedia API
   - Increment cache_misses and api_calls counters
   - Begin transaction:
     * INSERT INTO pages (title, last_fetched) VALUES (?, CURRENT_TIMESTAMP)
     * Get page_id from last insert
     * INSERT INTO links (source_page_id, target_page_title) VALUES (?, ?) [for each link]
   - Commit transaction
   - Use fresh links for frontier expansion
```

### Backward Search (Unchanged - No Caching)

- Always fetch backlinks from Wikipedia API
- Do not cache backlinks
- Increment api_calls counter
- Use API results directly for frontier expansion

## Implementation Details

### Database Initialization

Call this function when Flask app starts:
```python
def init_database():
    """Create database and tables if they don't exist."""
    conn = sqlite3.connect('links_cache.db')
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
```

### Database Connection Management
- Create database connection when Flask app starts
- Store connection in app context or create connection pool
- Reuse connection across requests
- Properly close connection on app shutdown
- Use `sqlite3.Row` factory for dict-like access to rows (optional but helpful)

### Transaction Safety

When caching new page or updating stale page:
```python
try:
    cursor.execute("BEGIN TRANSACTION")
    
    # For new page:
    cursor.execute("INSERT INTO pages (title, last_fetched) VALUES (?, ?)", ...)
    page_id = cursor.lastrowid
    cursor.executemany("INSERT INTO links (source_page_id, target_page_title) VALUES (?, ?)", ...)
    
    # For stale page:
    cursor.execute("DELETE FROM links WHERE source_page_id = ?", ...)
    cursor.executemany("INSERT INTO links (source_page_id, target_page_title) VALUES (?, ?)", ...)
    cursor.execute("UPDATE pages SET last_fetched = ? WHERE id = ?", ...)
    
    cursor.execute("COMMIT")
    
except Exception as e:
    cursor.execute("ROLLBACK")
    # Log error
    # Fall back to using API results without caching
    # Continue search normally
```

### Error Handling

If database operations fail:
- Log the error with details
- Fall back to API-only mode (treat as cache miss)
- Don't block or fail the search
- Return results as if cache didn't exist
- Ensure partial data isn't left in database (transaction rollback handles this)

### Statistics Tracking

Track these metrics during search:
- `cache_hits`: Number of pages found in cache (not stale)
- `cache_misses`: Number of pages not in cache
- `api_calls`: Total Wikipedia API calls made (includes fetching new pages + backlinks + stale refreshes)

Include in API response:
```json
{
  "stats": {
    "articles_explored": 150,
    "search_time": 2.5,
    "cache_hits": 45,
    "cache_misses": 12,
    "api_calls": 157
  }
}
```

Note: `api_calls` may be higher than `cache_misses` because backlinks always use API.

## User-Facing Changes

### Frontend Updates (Optional but Recommended)

Display cache statistics in results area:
```
Results found in 1.2 seconds
Explored 87 articles
Cache efficiency: 45 hits, 12 misses (79% cached)
API calls: 157
```

Or more compact:
```
87 articles explored in 1.2s (79% cached, 157 API calls)
```

### No Breaking Changes
- All existing functionality remains identical
- Search results are the same quality and correctness
- API endpoint unchanged
- Users don't need to modify their usage

## Performance Expectations

### Part 1 (No Caching)
- Average search: 3-8 seconds
- API calls: 50-200 per search
- Network and Wikipedia API speed dependent

### Part 2 (With Caching)
- **First search**: 3-8 seconds (same as Part 1)
- **Repeated searches with overlap**: 0.5-2 seconds (50-90% faster)
- **Searches from popular articles**: Near-instant after first cache
- **API calls**: 0-50 per search (depending on cache coverage)
- **Cache grows over time**: More searches = better performance

### Example Scenarios

**Scenario 1: First-time search**
- Search: "Python" → "Java"
- Cache: Empty
- Result: 5 seconds, 0 cache hits, 89 cache misses, 134 API calls

**Scenario 2: Immediate repeat**
- Search: "Python" → "Java" (same search again)
- Cache: Contains most pages from first search
- Result: 0.8 seconds, 89 cache hits, 0 cache misses, 45 API calls (backlinks only)

**Scenario 3: Related search**
- Search: "Python" → "Ruby" (different target, same start)
- Cache: Contains "Python" and many overlapping pages
- Result: 2 seconds, 67 cache hits, 22 cache misses, 67 API calls

## Testing Verification

### Test 1: Verify Caching Works
1. Search: "Python (programming language)" → "Computer science"
2. Note stats (e.g., 0 hits, 45 misses, 90 API calls)
3. Immediately search same path again
4. Verify stats show cache hits, fewer API calls
5. Verify path is identical

### Test 2: Verify Staleness Policy
1. Manually update database: `UPDATE pages SET last_fetched = datetime('now', '-100 days') WHERE title = 'Python (programming language)'`
2. Search using "Python (programming language)"
3. Verify it re-fetches from API (check logs or API call count)
4. Query database: Verify `last_fetched` is now current timestamp

### Test 3: Verify Transaction Safety
1. Introduce artificial error during link insertion (e.g., invalid foreign key)
2. Attempt search that would trigger this error
3. Verify search completes using API fallback
4. Verify database has no partial data (check pages and links tables)

### Test 4: Verify Database Growth
1. Perform 5 different searches
2. Query: `SELECT COUNT(*) FROM pages` - should show increasing count
3. Query: `SELECT COUNT(*) FROM links` - should show hundreds/thousands of links
4. Verify database file size grows appropriately

## File Structure
```
wikipedia-chain-finder/
├── app.py                 # Flask backend (modified for Part 2)
├── links_cache.db        # SQLite database (auto-created, grows over time)
├── templates/
│   └── index.html        # Frontend HTML (optional stats display added)
├── static/
│   ├── style.css         # Styles
│   └── script.js         # Frontend JavaScript (optional stats display added)
├── requirements.txt      # Python dependencies
├── specs.md              # This specification (Part 1)
└── specs-part2.md        # Part 2 specification (if kept separate)
```

## Dependencies

- **Flask**: Web framework
- **requests**: HTTP library for Wikipedia API calls
- **sqlite3**: Database (included with Python standard library)

`requirements.txt`:
```
Flask>=2.0.0
requests>=2.25.0
```

Note: `sqlite3` doesn't need to be in requirements.txt as it's part of Python's standard library.

## Success Criteria

### Part 1 Success Criteria
- Successfully finds paths between arbitrary Wikipedia articles
- Handles redirects automatically
- Returns shortest path within depth limit
- Provides useful feedback when no path is found
- Clean, functional user interface
- Reasonable performance (completes searches within seconds for most article pairs)

### Part 2 Success Criteria
- Database auto-created on first run with correct schema
- Forward links successfully cached with proper foreign key relationships
- Stale entries (>90 days) automatically refreshed
- Significant speedup on repeated searches (50-90% improvement)
- Cache statistics accurately tracked and displayed
- No regression in search quality or correctness
- Graceful fallback to API-only mode if database fails
- Database grows appropriately as more searches are performed
- Transaction safety ensures no corrupt data

## Future Enhancements (Beyond Part 2)

Potential improvements for future versions:
- Cache backlinks (requires addressing completeness problem)
- Database management endpoint (view cache stats, clear cache, export/import)
- Cache warming (pre-populate with popular articles)
- Multiple language Wikipedia support (separate caches)
- Compressed storage for very large caches
- Background job to refresh old cache entries
- Analytics dashboard showing most-searched paths