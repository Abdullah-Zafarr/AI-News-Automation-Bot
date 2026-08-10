from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse

from src.news_bot.pipeline import run_news_pipeline

load_dotenv()
app = FastAPI(title="AI News Automation Bot")


@app.get("/", response_class=HTMLResponse)
def root() -> str:
    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI News Bot</title><style>
:root{color-scheme:dark;font-family:Inter,ui-sans-serif,system-ui,sans-serif}*{box-sizing:border-box}body{margin:0;background:#0b0d12;color:#f4f5f7}main{width:min(760px,calc(100% - 32px));margin:0 auto;padding:52px 0}.top{display:flex;align-items:center;justify-content:space-between;margin-bottom:54px}.brand{display:flex;gap:12px;align-items:center;font-weight:700;font-size:18px}.logo{width:34px;height:34px;border-radius:10px;background:linear-gradient(135deg,#7c5cff,#32d5b5);display:grid;place-items:center;font-size:17px}.pill{border:1px solid #263044;border-radius:99px;padding:7px 12px;color:#8e9bb2;font-size:12px}.hero h1{font-size:clamp(34px,7vw,62px);line-height:1.02;letter-spacing:-.05em;margin:0 0 17px}.hero p{color:#8e9bb2;font-size:16px;margin:0 0 34px}.card{background:#11151e;border:1px solid #202839;border-radius:18px;padding:24px;margin-top:28px}.row{display:flex;gap:14px;align-items:end}.field{flex:1}.field label{display:block;color:#8e9bb2;font-size:12px;margin:0 0 8px}.field input{width:100%;background:#0b0d12;border:1px solid #2b3549;border-radius:10px;padding:12px;color:#fff;font:inherit;outline:none}.field input:focus{border-color:#7c5cff}button{border:0;border-radius:10px;background:#7c5cff;color:white;padding:13px 18px;font:600 14px inherit;cursor:pointer}button:disabled{opacity:.55;cursor:wait}.status{display:flex;align-items:center;gap:9px;color:#aeb8cb;font-size:13px}.dot{width:8px;height:8px;border-radius:50%;background:#32d5b5}.result{white-space:pre-wrap;color:#8e9bb2;font:12px ui-monospace,monospace;line-height:1.5;margin-top:18px;max-height:230px;overflow:auto}footer{color:#566176;font-size:12px;margin-top:34px}@media(max-width:560px){.row{display:block}.field{margin-bottom:12px}button{width:100%}}
</style></head><body><main><div class="top"><div class="brand"><div class="logo">✦</div>AI News Bot</div><div class="pill">CrewAI · local</div></div>
<section class="hero"><h1>Your newsroom,<br><span style="color:#8e9bb2">on autopilot.</span></h1><p>Fetch, summarize, publish to Slack, and archive the latest stories.</p></section>
<div class="card"><div class="status"><span class="dot"></span><span id="health">Checking service…</span></div><div class="row" style="margin-top:24px"><button id="run">Run pipeline</button></div><div id="result" class="result"></div></div>
<footer>News sources · Groq summaries · Slack delivery · Google Sheets archive</footer></main><script>
const health=document.querySelector('#health'),run=document.querySelector('#run'),out=document.querySelector('#result');fetch('/api/health').then(r=>r.ok?r.json():Promise.reject()).then(()=>health.textContent='All systems operational').catch(()=>{health.textContent='Service unavailable';document.querySelector('.dot').style.background='#f06b7b'});
run.onclick=async()=>{run.disabled=true;run.textContent='Running…';out.textContent='The crew is working…';try{const r=await fetch('/api/run',{method:'POST'});const data=await r.json();if(!r.ok)throw Error(data.detail||'Request failed');out.textContent=JSON.stringify(data,null,2)}catch(e){out.textContent=e.message}finally{run.disabled=false;run.textContent='Run pipeline'}};
</script></body></html>"""


@app.post("/api/run")
def run_from_dashboard():
    """Run from the local dashboard; credentials stay server-side in .env."""
    try:
        result = run_news_pipeline()
        return {"success": True, "result": result.raw}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {exc}") from exc


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/cron")
def cron(request: Request):
    secret = os.getenv("CRON_SECRET")
    if not secret:
        raise HTTPException(status_code=500, detail="CRON_SECRET is not configured")

    if request.headers.get("authorization") != f"Bearer {secret}":
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        result = run_news_pipeline()
        return {"success": True, "result": result.raw}
    except Exception as exc:
        # Vercel logs the exception while the caller receives a useful HTTP error.
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {exc}") from exc
