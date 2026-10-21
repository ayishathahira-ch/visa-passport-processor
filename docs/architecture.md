# Architecture

```mermaid
flowchart LR
    A[Gmail inbox] -->|new unread email| B[n8n: Gmail Trigger]
    B --> C{Subject contains 'visa'?}
    C -- no --> X[Stop]
    C -- yes --> D[Download attachment]
    D --> E[Code node: pick file, classify visa type]
    E -->|POST + X-API-Key| F1
    subgraph API[Flask API /process-passport]
      direction TB
      F1[Validate type and size] --> F2[Tesseract OCR]
      F2 --> F3{MRZ found and check digits pass?}
      F3 -- yes --> F4[MRZ fields]
      F3 -- no --> F5[Gemini or regex fallback]
    end
    F4 --> G[n8n: Google Sheets append row]
    F5 --> G
```

## Design decisions

| Decision | Why |
|---|---|
| MRZ parsing with check digits first | Deterministic and verifiable; an LLM can silently hallucinate a digit, a checksum cannot |
| OCR repair step before checksum validation | Tesseract confuses `<` / `O` / `0`; layout-aware repair is safe because checksums still gate the result |
| Gemini only as a fallback, key from environment | No secret travels in request bodies or process arguments |
| Temp files in a `TemporaryDirectory` | Passport scans are deleted even if OCR crashes |
| `X-API-Key` + localhost bind | The API handles identity documents and must not be open |
| Private Google Sheet | The output is PII; the old setup script made it world-editable |
