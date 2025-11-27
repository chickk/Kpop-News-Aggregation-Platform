from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from typing import List, AsyncGenerator 
from contextlib import asynccontextmanager 
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from datetime import datetime

from app.models.articles import Article
from app.models.events import Event

from app.data_layer.schemas import Event_db, Article_db

from app.interfaces.unit_of_work import IUnitOfWork
from app.adapters.mongo_unit_of_work import MongoUnitOfWork
from app.data_layer.mongo_database import init_db

# --- Lifespan Manager ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Application startup... Initializing database connections...")
    URI = "mongodb://localhost:27017/idolTracker"
    
    # Initialize and obtain client
    db_client = await init_db(URI=URI) 
    
    # Store the client in app.state so that it can be used in requests.
    app.state.db_client = db_client 
    
    yield
    
    # --- Code executed when the application closes ---
    print("Application closed... Database connection closed...")
    if hasattr(app.state, 'db_client') and app.state.db_client:
        app.state.db_client.close()


# --- Pass Lifespan to FastAPI ---
app = FastAPI(
    title="Idol Tracker API",
    description="An API for managing articles, events, and artists.",
    lifespan=lifespan
)


# --- Unit of Work Dependency Injection ---
async def get_uow(request: Request) -> AsyncGenerator[IUnitOfWork, None]:
    """
    Get the database client from app.state and build UoW.
    """
    # Get the client from the application state.
    db_client: AsyncIOMotorClient = getattr(request.app.state, "db_client", None)
    
    if not db_client:
        raise HTTPException(status_code=500, detail="The database client has not yet been initialized.") 
        
    use_transaction = request.method not in ["GET"]
    
    # Create Unit of Work
    uow = MongoUnitOfWork(db_client, use_transaction=use_transaction)
    
    async with uow:
        yield uow

HTML_FORM = """
<!DOCTYPE html>
<html>
<head>
    <title>API Test Interface (FastAPI)</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        .form-group { margin-bottom: 15px; }
        textarea { width: 100%; height: 100px; }
        .response { margin-top: 20px; padding: 10px; background: #f0f0f0; border-radius: 5px; white-space: pre-wrap; word-wrap: break-word; }
        .section { margin-bottom: 40px; padding: 20px; border: 1px solid #ddd; border-radius: 8px; }
        h2 { color: #333; }
        button { background: #007bff; color: white; padding: 10px 15px; border: none; border-radius: 5px; cursor: pointer; }
        button:hover { background: #0056b3; }
    </style>
</head>
<body>
    <h1>API Testing Site (FastAPI Version)</h1>
    <div class="section">
        <h2>Testing POST /api/content/test-article (write DB)</h2>
        <div class="form-group">
            <label>Testing Article JSON data:</label>
            <textarea id="articleJsonData">{
    "title": "K-pop rising star group 'Aegis' first world tour preview",
    "author": "Lee",
    "source_id": "global_pop_weekly",
    "publication_date": "2025-11-18T15:30:00Z",
    "text": "New generation K-pop idol group Aegis released a teaser trailer today through their official channels for their first world tour, 'Guardian'. The tour is expected to cover Asia, North America, and Europe...",
    "images": ["https://placehold.co/800x450/333333/ffffff?text=Concert+Poster+Image+URL"],
    "video": null,
    "language": "english",
    "in_event": true,
    "event_id": "Met Gala",
    "groups_mentioned_ids": ["TWICE"],
    "artists_mentioned_ids": ["Sana", "Tzuyu"],
    "summary": "K-pop group Aegis has announced its first world tour, 'Guardian', which is expected to cover Asia, North America, and Europe, to promote its hit single 'Phoenix'.",
    "sentiment": 0.95,
    "artists_mentioned": ["Minho", "Jina"],
    "groups_mentioned": ["Aegis"],
    "tags": ["K-pop", "Concert", "World Tour", "Rising Star"],
    "countries": ["KR", "USA", "JP"]
}</textarea>
        </div>
        <button onclick="sendArticleRequest()">Create Test Article</button>
        <div id="articleResponse" class="response"></div>
    </div>
    <div class="section">
        <h2>Testing GET /api/content/latest</h2>
        <p>Retrieve up to 10 of the latest articles from the database.</p>
        <button onclick="fetchLatest()">Get the latest content</button>
        <div id="latestResponse" class="response"></div>
    </div>

    <div class="section">
        <h2>Testing Event Merge POST request</h2>
        <div class="form-group">
            <label>Event JSON data:</label>
            <textarea id="eventJsonData">{
    "title": "Coachella 2025",
    "summary": "Annual music and arts festival featuring various artists",
    "synthesized_text": "TWICE",
    "event_date": "2025-04-11T00:00:00Z",
    "article_ids": ["article1", "article2"],
    "article_count": 100,
    "artist_ids": ["artist1", "artist2"],
    "group_ids": ["group1", "group2"],
    "tags": ["music", "festival", "concert"],
    "countries": ["USA"],
    "avg_sentiment": 0.85
}</textarea>
        </div>
        <button onclick="sendEventRequest()">Send event merging request</button>
        <div id="eventResponse" class="response"></div>
    </div>

    <script>
        function sendArticleRequest() {
            document.getElementById('articleResponse').innerText = 'sending...';
            fetch('/api/content/test-article', { // <-- new route
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: document.getElementById('articleJsonData').value
            })
            .then(response => {
                if (!response.ok) throw new Error('Article creation failed, please check the log: ' + response.statusText);
                return response.json();
            })
            .then(data => {
                document.getElementById('articleResponse').innerText = 'Article created successfully:\\n' + JSON.stringify(data, null, 2);
            })
            .catch(error => {
                document.getElementById('articleResponse').innerText = 'Error: ' + error.message;
            });
        }
        function fetchLatest() {
            document.getElementById('latestResponse').innerText = 'loading...';
            fetch('/api/content/latest')
                .then(response => {
                    if (!response.ok) throw new Error('Network response error: ' + response.statusText);
                    return response.json();
                })
                .then(data => {
                    document.getElementById('latestResponse').innerText = JSON.stringify(data, null, 2);
                })
                .catch(error => {
                    document.getElementById('latestResponse').innerText = 'Error: ' + error;
                });
        }

        function sendEventRequest() {
            document.getElementById('eventResponse').innerText = 'sending...';
            fetch('/api/events/merge', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: document.getElementById('eventJsonData').value
            })
            .then(response => response.json()) // Always parse JSON
            .then(data => {
                if (data.detail) { // FastAPI errors are usually found in the 'detail' section
                     document.getElementById('eventResponse').innerText = 'Error: ' + JSON.stringify(data.detail, null, 2);
                } else {
                     document.getElementById('eventResponse').innerText = JSON.stringify(data, null, 2);
                }
            })
            .catch(error => {
                document.getElementById('eventResponse').innerText = 'Error: ' + error.message;
            });
        }
    </script>
</body>
</html>
"""

# --- API router ---

@app.get("/", response_class=HTMLResponse)
async def root():
    """ HTML testing page """
    return HTMLResponse(content=HTML_FORM)

@app.get("/api/content/latest", response_model=List[Article])
async def get_latest_content(
    uow: IUnitOfWork = Depends(get_uow) 
):
    """
    Get the latest articles from the database.
    """
    try:
        articles_db = await uow.articles.get_all(limit=10)
        return articles_db
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/content/test-article", response_model=Article, status_code=201)
async def create_test_article(
    article: Article,
    uow: IUnitOfWork = Depends(get_uow)
):
    try:
        groups_ids = article.groups_mentioned_ids
        artists_ids = article.artists_mentioned_ids

        # Turn publication_date to datetime
        pub_date = article.publication_date
        if isinstance(pub_date, str):
            pub_date = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))

        # Create Beanie DB model
        article_db = Article_db(
            **article.model_dump(exclude={"groups_mentioned_ids", "artists_mentioned_ids", "publication_date"}),
            groups_mentioned_ids=groups_ids,
            artists_mentioned_ids=artists_ids,
            publication_date=pub_date
        )

        # Save to DB
        created_article = await uow.articles.create(article_db)

        return created_article
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Test article creation error: {str(e)}")

@app.post("/api/events/merge", response_model=Event, status_code=201)
async def merge_articles_to_event(
    event: Event, 
    uow: IUnitOfWork = Depends(get_uow)
):
    """
    Create a new event and store it in the database.
    """
    try:
        event_db = Event_db(**event.model_dump())
        created_event = await uow.events.create(event_db)
        return created_event
    except Exception as e:
        raise HTTPException(
            status_code=400, 
            detail=f"Event creation error: {str(e)}"
        )