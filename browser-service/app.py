from fastapi import FastAPI

app = FastAPI()


@app.get("/health/browser")
def health_browser():
    return {"status": "ok"}
