"""
linkedin_prompt_templates.py
============================
Linkphobot - Phase 6: LinkedIn Caption Generator
Prompt Engineering Templates

Contains:
- System prompt for LinkedIn caption generation
- Caption style templates (educational, story, listicle, data-driven, thought-leadership)
- Hook templates by content type
- CTA templates by goal
- Hashtag prompt templates
- SEO keyword extraction prompt
"""

# ════════════════════════════════════════════════════════════════════════════
# SYSTEM PROMPT
# ════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT_CAPTION = """
You are an elite LinkedIn content strategist and ghostwriter who has helped
Fortune 500 executives and top creators grow multi-million follower audiences.

Your specialty: writing LinkedIn captions that:
- Stop the scroll in the first 2 lines
- Build authority and trust instantly
- Educate without overwhelming
- Drive saves, comments, and shares
- Sound human, not AI-generated
- Work perfectly on mobile (short paragraphs, white space)

VOICE: Professional but warm. Expert but approachable. Confident but not arrogant.

FORMATTING RULES (always follow):
- First line: HOOK - bold claim, provocative question, or surprising stat
- Short paragraphs: max 2-3 sentences each
- Empty line between every paragraph
- No walls of text
- End with a clear CTA
- Hashtags on final line only
- Total length: 150-220 words (not counting hashtags)

NEVER:
- Use "I am excited to share"
- Use "In today's fast-paced world"
- Use "It is no secret that"
- Use "Leverage" as a verb
- Use "Game-changer" or "Revolutionize"
- Start with "As a [title]"
- Write more than 220 words

ALWAYS return ONLY valid JSON. No markdown. No explanation. No preamble.
"""

# ════════════════════════════════════════════════════════════════════════════
# CAPTION STYLE TEMPLATES
# ════════════════════════════════════════════════════════════════════════════

CAPTION_STYLES = {

    "educational": {
        "name":        "Educational Authority",
        "description": "Teach one concept deeply. Build credibility through expertise.",
        "structure":   ["hook_stat_or_claim", "problem_context", "key_insight_1", "key_insight_2", "key_insight_3", "takeaway", "cta"],
        "tone":        "Expert teacher sharing hard-won knowledge",
        "best_for":    ["how-to", "educational", "framework"],
    },

    "story": {
        "name":        "Story Arc",
        "description": "Narrative journey from problem to solution. Emotionally engaging.",
        "structure":   ["hook_question", "scene_setting", "conflict", "turning_point", "resolution", "lesson", "cta"],
        "tone":        "Storyteller drawing from real-world experience",
        "best_for":    ["case_study", "comparison", "educational"],
    },

    "listicle": {
        "name":        "Power List",
        "description": "Numbered insights. High skimmability. Max engagement.",
        "structure":   ["hook_number", "context_why", "list_items", "bonus_insight", "cta"],
        "tone":        "Direct, punchy, high-value",
        "best_for":    ["listicle", "how-to", "statistics"],
    },

    "data_driven": {
        "name":        "Data-Led Insight",
        "description": "Lead with a statistic. Build argument from evidence.",
        "structure":   ["hook_stat", "stat_context", "what_it_means", "implications", "action", "cta"],
        "tone":        "Analytical authority who translates numbers into meaning",
        "best_for":    ["statistics", "framework", "educational"],
    },

    "thought_leadership": {
        "name":        "Thought Leadership",
        "description": "Contrarian or forward-looking take. Position as industry voice.",
        "structure":   ["hook_contrarian", "conventional_wisdom", "why_wrong", "new_perspective", "evidence", "future_outlook", "cta"],
        "tone":        "Confident industry thinker who challenges assumptions",
        "best_for":    ["comparison", "framework", "educational"],
    },
}

# ════════════════════════════════════════════════════════════════════════════
# HOOK TEMPLATES
# ════════════════════════════════════════════════════════════════════════════

HOOK_TEMPLATES = {
    "stat": [
        "{stat_value} of {audience} still don't understand {topic}.",
        "{stat_value}. That is what {topic} is worth by {year}.",
        "Only {stat_value} of professionals know how to use {topic} correctly.",
        "The {topic} market will reach {stat_value} by {year}. Are you positioned for it?",
    ],
    "question": [
        "Why do most people get {topic} completely wrong?",
        "What separates the top 1% who understand {topic} from everyone else?",
        "If {topic} is so important, why does nobody teach it properly?",
        "Are you making these {topic} mistakes?",
    ],
    "contrarian": [
        "Everyone is talking about {topic}. Almost everyone is missing the point.",
        "The {topic} advice you keep hearing is costing you results.",
        "{topic} is not what you think it is.",
        "Stop approaching {topic} the wrong way.",
    ],
    "bold_claim": [
        "{topic} will be the most important skill of the next decade.",
        "The professionals who master {topic} now will lead their industries in 5 years.",
        "Understanding {topic} is no longer optional.",
        "{topic} changes everything. Here is what you need to know.",
    ],
    "number": [
        "{number} things every professional needs to know about {topic}:",
        "I studied {topic} for {time_period}. Here are {number} things that actually matter:",
        "{number} {topic} insights that took me years to learn:",
        "The {number} most important {topic} concepts, explained simply:",
    ],
}

# ════════════════════════════════════════════════════════════════════════════
# CTA TEMPLATES
# ════════════════════════════════════════════════════════════════════════════

CTA_TEMPLATES = {
    "save": [
        "Save this post — you will want to refer back to it.",
        "Bookmark this before you scroll. It will save you time later.",
        "Save this for your next strategy session.",
        "This took hours to research. Save it so you don't have to.",
    ],
    "comment": [
        "What is your biggest question about {topic}? Drop it below.",
        "Which of these surprised you most? Tell me in the comments.",
        "What would you add? Share your experience below.",
        "Agree or disagree? Tell me why in the comments.",
    ],
    "share": [
        "Share this with someone who needs to understand {topic}.",
        "Tag a colleague who should see this.",
        "Repost if this changed how you think about {topic}.",
        "Share this with your team — this affects all of us.",
    ],
    "follow": [
        "Follow for more {topic} insights every week.",
        "Follow for weekly breakdowns like this one.",
        "I post about {topic} every week. Follow so you don't miss it.",
        "More content like this coming. Follow to stay ahead.",
    ],
    "engage": [
        "Save this. Share it. Start applying it today.",
        "Which insight will you act on first? Let me know below.",
        "What is holding you back from mastering {topic}? Comment below.",
        "Save this, share it with someone it will help, and follow for more.",
    ],
}

# ════════════════════════════════════════════════════════════════════════════
# MAIN CAPTION GENERATION PROMPT BUILDER
# ════════════════════════════════════════════════════════════════════════════

def build_caption_prompt(content: dict, style: str = "educational") -> str:
    """
    Build the full caption generation prompt from Phase 1 content.

    Args:
        content: Phase 1 content dict
        style:   caption style key from CAPTION_STYLES

    Returns:
        Complete prompt string to send to Groq
    """
    title        = content.get("title", "")
    subtitle     = content.get("subtitle", "")
    topic        = content.get("topic", title)
    sections     = content.get("sections", [])
    key_points   = content.get("key_points", [])
    statistics   = content.get("statistics", [])
    content_type = content.get("content_type", "educational")
    audience     = content.get("target_audience", "professionals")

    style_def    = CAPTION_STYLES.get(style, CAPTION_STYLES["educational"])

    # Build sections summary
    sections_text = ""
    for i, sec in enumerate(sections[:5], 1):
        heading = sec.get("heading", "")
        bullets = sec.get("content", [])[:3]
        sections_text += f"\n  Section {i}: {heading}\n"
        for b in bullets:
            sections_text += f"    - {b}\n"

    # Build key points text
    kp_text = "\n".join(f"  - {kp}" for kp in key_points[:5])

    # Build stats text
    stats_text = ""
    for stat in statistics[:3]:
        stats_text += f"  - {stat.get('value','')} : {stat.get('label','')}\n"

    prompt = f"""
TOPIC: {topic}
TITLE: {title}
SUBTITLE: {subtitle}
AUDIENCE: {audience}
CONTENT TYPE: {content_type}
CAPTION STYLE: {style_def['name']} - {style_def['description']}

CONTENT SUMMARY:
{sections_text}

KEY POINTS:
{kp_text if kp_text else "  Not provided"}

STATISTICS:
{stats_text if stats_text else "  Not provided"}

TASK:
Generate a complete LinkedIn caption package using the {style_def['name']} style.
The caption must feel like it was written by a senior human professional — not AI.

OUTPUT SCHEMA (return ONLY this JSON, nothing else):
{{
  "hook": "First 1-2 lines that stop the scroll. Max 20 words. No period at end optional.",
  "caption_body": "Full caption body (without hook and without hashtags). 120-180 words. Mobile-formatted with empty lines between paragraphs.",
  "full_caption": "Complete caption = hook + empty line + body + empty line + cta_line. Ready to copy-paste.",
  "cta_line": "Single call-to-action line. Max 15 words.",
  "hook_type": "One of: stat | question | contrarian | bold_claim | number",
  "word_count": 0,
  "readability_score": "easy | medium | professional",
  "emotional_triggers": ["list", "of", "emotions", "this", "triggers"],
  "best_posting_time": "Morning (7-9am) | Midday (12-1pm) | Evening (5-7pm)",
  "content_format_tip": "One tip for how to present this content visually alongside the caption"
}}

RULES:
- hook must be the first sentence of full_caption
- full_caption must be complete and ready to post
- No AI cliches (no 'game-changer', 'leverage', 'excited to share')
- Mobile-friendly: short paragraphs, line breaks
- Return ONLY the JSON object. Start with {{ end with }}
"""
    return prompt.strip()


# ════════════════════════════════════════════════════════════════════════════
# HASHTAG GENERATION PROMPT
# ════════════════════════════════════════════════════════════════════════════

def build_hashtag_prompt(topic: str,
                          content_type: str,
                          key_points: list,
                          existing_hashtags: list = None) -> str:
    """Build the hashtag generation prompt."""
    kp_text = "\n".join(f"  - {kp}" for kp in key_points[:5])
    existing = ", ".join(existing_hashtags[:5]) if existing_hashtags else "None"

    return f"""
TOPIC: {topic}
CONTENT TYPE: {content_type}
KEY POINTS:
{kp_text}
EXISTING HASHTAGS: {existing}

Generate an optimised LinkedIn hashtag set for this content.

LinkedIn hashtag strategy:
- Mix of broad (100k+ posts) and niche (1k-50k posts) tags
- Max 8 hashtags (LinkedIn algorithm penalises more)
- Include: 2 broad industry tags, 3 topic-specific tags, 2 skill/role tags, 1 trending tag
- No spaces in hashtags
- CamelCase for multi-word tags

OUTPUT SCHEMA (return ONLY this JSON):
{{
  "primary_hashtags": ["#Tag1", "#Tag2", "#Tag3"],
  "secondary_hashtags": ["#Tag4", "#Tag5", "#Tag6"],
  "niche_hashtags": ["#Tag7", "#Tag8"],
  "full_set": ["#Tag1", "#Tag2", "#Tag3", "#Tag4", "#Tag5", "#Tag6", "#Tag7", "#Tag8"],
  "hashtag_string": "#Tag1 #Tag2 #Tag3 #Tag4 #Tag5 #Tag6 #Tag7 #Tag8",
  "reach_estimate": "broad | medium | niche",
  "strategy_note": "One sentence explaining the hashtag strategy for this post"
}}

Return ONLY the JSON. Start with {{ end with }}
""".strip()


# ════════════════════════════════════════════════════════════════════════════
# SEO KEYWORD EXTRACTION PROMPT
# ════════════════════════════════════════════════════════════════════════════

def build_seo_prompt(topic: str, content: dict) -> str:
    """Build the SEO keyword extraction and optimisation prompt."""
    sections = content.get("sections", [])
    all_headings = [s.get("heading", "") for s in sections]

    return f"""
TOPIC: {topic}
SECTION HEADINGS: {", ".join(all_headings[:6])}
TARGET AUDIENCE: {content.get("target_audience", "professionals")}

Extract SEO-optimised keywords and phrases for a LinkedIn infographic post.

LinkedIn SEO context:
- LinkedIn search indexes post text and hashtags
- Keyword-rich first 3 lines rank better in search
- Exact-match professional terms outperform generic ones
- Include long-tail phrases that professionals actually search

OUTPUT SCHEMA (return ONLY this JSON):
{{
  "primary_keyword": "The single most important search term (2-4 words)",
  "secondary_keywords": ["keyword 1", "keyword 2", "keyword 3", "keyword 4"],
  "long_tail_phrases": ["3-5 word phrase 1", "3-5 word phrase 2", "3-5 word phrase 3"],
  "lsi_keywords": ["related term 1", "related term 2", "related term 3"],
  "keyword_density_tip": "How to naturally include keywords without keyword stuffing",
  "search_intent": "informational | navigational | commercial | transactional",
  "competitor_gaps": ["topic gap 1", "topic gap 2"]
}}

Return ONLY the JSON. Start with {{ end with }}
""".strip()
