## System Design: Scalable Search Engine System

## Requirements
- 4 billion pages crawled per month
- ~100 billion search queries per month via an  API endpoint
- On-demand re-crawl requests (submitted via API) with 1-hour SLA

## Capacity math

- **Crawling rage (avg):** 4,000,000,000 pages / month ≈ 1,543 pages/sec
- **Query load (avg):** 100,000,000,000 queries / month ≈ 38,580 queries/sec
- **Storage:** if extracted text per page ≈ 20 KB → raw extracted text ≈ 80 TB
- **Total Storage:** Add indexes, metadata, redundancy, replication, and intermediate structures,
  let's multiply by 80*3 = 240 TB


## 1. Query System

### 1.1 User Frontend
Web browser and Mobile App that allows users to search for content. It hits the [1.2 Load Balancer / API Gateway](#12-load-balancer--api-gateway).

### 1.2 Load Balancer / API Gateway
- Make the user request to the right backend service ([1.3 Query App](#13-query-app)).
- Cache queries for frequent queries (1.4 Cache).

### 1.3 Query API
REST API that receives and parses the query and returns results.

- Apply constraints on the query (e.g. query max length).
- Query time boosting.
  - Query-time boosts are a technique used in search engines to dynamically adjust the relevance and ranking of search results for specific queries without reindexing documents. This is achieved by applying a boost factor to certain parts of a query to make them more important than others, allowing for on-the-fly adjustments based on context like location or purchase history. For example, a query for "apple" could be boosted to rank "apple products" higher for a user with a history of buying electronics.
- Handle synonyms.
- Return the results to the user frontend [1.1 User Frontend](#11-user-frontend).

- Request the [2. Shared Inverted Index Cluster](#2-shared-inverted-index-cluster).


## 2. Shared Inverted Index Cluster
A sharded inverted index is a distributed data structure that divides the postings lists of a standard inverted index
across multiple servers (shards) to handle large datasets more efficiently. It maps terms to the documents they appear in,
but the index is broken into smaller, manageable pieces, with each shard storing a portion of the complete inverted index.

- Index is sharded (by doc id hash, domain, or term). Each shard is replicated (N=2/3).

Use Elasticsearch for it.

Add a Near-Real-Time Index Layer besides the main index to ingest high-priority re-crawled documents with <5 minutes delay, which is later merged asynchronously into main shards.

### 2.1 Make the tokenization (5.5 Tokenizer)

## 3. Ranker
- Feature extraction + ML model served separately with low latency (microsecond to low ms); feature store must be fast.
- Serve the ranking results to the [1.3 Query App](#13-query-app).
- Ranker may have multiple replicas to handle high load.
- Receives training data from the [5.2 Ingest App](#52-ingest-app)
- Ranking logs and document features are stored for offline model training.
- New ML models are deployed via a Model Registry, not directly from the ingest pipeline.

## 4. Crawler System

### 4.1 Re-crawl API

- REST API that allows users to re-crawl a specific domain or a list of domains, check the status of the re-crawl.

### 4.2 URL Frontier / Priority Queue

A priority queue that stores URLs to crawl.

- Per-host queues
- Politeness rules (min delay between fetches)
- Priority scoring for re-crawl requests
- Backoff rules for slow or failing hosts
- Persistent storage of crawl state

### 4.3 Fetch Workers

Fetch URLs from the [4.2 URL Frontier / Priority Queue](#42-url-frontier--priority-queue) and sends them to the
[4.4 Parser, extractor, and deduplication](#44-parser-extractor-and-deduplication).

### 4.4 Parser, extractor, and deduplication

- Parse HTML pages.
- Deduplicate URLs.
- Send full pages and the extracted text to the [5.1 Pub Sub / Kafka](#51-pub-sub--kafka).

## 5. Ingest System

Extract anchor text and outbound links to build a Link Graph used for ranking signals and crawl scheduling.

### 5.1 Pub Sub / Kafka

This buffering decouples fetching from indexing and absorbs spikes (re-crawl surges).

### 5.2 Ingest App

- Consume [5.1 Pub Sub / Kafka](#51-pub-sub--kafka) messages.
- Store metadata (e.g. crawl date) to the 5.3 Meta Store.
- Store HTML pages / snapshots in the 5.4 Document Store (S3).
- Only processed text and metadata flow into the [2. Shared Inverted Index Cluster](#2-shared-inverted-index-cluster). Full HTML is archived in the Document Store.

### 5.3 Meta Store
- Content hash
- ETag / Last-Modified
- Crawl frequency settings
- Re-crawl deadlines (for SLA)

## Observability

- Kafka lag
- Query latency p95/p99
- Index merge queue depth
- Crawl success rate
- Re-crawl SLA %
- Document ingestion lag
