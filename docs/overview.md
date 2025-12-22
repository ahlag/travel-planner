# Open-Source LLM Travel Planner

## 1. Purpose
Build an open-source AI travel planner that generates personalized itineraries, events, and food recommendations for Tokyo, using scraped data and an open-source LLM.

## 2. Scope

### In Scope (MVP)
Generate 1–3 day itineraries, nearby events or restaurants for a single city. Start with Tokyo but allows flexibility in future changes for user to select big cities, i.e. Osaka/Kyoto.

Basic intents the LLM needs to respond to:
- generate itinerary
- events FAQ
- countries, cities, POIs FAQ
- LLM should ignore out of topic chats.

Incorporate user preferences (First-time Tokyo Visitor):
- Food preferences (Ramen, Halal, etc.)
- Events (Cultural)
- Budget (budget / mid / high or a number)
- Interests (culture, food, nature, shopping)

Use RAG with structured, metadata-rich content for:
- **Attractions** — with tags (category, neighborhood, duration, best time), coordinates, short description
- **Restaurants** — with cuisine, halal flag, price range, interest tags, coordinates
- **Core POI metadata** — type, category_tags, interest_tags, coordinates, short_description, last_updated timestamp

### Output (Structured, JSON-first)
The planner produces a structured daily plan using a JSON schema to ensure consistency and easier UI rendering:
- Daily itinerary (morning / afternoon / evening), structured as:
  - `time_of_day`
  - list of POI items with:
    - `poi_id`
    - `type` (attraction / restaurant / etc.)
    - `approx_time_minutes` (for attractions)
    - optional notes (e.g., food type, popularity, tips)
- Restaurant recommendations:
  - Selected based on user preferences such as cuisine, halal, price range
  - Returned as structured POI objects with metadata
- Simple map data:
  - Array of geo-coordinates (lat, lon) for all POIs used in the itinerary
  - Usable directly by map libraries (Leaflet, Mapbox, Google Maps)

### Technologies
- Mistral/LLaMA-class model or other Open Source Models for pretraining (PyTorch or Hugging Face)
- Vector store (FAISS/Chroma)
- LangChain/LangGraph for workflow

### Out of Scope (MVP)
- Live/real-time APIs (weather, events, prices)
- Multi-city routing
- Flight/hotel booking integrations
- User accounts or profile history
- Complex agents beyond basic planner + retriever

## 3. Key Requirements

### Functional
#### Phase 0
- **Users input**: city, days, preferences.
- **System retrieves POIs** from vector store (matching tags + city).
- **LLM generates**:
  - Day-by-day itinerary
  - Matching restaurants
- **System filters results by**:
  - `halal = true` or food categories when selected
  - budget range
- **Produce a map** showing selected POIs.
- Implement chat and user preference history in Chat

### Non-Functional
- **Fast inference** (<3–5 seconds per plan with 7B model)
- **Fully open-source stack**
- **Easy to deploy** locally, on AWS, or GCP
- **Data updatable** via lightweight scraping pipeline
- **Hallucination control**: the LLM must use only POIs retrieved from RAG, identified by a valid POI ID, and must not invent new locations.
- **Safety**: Add a UI note stating that the tool uses static data and may be outdated, ensure family-inappropriate POIs are not recommended by using a family friendly tag when needed, and keep all suggestions aligned with user context.

## 4. Workflow (MVP)
1. User Input
2. RAG Retrieval (city + preferences)
3. LLM Planner (creates structured itinerary)
4. Plan and Map Generator
5. Final Output

## 5. Deliverables
- Basic web UI
- Trained Model
- Scraper scripts for 1–3 cities
- Vector database with embedded POI data
- LLM-based itinerary generator (must produce a structured JSON output and respect basic distance and time constraints so the model does not schedule far-apart neighborhoods (for example Odaiba, Asakusa, and Shinjuku) in the same time block).
- Map output module
- README + minimal documentation

## 6. FAQs

### 1. What is the schema of POIs?
**POI Schema** (for attractions, restaurants, shops, event venues)
Each POI in the vector store should follow this schema:

- `id`: string – stable unique ID for the POI
- `name`: string – POI name (English / local)
- `type`: enum – `attraction` | `restaurant` | `shop` | `event_venue`
- `category_tags`: string[] – tags such as temple, park, ramen, izakaya, mall
- `neighborhood`: string – e.g., Shinjuku, Shibuya, Asakusa
- `price_range`: enum – 1 | 2 | 3 (or $ | $$ | $$$)
- `halal`: enum – `true` | `false` | `unknown` (for restaurants)
- `cuisine`: string[] – e.g., ramen, sushi, halal, vegan (restaurants only)
- `interest_tags`: string[] – e.g., culture, food, nature, shopping, nightlife, kids_friendly
- `coordinates`: object – `{ lat: number, lon: number }`
- `typical_duration_minutes`: number – average time spent (attractions)
- `best_time_of_day`: enum – `morning` | `afternoon` | `evening` | `night`
- `short_description`: string – 2–3 sentence summary for UI
- `source_url`: string – original data/source page
- `last_updated_ts`: datetime – last time this POI record was refreshed

**Example JSON**
```json
{
  "id": "poi_tokyo_sensoji_001",
  "name": "Sensō-ji Temple",
  "type": "attraction",
  "category_tags": ["temple", "historical", "landmark"],
  "neighborhood": "Asakusa",
  "price_range": 1,
  "halal": "unknown",
  "cuisine": [],
  "interest_tags": ["culture", "history", "photography"],
  "coordinates": { "lat": 35.7148, "lon": 139.7967 },
  "typical_duration_minutes": 60,
  "best_time_of_day": "morning",
  "short_description": "One of Tokyo's oldest and most famous temples, with a vibrant shopping street (Nakamise) leading up to the main hall.",
  "source_url": "https://example.com/sensoji",
  "last_updated_ts": "2025-12-02T09:00:00Z"
}
```

### 2. What is the sample JSON output of planner?
```json
{
  "city": "Tokyo",
  "days": [
    {
      "day_number": 1,
      "parts": [
        {
          "time_of_day": "morning",
          "items": [
            {
              "poi_id": "sensoji_temple",
              "type": "attraction",
              "approx_time_minutes": 90
            }
          ]
        },
        {
          "time_of_day": "lunch",
          "items": [
            {
              "poi_id": "ichiran_asakusa",
              "type": "restaurant",
              "notes": "Ramen, mid-range, popular with tourists"
            }
          ]
        }
      ]
    }
  ]
}
```
