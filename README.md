---
title: Kokoro TTS Server
emoji: 🎤
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
---

# Kokoro TTS Streaming Server

High-performance Kokoro TTS API with streaming support.

## Endpoints

- `GET /` - Health check
- `GET /voices` - List available voices
- `POST /tts` - Generate complete audio
- `POST /tts/stream` - Stream audio generation

## Usage

```python
import requests

response = requests.post(
    "https://YOUR_USERNAME-kokoro-tts-server.hf.space/tts",
    json={
        "text": "Hello world",
        "voice": "af_sarah",
        "speed": 1.0,
        "lang": "en-us"
    }
)

with open("output.wav", "wb") as f:
    f.write(response.content)
```

## Available Voices

Female: af_alloy, af_aoede, af_bella, af_heart, af_jessica, af_kore, af_nicole, af_nova, af_river, af_sarah, af_sky

Male: am_adam, am_michael
