import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import io
import soundfile as sf
import numpy as np

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

kokoro_session = None

@app.on_event("startup")
def startup():
    global kokoro_session
    from kokoro_onnx import Kokoro
    kokoro_session = Kokoro("kokoro-v1.0.onnx", "voices-v1.0.bin")

class TTSRequest(BaseModel):
    text: str
    voice: str = "af_sarah"
    speed: float = 1.0
    lang: str = "en-us"

@app.get("/")
def root():
    return {"status": "ok"}

@app.get("/voices")
def voices():
    return {
        "voices": [
            "af_alloy", "af_aoede", "af_bella", "af_heart",
            "af_jessica", "af_kore", "af_nicole", "af_nova",
            "af_river", "af_sarah", "af_sky",
            "am_adam", "am_michael"
        ]
    }

@app.post("/tts/stream")
async def tts_stream(req: TTSRequest):
    async def generate():
        try:
            all_samples = []
            sample_rate = None
            
            # Collect ALL chunks first
            stream = kokoro_session.create_stream(
                req.text,
                voice=req.voice,
                speed=req.speed,
                lang=req.lang
            )
            
            async for samples, sr in stream:
                all_samples.append(samples)
                if sample_rate is None:
                    sample_rate = sr
            
            # Make sure we got all chunks
            if all_samples and sample_rate:
                combined = np.concatenate(all_samples)
                # Add 0.5 seconds of silence
                silence = np.zeros(int(sample_rate * 0.5))
                combined = np.concatenate([combined, silence])
                
                buf = io.BytesIO()
                sf.write(buf, combined, sample_rate, format='WAV', subtype='PCM_16')
                buf.seek(0)
                yield buf.read()
                
        except Exception as e:
            print(f"Stream error: {e}")
    
    return StreamingResponse(
        generate(),
        media_type="audio/wav"
    )

@app.post("/tts")
def tts(req: TTSRequest):
    try:
        samples, sr = kokoro_session.create(
            req.text, 
            voice=req.voice, 
            speed=req.speed, 
            lang=req.lang
        )
        
        buf = io.BytesIO()
        sf.write(buf, samples, sr, format='WAV', subtype='PCM_16')
        buf.seek(0)
        
        return StreamingResponse(
            buf,
            media_type="audio/wav",
            headers={"Content-Disposition": "inline; filename=speech.wav"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))