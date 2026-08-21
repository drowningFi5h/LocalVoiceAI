from fastapi import FastAPI

app = FastAPI(title="LocalVoiceAI")

@app.get("/api/health")
async def health():
    return {"status": "ok"}
