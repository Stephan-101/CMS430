document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('search-form');
    const startInput = document.getElementById('start-article');
    const endInput = document.getElementById('end-article');
    const searchBtn = document.getElementById('search-btn');
    const btnText = searchBtn.querySelector('.btn-text');
    const spinner = searchBtn.querySelector('.spinner');
    const errorMessage = document.getElementById('error-message');
    const results = document.getElementById('results');
    const pathDisplay = document.getElementById('path-display');
    const stats = document.getElementById('stats');
    const articlesExplored = document.getElementById('articles-explored');
    const timeTaken = document.getElementById('time-taken');

    function setLoading(isLoading) {
        searchBtn.disabled = isLoading;
        btnText.textContent = isLoading ? 'Searching...' : 'Find Path';
        spinner.classList.toggle('hidden', !isLoading);
    }

    function showError(message) {
        errorMessage.textContent = message;
        errorMessage.classList.remove('hidden');
        results.classList.add('hidden');
    }

    function hideError() {
        errorMessage.classList.add('hidden');
    }

    function displayResults(path) {
        pathDisplay.innerHTML = '';

        path.forEach((title, index) => {
            const item = document.createElement('div');
            item.className = 'path-item';

            const number = document.createElement('span');
            number.className = 'path-number';
            number.textContent = index + 1;

            const link = document.createElement('a');
            link.className = 'path-link';
            link.href = `https://en.wikipedia.org/wiki/${encodeURIComponent(title.replace(/ /g, '_'))}`;
            link.target = '_blank';
            link.rel = 'noopener noreferrer';
            link.textContent = title;

            item.appendChild(number);
            item.appendChild(link);
            pathDisplay.appendChild(item);

            // Add arrow between items (except after last)
            if (index < path.length - 1) {
                const arrow = document.createElement('div');
                arrow.className = 'path-arrow';
                arrow.textContent = '↓';
                pathDisplay.appendChild(arrow);
            }
        });

        results.classList.remove('hidden');
    }

    function displayStats(statsData) {
        articlesExplored.textContent = statsData.articles_explored;
        timeTaken.textContent = statsData.time_taken;
        stats.classList.remove('hidden');
    }

    function clearResults() {
        results.classList.add('hidden');
        stats.classList.add('hidden');
        hideError();
    }

    form.addEventListener('submit', async function(e) {
        e.preventDefault();

        const start = startInput.value.trim();
        const end = endInput.value.trim();

        // Validate inputs
        if (!start || !end) {
            showError('Please enter both start and end article titles.');
            return;
        }

        clearResults();
        setLoading(true);

        try {
            const response = await fetch('/api/search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ start, end })
            });

            const data = await response.json();

            if (response.ok && data.path) {
                displayResults(data.path);
                if (data.stats) {
                    displayStats(data.stats);
                }
            } else {
                showError(data.error || 'An unexpected error occurred.');
                if (data.stats) {
                    displayStats(data.stats);
                }
            }
        } catch (error) {
            showError('Failed to connect to server. Please try again.');
            console.error('Search error:', error);
        } finally {
            setLoading(false);
        }
    });
});
