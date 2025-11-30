# Kokoro TTS Server

High-performance Kokoro TTS streaming server on Hugging Face Spaces.

## Endpoints

- `GET /` - Health check
- `GET /voices` - List available voices
- `POST /tts` - Generate speech

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

## Performance Optimizations

- ONNX Runtime CPU optimizations enabled
- Thread spinning for low latency
- Memory arena for efficient allocation
- Denormal-as-zero for faster float ops
