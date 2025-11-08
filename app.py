from flask import Flask, request, jsonify, render_template_string
from articles import Article
from events import Event
from datetime import datetime

app = Flask(__name__)

# Sample article data
SAMPLE_ARTICLE = {
    "title": "Rock Legends Reunite for Historic Concert",
    "author": "Jane Smith",
    "source_id": "music_news_daily",
    "publication_date": datetime.now().isoformat(),
    "text": "In an unexpected turn of events, legendary rock band Pink Floyd...",
    "language": "en",
    "summary": "Historic reunion concert featuring Pink Floyd with special appearances from Paul McCartney.",
    "sentiment": 0.9,
    "artists_mentioned": ["Paul McCartney", "David Gilmour", "Roger Waters"],
    "groups_mentioned": ["Pink Floyd", "The Beatles"],
    "tags": ["rock", "reunion", "concert"],
    "countries": ["United Kingdom", "USA"],
    "in_event": True,
    "event_id": "reunion_2025",
    "groups_mentioned_ids": ["pf_001", "tb_001"],
    "artists_mentioned_ids": ["pm_001", "dg_001", "rw_001"]
}

# HTML form for testing POST requests
HTML_FORM = '''
<!DOCTYPE html>
<html>
<head>
    <title>API Test Interface</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        .form-group { margin-bottom: 15px; }
        textarea { width: 100%; height: 100px; }
        .response { margin-top: 20px; padding: 10px; background: #f0f0f0; }
        .section { margin-bottom: 40px; padding: 20px; border: 1px solid #ddd; }
        h2 { color: #333; }
    </style>
</head>
<body>
    <div class="section">
        <h2>Test Article POST Request</h2>
        <div class="form-group">
            <label>Article JSON Data:</label>
            <textarea id="jsonData">{
    "title": "Rock Legends Reunite for Historic Concert",
    "author": "Jane Smith",
    "source_id": "music_news_daily",
    "publication_date": "2025-11-06T02:36:39.000Z",
    "text": "In an unexpected turn of events, legendary rock band Pink Floyd...",
    "language": "en",
    "summary": "Historic reunion concert featuring Pink Floyd with special appearances from Paul McCartney.",
    "sentiment": 0.9,
    "artists_mentioned": ["Paul McCartney", "David Gilmour", "Roger Waters"],
    "groups_mentioned": ["Pink Floyd", "The Beatles"],
    "tags": ["rock", "reunion", "concert"],
    "countries": ["United Kingdom", "USA"],
    "in_event": true,
    "event_id": "reunion_2025",
    "groups_mentioned_ids": ["pf_001", "tb_001"],
    "artists_mentioned_ids": ["pm_001", "dg_001", "rw_001"]
}</textarea>
    </div>
    <button onclick="sendArticleRequest()">Send Article POST Request</button>
    <div id="articleResponse" class="response"></div>
    </div>

    <div class="section">
        <h2>Test Event Merge POST Request</h2>
        <div class="form-group">
            <label>Event JSON Data:</label>
            <textarea id="eventJsonData">{
    "title": "Coachella 2025",
    "description": "Annual music and arts festival featuring various artists",
    "event_date": "2025-04-11T00:00:00Z",
    "article_ids": ["article1", "article2"],
    "artist_ids": ["artist1", "artist2"],
    "group_ids": ["group1", "group2"],
    "tags": ["music", "festival", "concert"],
    "countries": ["USA"],
    "avg_sentiment": 0.85
}</textarea>
        </div>
        <button onclick="sendEventRequest()">Send Event Merge Request</button>
        <div id="eventResponse" class="response"></div>
    </div>

    <script>
        function sendArticleRequest() {
            fetch('/api/data', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: document.getElementById('jsonData').value
            })
            .then(response => response.json())
            .then(data => {
                document.getElementById('articleResponse').innerText = JSON.stringify(data, null, 2);
            })
            .catch(error => {
                document.getElementById('articleResponse').innerText = 'Error: ' + error;
            });
        }

        function sendEventRequest() {
            fetch('/api/events/merge', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: document.getElementById('eventJsonData').value
            })
            .then(response => response.json())
            .then(data => {
                document.getElementById('eventResponse').innerText = JSON.stringify(data, null, 2);
            })
            .catch(error => {
                document.getElementById('eventResponse').innerText = 'Error: ' + error;
            });
        }
    </script>
</body>
</html>
'''

@app.route('/')
def hello():
    return render_template_string(HTML_FORM)

@app.route('/api/data', methods=['POST'])
def post_data():
    try:
        data = request.get_json()
        # Convert the publication_date string to datetime if it exists
        if 'publication_date' in data and data['publication_date']:
            data['publication_date'] = datetime.fromisoformat(data['publication_date'].replace('Z', '+00:00'))
        
        # Validate the data against our Pydantic model
        article = Article(**data)
        
        return jsonify({
            "message": "Article data received and validated successfully",
            "data": article.model_dump(mode='json')
        }), 201
    except Exception as e:
        return jsonify({
            "error": "Validation error",
            "details": str(e)
        }), 400

@app.route('/api/events/merge', methods=['POST'])
def merge_articles_to_event():
    try:
        data = request.get_json()
        
        # create events
        event_data = {
            "title": data['title'],
            "description": data['description'],
            "event_date": datetime.fromisoformat(data['event_date'].replace('Z', '+00:00')),
            "article_ids": data['article_ids'],
            "article_count": len(data['article_ids']),
            "artist_ids": data.get('artist_ids', []),
            "group_ids": data.get('group_ids', []),
            "tags": data.get('tags', []),
            "countries": data.get('countries', []),
            "avg_sentiment": data.get('avg_sentiment', 0.0)
        }
        
        # Validate the data
        event = Event(**event_data)
        
        return jsonify({
            "message": "Articles merged into event successfully",
            "event": event.model_dump(mode='json')
        }), 201
        
    except Exception as e:
        return jsonify({
            "error": "Event creation error",
            "details": str(e)
        }), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
