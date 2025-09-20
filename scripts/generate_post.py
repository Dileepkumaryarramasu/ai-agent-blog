# scripts/generate_post.py
# Simple script: creates a Markdown post using either OpenAI or Hugging Face
# Designed for beginners. Writes to posts/ directory.

import os, datetime, textwrap
from pathlib import Path

USE_OPENAI = os.getenv("USE_OPENAI", "true").lower() in ("1", "true", "yes")

def gen_with_openai(prompt):
    import openai
    openai.api_key = os.environ.get("OPENAI_API_KEY")
    if not openai.api_key:
        raise RuntimeError("OPENAI_API_KEY not set")
    res = openai.ChatCompletion.create(
        model="gpt-4o-mini" if "gpt-4o-mini" in openai.Model.list().data else "gpt-4o",
        messages=[{"role":"user","content":prompt}],
        temperature=0.7,
        max_tokens=800
    )
    return res.choices[0].message.content.strip()

def gen_with_hf(prompt):
    # Requires HF_INFERENCE_API_TOKEN secret (free tier available at huggingface.co)
    import requests, json
    token = os.environ.get("HF_INFERENCE_API_TOKEN")
    if not token:
        raise RuntimeError("HF_INFERENCE_API_TOKEN not set")
    api_url = "https://api-inference.huggingface.co/models/gpt2"  # fallback small model
    # You can replace the model path with a better free model if available
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"inputs": prompt, "options": {"wait_for_model": True}, "parameters": {"max_new_tokens": 400}}
    resp = requests.post(api_url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    # HF returns different structures; try to extract text safely:
    if isinstance(data, dict) and "error" in data:
        raise RuntimeError("HF error: " + data["error"])
    if isinstance(data, list) and "generated_text" in data[0]:
        return data[0]["generated_text"]
    # Otherwise try common fallback:
    if isinstance(data, list) and isinstance(data[0], dict):
        return data[0].get("generated_text", str(data[0]))
    return str(data)

def build_prompt(niche):
    return f"""
You are an assistant that writes a clear, helpful 450-700 word blog post for humans.
Niche: {niche}
Output format:
YAML frontmatter with title and date, then markdown body.
Include an H1 title, short intro, 3 subheadings (H2), one short conclusion, and one simple call-to-action line at the end that links to https://example.com/affiliate (placeholder).
Be concise, avoid made-up facts, and keep it practical.
"""

def save_markdown(title, content, out_dir="posts"):
    date = datetime.date.today().isoformat()
    safe = "".join(c if c.isalnum() else "-" for c in title.lower())[:60].strip("-")
    filename = f"{date}-{safe}.md"
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    path = Path(out_dir) / filename
    with path.open("w", encoding="utf-8") as f:
        f.write(content)
    return path

def parse_title_from_output(text):
    # naive: title is first line if it starts with '#'
    for line in text.splitlines():
        if line.strip().startswith("#"):
            return line.strip().lstrip("# ").strip()
    # fallback
    return "Auto Generated Post"

def main():
    niche = os.getenv("NICHE", "budget camping gear for beginners")
    prompt = build_prompt(niche)
    print("Generating post for niche:", niche)
    if USE_OPENAI:
        out = gen_with_openai(prompt)
    else:
        out = gen_with_hf(prompt)
    # ensure frontmatter exists; if not, add minimal frontmatter
    title = parse_title_from_output(out)
    if not out.lstrip().startswith("---"):
        front = f"---\ntitle: \"{title}\"\ndate: {datetime.date.today().isoformat()}\n---\n\n"
        out = front + out
    path = save_markdown(title, out, out_dir="posts")
    print("Saved:", path)

if __name__ == "__main__":
    main()
