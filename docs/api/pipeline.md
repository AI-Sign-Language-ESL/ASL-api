# Sign Language Translation Pipeline

## Overview

The sign language translation pipeline enables real-time conversion of sign language video frames to Arabic text. The pipeline is orchestrated by `SignTranslationService` and flows through two AI stages:

1. **Computer Vision (CV)** — Video frames → English gloss text
2. **NLP** — English gloss → Arabic text

## Architecture

```
Frontend Camera
     │
     ▼  binary frames (WebSocket)
Backend (SignTranslationConsumer)
     │
     ▼  buffer every 5 seconds
StreamingTranslationService
     │
     ▼  send batch
SignTranslationService.translate(frames)
     │
     ├──► CVWebSocketClient.send_video_chunk(chunk)
     │       │
     │       ▼  CV_MODEL_WS_URL (WebSocket)
     │    CV Model
     │       │
     │       ▼  {"gloss": "HELLO HOW ARE YOU"}
     │
     ├──► emits "gloss_received" event to frontend
     │
     └──► NLPModelClient.translate_gloss(gloss)
             │
             ▼  NLP_MODEL_URL (HTTP POST /translate)
          NLP Service
             │
             ▼  {"text": "مرحباً كيف حالك"}
             │
          emits "translation_received" event to frontend
```

## WebSocket Events

### Client → Server

| Message | Description |
|---|---|
| Binary frames | Video frame data (JPEG/raw bytes) |
| `{"action": "start", "output_type": "text"}` | Start translation session |
| `{"action": "stop"}` | Stop translation session |
| `{"type": "ping"}` | Heartbeat keep-alive |

### Server → Client

| Event Type | Payload | Description |
|---|---|---|
| `translation_started` | `{"type": "translation_started", "request_id": "..."}` | Pipeline processing started |
| `gloss_received` | `{"type": "gloss_received", "gloss": "HELLO HOW ARE YOU"}` | CV model returned gloss |
| `translation_received` | `{"type": "translation_received", "gloss": "...", "text": "مرحباً كيف حالك"}` | Full translation complete |
| `translation_error` | `{"type": "translation_error", "stage": "cv", "message": "..."}` | Error at CV or NLP stage |
| `partial_result` | `{"type": "partial_result", "text": "..."}` | Legacy intermediate result |
| `final_result` | `{"type": "final_result", "text": "...", "audio": "..."}` | Final result with optional audio |
| `pong` | `{"type": "pong"}` | Heartbeat response |
| `status` | `{"type": "status", "status": "processing", "translation_id": 1}` | Session status |
| `warning` | `{"type": "warning", "message": "..."}` | Non-fatal warning |
| `error` | `{"type": "error", "message": "..."}` | Fatal error |

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `CV_MODEL_WS_URL` | Yes | — | WebSocket URL for CV model (e.g. `ws://localhost:8002/ws/cv`) |
| `NLP_MODEL_URL` | Yes | — | HTTP URL for NLP model (e.g. `http://localhost:8003`) |
| `CV_WS_TIMEOUT` | No | `30` | WebSocket response timeout (seconds) |
| `NLP_REQUEST_TIMEOUT` | No | `30` | NLP HTTP request timeout (seconds) |
| `MAX_CV_RETRIES` | No | `3` | Max retry attempts for CV calls |
| `NLP_RETRIES` | No | `3` | Max retry attempts for NLP calls |

## AI Service Contracts

### Computer Vision (WebSocket)

**Endpoint:** `CV_MODEL_WS_URL`

**Request:** Binary video frame data (WebSocket binary message)

**Response (WebSocket text message):**
```json
{"gloss": "HELLO HOW ARE YOU"}
```

### NLP Translation (HTTP)

**Endpoint:** `POST {NLP_MODEL_URL}/translate`

**Request:**
```json
{"gloss": "HELLO HOW ARE YOU"}
```

**Response:**
```json
{"text": "مرحباً كيف حالك"}
```

## Dependencies

### `SignTranslationService`

The main orchestration service. Accepts injected dependencies:

```python
service = SignTranslationService(
    cv_client=CVWebSocketClient(),       # Computer Vision client
    nlp_client=NLPModelClient(),          # NLP translation client
    retry_handler=RetryHandler(...),      # Retry with exponential backoff
    config=PipelineConfig(...),           # Pipeline limits and timeouts
    event_callback=async_callable,        # Event emitter (e.g. WebSocket send)
)
```

### `CVWebSocketClient`

- Sends video chunks via WebSocket to `CV_MODEL_WS_URL`
- Falls back to HTTP `ComputerVisionClient` if WebSocket unavailable
- Method: `send_video_chunk(video_chunk: bytes) -> CVResponse`
- Returns: `CVResponse(gloss="HELLO HOW ARE YOU")`

### `NLPModelClient`

- Sends gloss string via HTTP POST to `{NLP_MODEL_URL}/translate`
- Extends `BaseAIClient` for shared HTTP infrastructure
- Method: `translate_gloss(gloss: str) -> NLPResponse`
- Returns: `NLPResponse(text="مرحباً كيف حالك")`

### `RetryHandler`

- Configurable async retry with exponential backoff
- Default: 3 retries, 0.5s base delay, 2x backoff, 5s max delay
- Used independently for CV and NLP stages

## Data Flow

1. **Frontend** opens WebSocket to `ws://<host>/ws/translation/stream/`
2. **Frontend** sends `{"action": "start"}` to begin translation
3. **Frontend** streams binary video frames at ~10-30 fps
4. **Backend** buffers frames in a deque (max 120)
5. **Every 5 seconds**, buffered frames are batched (max 30) and sent to the pipeline
6. **CV stage:** Video chunk → WebSocket → gloss text
7. **NLP stage:** Gloss text → HTTP POST → Arabic text
8. **Frontend receives:** `translation_started` → `gloss_received` → `translation_received`
9. **Frontend** sends `{"action": "stop"}` when signing is done
10. **Backend** generates TTS audio and sends `final_result`

## Error Handling

| Scenario | Behavior |
|---|---|
| CV WebSocket failure | Falls back to HTTP `ComputerVisionClient` |
| CV timeout | Retries up to `MAX_CV_RETRIES` times with backoff |
| NLP failure | Retries up to `NLP_RETRIES` times with backoff |
| All retries exhausted | Emits `translation_error` event to frontend |
| Empty frames | Returns `TranslationPipelineResult(success=False)` |
| Pipeline timeout | Sends `warning` event and continues buffering |

## Testing

```bash
# Unit tests
pytest tests/apps/v1/translation/test_sign_translation_service.py -v

# Integration tests
pytest tests/apps/v1/translation/test_integration_pipeline.py -v

# All translation tests
pytest tests/apps/v1/translation/ -v
```
