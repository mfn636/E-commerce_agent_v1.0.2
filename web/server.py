"""
web/server.py

极简 Web 调试台：FastAPI 后端 + 单页前端，连到 EcommerceAgent。
- GET  /           聊天页面
- POST /chat       {session_id, message} -> {replies: [...], state: "..."}
- POST /reset      {session_id}          -> 清空该会话（内存 + 快照）

启动（项目根目录）：
    python -m uvicorn web.server:app --port 8000
浏览器打开 http://127.0.0.1:8000
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from agent.core.loop import EcommerceAgent
from llm.client import LLMClient

app = FastAPI(title="电商智能客服 Agent · 调试台")

_LLM = LLMClient()              # 共享一个 LLM 客户端
_AGENTS: dict = {}              # session_id -> EcommerceAgent
_INDEX = Path(__file__).parent / "index.html"


def _get_agent(session_id: str) -> EcommerceAgent:
    if session_id not in _AGENTS:
        _AGENTS[session_id] = EcommerceAgent(session_id=session_id, llm=_LLM)
    return _AGENTS[session_id]


class ChatRequest(BaseModel):
    session_id: str = "web"
    message: str


class ResetRequest(BaseModel):
    session_id: str = "web"


@app.get("/", response_class=HTMLResponse)
def index():
    return _INDEX.read_text(encoding="utf-8")


@app.post("/chat")
def chat(req: ChatRequest):
    agent = _get_agent(req.session_id)
    result = agent.run(req.message)          # TurnResult：replies + tool_calls + usage
    return {"replies": result.replies, "state": agent.state.text, "usage": result.usage}


@app.post("/reset")
def reset(req: ResetRequest):
    _AGENTS.pop(req.session_id, None)
    snapshot = Path("sessions") / f"{req.session_id}.json"
    if snapshot.is_file():
        snapshot.unlink()
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
