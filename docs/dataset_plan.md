# Dataset & Scraping Strategy

## 1. Unified POI Schema
All scraped data will be normalized to this single schema to ensure consistency across the application.

```typescript
interface POI {
  id: string;                      // Unique ID (hash of source URL or internal ID)
  name: string;                    // Name in English (or Romanized)
  type: "attraction" | "restaurant" | "shop" | "event_venue";
  category_tags: string[];         // e.g., ["Temple", "History", "Nature"]
  neighborhood: string;            // e.g., "Shinjuku", "Asakusa"
  price_range?: 1 | 2 | 3 | 4;     // Normalized price: 1=Cheap, 4=Luxury
  halal?: "true" | "false" | "unknown"; // Specific for Muslim-friendly travel
  cuisine?: string[];              // For restaurants: ["Ramen", "Sushi"]
  interest_tags: string[];         // e.g., ["Culture", "Kids Friendly", "Nightlife"]
  coordinates: {
    lat: number;
    lon: number;
  };
  typical_duration_minutes?: number; // Estimated visit time
  best_time_of_day?: "morning" | "afternoon" | "evening" | "night";
  short_description: string;       // 2-3 sentence summary
  source_url: string;              // Link to original scraping source
  last_updated_ts: string;         // ISO Datetime
}
```

## 2. Selected Data Sources

### A. Attractions
**Primary Source**: [Go Tokyo (Official Travel Guide)](https://www.gotokyo.org/en/spot/index.html)
*   **Coverage**: Comprehensive list of temples, museums, parks, and landmarks.
*   **Data Quality**: High. Structured "Mood" tags, distinct area definitions, and official descriptions.
*   **Field Mapping**:
    *   `category_tags` <- GoTokyos "Mood" / "Category" filters.
    *   `neighborhood` <- "Area" field.
    *   `coordinates` <- Parsed from embedded Google Maps links.

### B. Restaurants
**Strategy**: Aggregating "Best of" lists for specific categories to ensure quality over quantity.

**Source 1**: [TripAdvisor](https://www.tripadvisor.com/)
*   **Role**: Broad category coverage, tourist-friendly English content, and dietary tags.
*   **Categories to Scrape**:
    1.  Sushi
    2.  Ramen
    3.  Yakiniku (BBQ)
    4.  Izakaya
    5.  Tempura
    6.  Udon/Soba
    7.  Unagi (Eel)
    8.  Curry
    9.  Tonkatsu
    10. Cafe / Dessert
*   **Field Mapping**:
    *   `price_range` <- Mapped from `$` signs ($ = 1, $$$$ = 4).
    *   `dietary_tags` <- "Vegetarian Friendly", "Vegan Options".

**Source 2**: [Halal Gourmet Japan](https://www.halalgourmet.jp/)
*   **Role**: Definitive source for the `halal` field.
*   **Mapping**:
    *   `halal` <- "Halal Certified" = true.

**Source 3**: [Tabelog (English)](https://tabelog.com/en/)
*   **Role**: Primary validation for "Authencity" & Quality.
*   **Usage**: Supplementary scraping of "Hyakumeiten" (100 Famous Stores) lists to identify top-tier local spots.
*   **Pros**: High trust, local standard (3.5+ stars = excellent).
*   **Cons**: Stricter scraping policy; will be used sparingly for "Top lists" only. Tabelog is stricter technically and legally (Terms of Service prohibit scraping). TripAdvisor is more permissive for "personal use" style scraping of lists.

### C. Shops
**Primary Source**: [Go Tokyo Shopping Guide](https://www.gotokyo.org/en/spot/shopping/index.html)
*   **Coverage**: Major department stores, electronics hubs (Akihabara), and traditional streets.
*   **Supplement**: [Time Out Tokyo](https://www.timeout.com/tokyo/shopping) "Best Shops" lists for curated independent stores.

### D. Events
**Primary Source**: [Go Tokyo Event Calendar](https://www.gotokyo.org/en/event/index.html)
*   **Coverage**: Major festivals (Matsuri), exhibitions, and seasonal events.

### E. FAQ
**Source**: [Wikivoyage Tokyo](https://en.wikivoyage.org/wiki/Tokyo) (and district sub-pages)
*   **Role**: Suitable for FAQ type questions, has rich textual descriptions, practical tips, and "See"/"Do"/"Eat" listings.
*   **Why**: Structured "listing" templates (vCard style), and excellent for RAG context.
*   **Field Mapping**:
    *   `description` <- Wiki content is often more detailed/neutral than official sites.
    *   `coordinates` <- Extracted from listing templates.
    *   `type` <- Inferred from section headers ("See"->Attraction, "Eat"->Restaurant).


## 3. Data Ingestion Pipeline

1.  **Scrapers (`src/data/scrapers/`)**: Individual scripts for each domain (e.g., `gotokyo_attractions.py`).
2.  **Raw Storage (`src/data/raw/`)**: JSON dumps of the raw scraped data.
3.  **Normalization**: A centralized processor converts raw JSONs into the **Unified POI Schema**.
4.  **Vector Store**: Enriched text (description + tags) is embedded and stored for RAG.

## 4. Gaps & Mitigations
*   **Missing Coordinates**: If source lacks lat/lon, use a Geocoding API (e.g., OpenStreetMap Nominatim) during the normalization phase.
*   **Missing Duration**: `typical_duration_minutes` is rarely explicit.
    *   *Mitigation*: Set defaults based on type (Museum=90, Park=45) or use the LLM to estimate based on description.
*   **Dynamic Opening Hours**: We will scrape `best_time_of_day` where possible, but exact hours might be skipped for MVP to reduce complexity.
