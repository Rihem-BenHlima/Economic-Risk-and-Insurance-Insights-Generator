"""agent.py: answers ONE question by letting the model use tools, in a loop.

run(llm, history, message, cfg) -> {"reply": str, "sources": [str], "mode": "offline" | "gemini", "tools": [{"name", "args", "ok"}]}

The loop:
    1. clean the history (only user and assistant text, the last turns, each cut to a size limit) and add the new question
    2. ask the model (llm.generate) with the system prompt (prompts.SYSTEM) and the tool declarations (registry.specs)
    3. if the model asks for tools: run each through registry.call (read-only, allow-listed), add the results, go back to 2
    4. if the model answers in text: return it with the sources of the tools that were used
    5. stop after cfg["max_tool_rounds"] rounds; if the model fails (network, key, quota) return a plain error reply instead of crashing,
       so the page can say so and fall back to its own offline answers
It never touches the network itself and never sees the API key: that stays inside llm.GeminiLLM.
"""
import prompts
import registry


def clean_history(history, max_turns, max_chars):
    """Keeps only well-formed user/assistant text turns, the last `max_turns` of them, each cut to `max_chars`."""
    out = []
    for m in history if isinstance(history, list) else []:
        if isinstance(m, dict) and m.get("role") in ("user", "assistant") and isinstance(m.get("content"), str) and m["content"].strip():
            out.append({"role": m["role"], "content": m["content"][:max_chars]})
    return out[-2 * max_turns:]


def run(llm, history, message, cfg):
    msgs = clean_history(history, cfg["max_history_turns"], 2000) + [{"role": "user", "content": message}]
    specs = registry.specs(cfg["enable_web"])
    sources, calls = [], []
    for _ in range(cfg["max_tool_rounds"]):
        try:
            out = llm.generate(prompts.SYSTEM, msgs, specs)
        except Exception as e:                                       # the key, the network or the quota: tell the page, never crash
            return {"reply": "The language model could not be reached, so I cannot answer this question now.", "sources": sources, "mode": llm.name, "tools": calls,
                    "error": type(e).__name__}
        if out.get("tool_calls"):
            msgs.append({"role": "assistant", "tool_calls": out["tool_calls"]})
            for c in out["tool_calls"]:
                result, source = registry.call(c["name"], c.get("args"), cfg["enable_web"], **cfg.get("tool_extra", {}))
                msgs.append({"role": "tool", "name": c["name"], "result": result, "call_id": c.get("id")})
                calls.append({"name": c["name"], "args": c.get("args") or {}, "ok": "error" not in result})
                if source and source not in sources:
                    sources.append(source)
            continue
        return {"reply": out["text"], "sources": sources, "mode": llm.name, "tools": calls}
    return {"reply": "I could not settle this question within the allowed steps. Please ask it more simply.", "sources": sources, "mode": llm.name, "tools": calls}
