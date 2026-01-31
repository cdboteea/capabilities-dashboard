# X API Manual Retrieval – Design & Implementation Plan

*Last updated: $(date)*

## 1  Overview
This feature lets a user manually fetch the content of any public X (Twitter) post from the dashboard.  We stay within the Free tier (100 requests / month).

Key goals:
1. Provide a dedicated “X Posts” sub-tab under **URLs**.
2. Allow selecting one or more tweet URLs still marked *pending* and fetch them via the official X REST v2 API.
3. Persist tweet body text, link entities and media attachments; upload media to Google Drive just like email attachments.
4. Display remaining quota in real-time.

## 2  Database Changes (`004_x_post_support.sql`)
| Table | Purpose |
|-------|---------|
| `x_posts` | Store one row per tweet (PK `tweet_id`) + raw JSON payload |
| `x_media` | Map tweet media → Google Drive uploads |
| `x_api_usage` | Monthly quota tracker (100 calls) |
| Column update | `urls.api_used BOOLEAN` → marks URL fetched by API |

## 3  Backend (`email_processor`)
### 3.1 SimpleXAPIClient (`src/x_api_client.py`)
* Env var: `X_BEARER_TOKEN`
* Methods
  * `get_post(tweet_id)` → returns hydrated tweet w/ media/author expansions
  * `increment_usage()` & `get_usage()` – creates/updates `x_api_usage`
  * Raises `QuotaExceededError` if limit reached

### 3.2 Routes (FastAPI)
| Verb | Path | Description |
|------|------|-------------|
| `GET` | `/x-posts` | Paginated list of stored tweets (joins with `urls`) |
| `POST` | `/x-posts/fetch` | `{urls: [..]}` → fetch & store tweets |
| `GET` | `/x-posts/api-usage` | Remaining quota info |

Flow of `/x-posts/fetch`:
1. Parse tweet IDs from URLs.
2. Check quota → 429 if exceeded.
3. Call X API; store in `x_posts` (UPSERT).
4. For every media item:
   * Download best variant → Drive upload.
   * Insert `attachments` & `x_media` rows.
5. Update `urls.processing_status='completed'`, `api_used=true`.
6. Return summary list + updated quota.

## 4  Frontend (`web_interface`)
### 4.1 New Components
* **XPostsTab.tsx** – Data table with select-checkboxes & *Fetch Selected* button.
* **XAPIQuotaCard.tsx** – Progress bar (green <80%, yellow <100%, red = exceeded) polling every 30 s.

### 4.2 Service API (`src/services/api.ts`)
```
getXPosts(page, limit)
fetchXPosts(urls[])
getXUsage()
```

### 4.3 UX details
* Tabs: `URLs | X Posts`
* Columns: URL, Tweet ID, Author, Posted, Status.
* Status chips: *pending*, *completed*, *failed*.
* Toasts on success / quota errors.

## 5  Quota Logic
```
month = yyyy-mm (UTC)
if calls_used >= calls_limit → raise QuotaExceededError
```
Quota resets automatically on first fetch of new month.

## 6  Attachments
Downloaded media is treated identically to email attachments:
* Uploaded to Drive folder `idea-database-attachments` via existing `drive_client`.
* Entries appear in **Files** tab alongside other attachments.

## 7  Testing
1. Postman collection – happy path, 401 (no token), 429 (quota).
2. Unit tests for `x_api_client` with mock responses.
3. Cypress end-to-end – fetch tweet → check table & quota update.

---
Owner: @idea-db
Status: **Planned** – migration in progress. 