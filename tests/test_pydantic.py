from datetime import datetime
from pydantic import ValidationError
from app.models.articles import Article

data = {
    "title": "K-pop rising star group 'Aegis' first world tour preview",
    "author": "Lee",
    "source_id": "global_pop_weekly",
    "publication_date": "2025-11-18T15:30:00Z",
    "text": "New generation K-pop idol group Aegis released a teaser trailer today...",
    "images": ["https://placehold.co/800x450/333333/ffffff?text=Concert+Poster+Image+URL"],
    "video": None,
    "language": "zh-TW",
    "in_event": True,
    "event_id": "65d706a1467f938c4f82d2f9",
    "groups_mentioned_ids": ["65d706b3467f938c4f82d305"],
    "artists_mentioned_ids": ["65d706b3467f938c4f82d306", "65d706b3467f938c4f82d307"],
    "summary": "K-pop group Aegis has announced its first world tour...",
    "sentiment": 0.95,
    "artists_mentioned": ["Minho", "Jina"],
    "groups_mentioned": ["Aegis"],
    "tags": ["K-pop", "Concert", "World Tour", "Rising Star"],
    "countries": ["KR", "USA", "JP"]
}

try:
    article = Article(**data)
    print("✅ Pydantic validation passed!")
except ValidationError as e:
    print(e.json())
