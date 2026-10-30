import sys
from config import GEMINI_API_KEY, GROQ_API_KEY, GROQ_MODEL
from agent.prompt_builder import SYSTEM_PROMPT

# Active models on Groq
GROQ_MODELS = [
    GROQ_MODEL,
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3.8-27b",
]

def generate_llm_synthesis(prompt: str) -> str:
    """
    Synthesize advisory using Gemini or Groq, with an explicit 8s timeout.
    Returns empty string on failure or timeout so the caller safely uses
    the deterministic, verified advisory.
    """
    if GEMINI_API_KEY:
        try:
            import google.generativeai as genai
            genai.configure(api_key=GEMINI_API_KEY)
            model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                system_instruction=SYSTEM_PROMPT,
                generation_config={"temperature": 0.1}
            )
            resp = model.generate_content(prompt, request_options={"timeout": 8.0})
            if resp and resp.text:
                return resp.text.strip()
        except Exception as e:
            sys.stderr.write(f"[WARN] Gemini call failed ({e}), checking Groq...\n")

    if GROQ_API_KEY:
        try:
            from groq import Groq
            # Explicit 8-second timeout protects against hanging in hackathon judging
            client = Groq(api_key=GROQ_API_KEY, timeout=8.0)
            seen_models = set()
            for model_name in GROQ_MODELS:
                if not model_name or model_name in seen_models:
                    continue
                seen_models.add(model_name)
                try:
                    completion = client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.1,
                        max_tokens=600
                    )
                    choice = completion.choices[0]
                    text = choice.message.content
                    if not text and hasattr(choice.message, 'reasoning') and choice.message.reasoning:
                        # Some reasoning models put output in reasoning if max_tokens is small
                        text = choice.message.reasoning
                    if text and len(text.strip()) > 0:
                        return text.strip()
                except Exception as model_err:
                    sys.stderr.write(f"[WARN] Groq model '{model_name}' failed: {model_err}\n")
                    continue
        except Exception as e:
            sys.stderr.write(f"[WARN] Groq client initialization skipped ({e}).\n")

    return ""
