"""AI tagging utility specialized for fishing content taxonomy.
Uses OpenAI to generate tags, a cleaned title, and a short summary.
Set OPENAI_API_KEY as an environment variable before running.
"""
import os
import json
import openai

OPENAI_KEY = os.getenv('OPENAI_API_KEY')
if OPENAI_KEY:
    openai.api_key = OPENAI_KEY

MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')

# Domain-specific taxonomy for fishing-related tags
FISHING_TAGS = [
    "carp", "match fishing", "float fishing", "ledgering", "feeder", "bait", "groundbait",
    "rig", "zig rig", "hair rig", "hookbait", "boilie", "method feeder", "venue", "river",
    "lake", "specimen", "coarse", "tackle", "rod setup", "reel", "line", "knot"
]

def tag_video(caption_or_url):
    """Return (tags_list, title, summary)"""
    if not OPENAI_KEY:
        # fallback heuristic tagging: find keywords in URL/caption
        tags = [t for t in FISHING_TAGS if t in (caption_or_url or '').lower()][:6]
        return (tags, 'untitled', '')

    prompt = (
        "You are a metadata assistant specialized in fishing video content.\n"
        "Given a TikTok video URL or caption, produce a JSON object with fields:\n"
        "- tags: up to 8 short tags chosen from common fishing taxonomy (e.g. carp, boilie, rig, method feeder),\n"
        "- title: a concise cleaned title (max 60 chars) suitable for a video file name,\n"
        "- summary: a 1-sentence summary of the video's core content.\n"
        "Prefer tags from this list when relevant: " + ', '.join(FISHING_TAGS) + "\n"
        f"Respond only with valid JSON. Input: {caption_or_url}"
    )

    try:
        resp = openai.ChatCompletion.create(
            model=MODEL,
            messages=[{'role':'user','content':prompt}],
            max_tokens=200,
            temperature=0.2
        )
        text = resp['choices'][0]['message']['content']
        parsed = json.loads(text)
        tags = parsed.get('tags', [])
        title = parsed.get('title', 'untitled')
        summary = parsed.get('summary', '')
        return (tags, title, summary)
    except Exception as e:
        print('OpenAI error:', e)
        return ([], 'untitled', '')
