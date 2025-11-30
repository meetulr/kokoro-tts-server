import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import onnxruntime as ort
import io
import soundfile as sf
import struct

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

kokoro_session = None

def create_optimized_session():
    sess_options = ort.SessionOptions()
    sess_options.intra_op_num_threads = 0
    sess_options.inter_op_num_threads = 1
    sess_options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    sess_options.enable_cpu_mem_arena = True
    sess_options.enable_mem_pattern = True
    sess_options.add_session_config_entry("session.intra_op.allow_spinning", "1")
    sess_options.add_session_config_entry("session.inter_op.allow_spinning", "1")
    sess_options.add_session_config_entry("session.set_denormal_as_zero", "1")
    return sess_options

@app.on_event("startup")
def startup():
    global kokoro_session
    from kokoro_onnx import Kokoro
    sess_options = create_optimized_session()
    kokoro_session = Kokoro(
        "kokoro-v1.0.onnx", 
        "voices-v1.0.bin",
        sess_options=sess_options
    )

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
def tts_stream(req: TTSRequest):
    def generate():
        try:
            stream = kokoro_session.create_stream(
                req.text,
                voice=req.voice,
                speed=req.speed,
                lang=req.lang
            )
            
            for samples, sample_rate in stream:
                buf = io.BytesIO()
                sf.write(buf, samples, sample_rate, format='WAV', subtype='PCM_16')
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