import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import io
import soundfile as sf
import numpy as np
import asyncio
from concurrent.futures import ThreadPoolExecutor

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

kokoro_session = None
executor = ThreadPoolExecutor(max_workers=4)

@app.on_event("startup")
def startup():
    global kokoro_session
    from kokoro_onnx import Kokoro
    kokoro_session = Kokoro("kokoro-v1.0.onnx", "voices-v1.0.bin")

VALID_VOICES = [
    "af_alloy", "af_aoede", "af_bella", "af_heart",
    "af_jessica", "af_kore", "af_nicole", "af_nova",
    "af_river", "af_sarah", "af_sky",
    "am_adam", "am_michael"
]

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
    return {"voices": VALID_VOICES}

@app.post("/tts/stream")
async def tts_stream(req: TTSRequest):
    if req.voice not in VALID_VOICES:
        raise HTTPException(status_code=400, detail=f"Invalid voice: {req.voice}")
    
    async def generate():
        try:
            stream = kokoro_session.create_stream(
                req.text,
                voice=req.voice,
                speed=req.speed,
                lang=req.lang
            )
            
            sample_rate = None
            
            # Stream raw PCM chunks as they're generated
            async for samples, sr in stream:
                if sample_rate is None:
                    sample_rate = sr
                # Convert float32 to int16 PCM
                pcm_data = (samples * 32767).astype(np.int16)
                yield pcm_data.tobytes()
            
            # Add 0.5 seconds of silence at the end
            if sample_rate:
                silence = np.zeros(int(sample_rate * 0.5), dtype=np.int16)
                yield silence.tobytes()
                
        except Exception as e:
            print(f"Stream error: {e}")
            raise
    
    return StreamingResponse(
        generate(),
        media_type="audio/pcm",
        headers={
            "X-Sample-Rate": "24000",
            "X-Channels": "1",
            "X-Bit-Depth": "16"
        }
    )

@app.post("/tts")
async def tts(req: TTSRequest):
    if req.voice not in VALID_VOICES:
        raise HTTPException(status_code=400, detail=f"Invalid voice: {req.voice}")
    
    try:
        # Run blocking TTS in thread pool to avoid blocking event loop
        loop = asyncio.get_event_loop()
        samples, sr = await loop.run_in_executor(
            executor,
            lambda: kokoro_session.create(
                req.text, 
                voice=req.voice, 
                speed=req.speed, 
                lang=req.lang
            )
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
