# NovaMart Assistant

An internal AI assistant for NovaMart store employees. It answers questions about company
policies (returns, refunds, warranties, discounts), looks up live order status through an
internal API, and declines to answer when the documentation does not cover the question,
instead of inventing an answer.

Built on the Google AI stack: a Gemini agent built with the Agent Development Kit (ADK),
grounded by hybrid retrieval (BM25 + embeddings) over NovaMart's policy documents.

## Status

Under active development. The build history is in the merged pull requests, one scoped
change per PR.

## Quickstart

Placeholder until the agent lands. The final version will be:

```bash
uv sync
cp .env.example .env   # add your Google AI Studio API key
make index             # build the retrieval index
make dev               # serve the app on http://localhost:8000
```
