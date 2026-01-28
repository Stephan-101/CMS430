# Wikipedia Chain Finder - Project Specification

## Overview
Create a web application that finds the shortest chain of Wikipedia articles connecting two given articles using bidirectional iterative deepening search.

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
      "search_time": 2.5
    },
    "message": "Path found successfully"
  }
  
  Response (Failure):
  {
    "success": false,
    "path": null,
    "stats": {
      "articles_explored": 500,
      "search_time": 5.2
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
     - For each article at current depth, fetch its outgoing links via Wikipedia API
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

### No Caching (Version 1)
- Do not implement caching of article links or search results
- Each search queries the Wikipedia API fresh
- This keeps the first version simple

### Single-Threaded
- Use a single thread to manage the search
- No parallel processing required for this version

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
  - Errors: Clear error message
- Responsive layout that works on desktop and mobile

### User Experience
- Validate that both input fields are non-empty before allowing search
- Clear previous results when starting new search
- Make article names in results clickable links to their Wikipedia pages
- Format links as: `https://en.wikipedia.org/wiki/{Article_Title}`

## File Structure
```
wikipedia-chain-finder/
├── app.py                 # Flask backend
├── templates/
│   └── index.html        # Frontend HTML
├── static/
│   ├── style.css         # Styles
│   └── script.js         # Frontend JavaScript
└── requirements.txt      # Python dependencies
```

## Dependencies
- **Backend**: Flask, requests (for Wikipedia API calls)
- **Frontend**: No external dependencies (vanilla JS)

## Success Criteria
- Successfully finds paths between arbitrary Wikipedia articles
- Handles redirects automatically
- Returns shortest path within depth limit
- Provides useful feedback when no path is found
- Clean, functional user interface
- Reasonable performance (completes searches within seconds for most article pairs)