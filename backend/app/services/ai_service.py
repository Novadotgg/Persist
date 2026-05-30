import httpx
import structlog
import json
import re
from typing import Optional, List
from app.core.config import settings

logger = structlog.get_logger()

async def call_llm(model: str, prompt: str, system_prompt: Optional[str] = None, timeout: float = 30.0) -> str:
    """
    Consolidated helper to call local LLM (Ollama) with multi-tiered fallback logic:
      Tier 1: Local Ollama call.
      Tier 2: Remote API fallback (OpenAI/Gemini) if configured.
      Tier 3: Graceful degradation to heuristic keyword/rule matching if completely offline.
    """
    import time
    start_time = time.time()
    prompt_preview = prompt[:200].replace("\n", " ")
    logger.info("Requesting LLM generation", model=model, timeout=timeout, prompt_preview=prompt_preview)

    # Tier 1: Local Ollama Call
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            json_payload = {
                "model": model,
                "prompt": prompt,
                "stream": False
            }
            if system_prompt:
                json_payload["system"] = system_prompt

            response = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/generate",
                json=json_payload
            )
            if response.status_code == 200:
                duration = round(time.time() - start_time, 2)
                raw_text = response.json().get("response", "").strip()
                logger.info(
                    "LLM generation successful (Ollama)",
                    duration_sec=duration,
                    response_preview=raw_text[:300].replace("\n", " ")
                )
                try:
                    from app.core.metrics import AI_GENERATION_LATENCY_SECONDS
                    AI_GENERATION_LATENCY_SECONDS.labels(model=model, provider="ollama").observe(duration)
                except Exception:
                    pass
                return raw_text
            else:
                logger.warning(
                    "Ollama returned non-200 status code",
                    status_code=response.status_code,
                    body=response.text[:200]
                )
    except (httpx.ConnectError, httpx.TimeoutException) as e:
        logger.warning("Local Ollama service unreachable or timed out", error=str(e), timeout=timeout)
    except Exception as e:
        logger.error("Unexpected error calling local Ollama model", error=str(e))

    # Tier 2: Remote Fallback (if configured)
    fallback_provider = getattr(settings, "FALLBACK_PROVIDER", None)
    fallback_api_key = getattr(settings, "FALLBACK_API_KEY", None)
    
    if fallback_provider and fallback_api_key:
        try:
            logger.info("Attempting remote fallback LLM call", provider=fallback_provider)
            if fallback_provider == "openai":
                fallback_model = getattr(settings, "FALLBACK_MODEL", "gpt-4o-mini")
                async with httpx.AsyncClient(timeout=timeout) as client:
                    headers = {
                        "Authorization": f"Bearer {fallback_api_key}",
                        "Content-Type": "application/json"
                     }
                    messages = []
                    if system_prompt:
                        messages.append({"role": "system", "content": system_prompt})
                    messages.append({"role": "user", "content": prompt})
                    
                    response = await client.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers=headers,
                        json={
                            "model": fallback_model,
                            "messages": messages,
                            "temperature": 0.2
                        }
                    )
                    if response.status_code == 200:
                        logger.info("LLM generation successful (OpenAI fallback)")
                        duration = time.time() - start_time
                        try:
                            from app.core.metrics import AI_GENERATION_LATENCY_SECONDS
                            AI_GENERATION_LATENCY_SECONDS.labels(model=fallback_model, provider="openai").observe(duration)
                        except Exception:
                            pass
                        return response.json()["choices"][0]["message"]["content"].strip()
                    else:
                        logger.warning("OpenAI fallback endpoint returned non-200", status_code=response.status_code)
                        
            elif fallback_provider == "gemini":
                # Call Gemini API directly (via REST endpoint)
                fallback_model = getattr(settings, "FALLBACK_MODEL", "gemini-1.5-flash")
                # Gemini endpoint format: https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={API_KEY}
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{fallback_model}:generateContent?key={fallback_api_key}"
                async with httpx.AsyncClient(timeout=timeout) as client:
                    # Construct Gemini payload
                    contents = []
                    if system_prompt:
                        contents.append({"role": "user", "parts": [{"text": f"System Instruction: {system_prompt}"}]})
                    contents.append({"role": "user", "parts": [{"text": prompt}]})
                    
                    response = await client.post(
                        url,
                        json={"contents": contents}
                    )
                    if response.status_code == 200:
                        logger.info("LLM generation successful (Gemini fallback)")
                        candidates = response.json().get("candidates", [])
                        if candidates:
                            duration = time.time() - start_time
                            try:
                                from app.core.metrics import AI_GENERATION_LATENCY_SECONDS
                                AI_GENERATION_LATENCY_SECONDS.labels(model=fallback_model, provider="gemini").observe(duration)
                            except Exception:
                                pass
                            return candidates[0]["content"]["parts"][0]["text"].strip()
                    else:
                        logger.warning("Gemini fallback endpoint returned non-200", status_code=response.status_code)
        except Exception as e:
            logger.error("Failed remote API fallback call", provider=fallback_provider, error=str(e))

    # Tier 3: Graceful Degradation (Heuristic Fallback)
    logger.warning("All LLM providers unavailable. Activating heuristic fallback degradation.")
    try:
        from app.core.metrics import AI_GENERATION_LATENCY_SECONDS
        AI_GENERATION_LATENCY_SECONDS.labels(model="heuristic", provider="offline").observe(time.time() - start_time)
    except Exception:
        pass
    return apply_heuristic_fallback(prompt)

def apply_heuristic_fallback(prompt: str) -> str:
    """
    Apply regex/keyword parsing rules to fulfill queries when AI models are unavailable.
    """
    prompt_lower = prompt.lower()
    
    # 1. Fallback for priority classification
    if "priority" in prompt_lower or "classify request priority" in prompt_lower:
        # Scan for urgent keywords
        urgent_keywords = ["prod", "outage", "critical", "emergency", "down", "broken", "fatal", "blocker"]
        for kw in urgent_keywords:
            if kw in prompt_lower:
                logger.info("Heuristic priority matched (Urgent keyword)", keyword=kw)
                return "4"
        return "2"  # Standard default medium-low priority

    # 2. Fallback for summarization
    if "summarize" in prompt_lower:
        # Locate the content portion of the prompt
        content_marker = "content: "
        content = ""
        if content_marker in prompt_lower:
            start_idx = prompt_lower.find(content_marker) + len(content_marker)
            summary_marker = "\n\nsummary:"
            end_idx = prompt_lower.find(summary_marker)
            if end_idx != -1 and end_idx > start_idx:
                content = prompt[start_idx:end_idx].strip()
            else:
                content = prompt[start_idx:].strip()
        else:
            # Grab last portion of prompt as raw text if possible
            content = prompt.split("\n")[-1].strip()

        # Clean content and extract key snippets
        clean_content = content.replace("{", "").replace("}", "").replace("'", "").replace('"', '').strip()
        # Truncate content to form a basic readable summary sentence
        snippet = clean_content[:80]
        if len(clean_content) > 80:
            snippet += "..."
        return f"Offline Heuristic Summary: Event received from payload containing [{snippet}]."

    return "Offline degradation: Unable to execute AI model reasoning."
