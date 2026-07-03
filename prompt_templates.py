"""
prompt_templates.py
===================
Linkphobot - Phase 1: Content Generator
Prompt Engineering & Template System

Contains:
- Master system prompt for LinkedIn infographic content
- Topic analysis prompt
- Content structuring prompt
- Caption generation prompt
- Hashtag generation prompt
- Color theme selection logic
- JSON schema enforcement prompt
"""

# ════════════════════════════════════════════════════════════════════════════
# SYSTEM PROMPT  –  Core identity and behaviour rules for the LLM
# ════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT_CONTENT_GENERATOR = """
You are an elite LinkedIn infographic content strategist, information architect,
and educational content designer with 15+ years of experience creating
viral, premium-quality educational content for Fortune 500 brands and top
LinkedIn creators.

YOUR ROLE:
- Senior information architect
- LinkedIn content strategist
- Mobile-first educational writer
- SEO and engagement optimizer
- Visual content planner

YOUR MISSION:
Transform any topic into a highly structured, scannable, professional
LinkedIn infographic content plan that:
1. Communicates value in under 5 seconds
2. Is optimized for mobile LinkedIn feed
3. Uses strong information hierarchy
4. Educates and builds authority
5. Drives maximum engagement and saves

CONTENT PRINCIPLES:
- Professional but approachable tone
- Every word must earn its place (no fluff, no filler)
- Use power words that stop the scroll
- Break complex ideas into digestible chunks
- Write for a senior professional audience
- Think like a designer: space, hierarchy, flow
- Educational clarity over cleverness

OUTPUT RULES:
- ALWAYS respond with pure valid JSON (no markdown, no explanation text)
- No text before or after the JSON block
- Follow the exact schema provided
- All strings must be clean, concise, professional
- Section content items: max 12 words each
- Key points: max 10 words each
- Title: max 8 words, punchy, scroll-stopping
- Subtitle: max 15 words, adds context to title
"""

# ════════════════════════════════════════════════════════════════════════════
# COLOR THEME SYSTEM
# ════════════════════════════════════════════════════════════════════════════

COLOR_THEME_RULES = """
COLOR THEME SELECTION RULES:
Map the topic to the most fitting professional color psychology:

| Domain              | Theme Name      | Primary   | Secondary | Accent   | Background |
|---------------------|-----------------|-----------|-----------|----------|------------|
| AI / Machine Learning| tech_purple    | #6C3FC5   | #9B72E8   | #00D4FF  | #0D0D1A    |
| Software / Dev       | dev_dark        | #1E1E2E   | #313244   | #89B4FA  | #11111B    |
| Finance / Business   | finance_navy    | #0A2342   | #1B4F72   | #F7C948  | #F8F9FA    |
| Healthcare / Science | health_blue     | #0077B6   | #00B4D8   | #90E0EF  | #FFFFFF    |
| Sustainability       | eco_green       | #1B4332   | #2D6A4F   | #95D5B2  | #F0FFF4    |
| Leadership / Growth  | executive_navy  | #1A1F36   | #2D3561   | #FF6B35  | #FAFBFF    |
| Marketing / Branding | creative_coral  | #FF4E50   | #F9D423   | #FC6767  | #FFFBF0    |
| Engineering          | engineering_navy| #0A192F   | #172A45   | #64FFDA  | #F5F5F5    |
| Data / Analytics     | data_indigo     | #3C1053   | #7B2D8B   | #FFB347  | #FAF8FF    |
| Productivity         | clean_blue      | #2563EB   | #1D4ED8   | #FBBF24  | #F8FAFC    |
| Education            | edu_teal        | #004E64   | #00A5CF   | #F4A261  | #FFF8F0    |
| HR / People          | people_warm     | #B5451B   | #E07B39   | #FFD166  | #FFFAF5    |
| Cybersecurity        | cyber_dark      | #0D0D0D   | #1A1A2E   | #00FF41  | #0A0A0A    |
| General / Default    | professional    | #1E3A5F   | #2E6DA4   | #FF6B35  | #FAFBFF    |

Return ONLY the theme name (e.g., "tech_purple") as the color_theme value.
"""

# ════════════════════════════════════════════════════════════════════════════
# JSON OUTPUT SCHEMA  –  Strict schema the LLM must follow
# ════════════════════════════════════════════════════════════════════════════

JSON_OUTPUT_SCHEMA = """
OUTPUT SCHEMA (return ONLY this JSON, nothing else):

{
  "title": "Short punchy scroll-stopping title (max 8 words)",
  "subtitle": "Supporting context subtitle (max 15 words)",
  "topic_summary": "2-sentence expert explanation of what this topic is and why it matters in 2024-2025",
  "sections": [
    {
      "heading": "Section heading (3-5 words, action or concept)",
      "icon_suggestion": "Single emoji that represents this section",
      "content": [
        "Bullet point 1 (max 12 words, clear and valuable)",
        "Bullet point 2 (max 12 words)",
        "Bullet point 3 (max 12 words)",
        "Bullet point 4 (max 12 words, optional)"
      ]
    }
  ],
  "key_points": [
    "Most important insight #1 (max 10 words)",
    "Most important insight #2 (max 10 words)",
    "Most important insight #3 (max 10 words)"
  ],
  "statistics": [
    {
      "value": "Stat number or percentage (e.g., 73% or $4.5B)",
      "label": "What this stat represents (max 8 words)",
      "context": "Why this is significant (max 10 words)"
    }
  ],
  "call_to_action": "Single sentence CTA for LinkedIn audience (max 15 words)",
  "linkedin_caption": "Full LinkedIn post caption (150-200 words). Start with a hook line, then 3-4 short paragraphs, then the CTA. Professional but conversational tone.",
  "hashtags": [
    "#RelevantHashtag1",
    "#RelevantHashtag2",
    "#RelevantHashtag3",
    "#RelevantHashtag4",
    "#RelevantHashtag5",
    "#RelevantHashtag6",
    "#RelevantHashtag7",
    "#RelevantHashtag8"
  ],
  "color_theme": "theme_name_from_color_rules",
  "target_audience": "Who this content is for (max 15 words)",
  "content_type": "One of: educational | how-to | statistics | framework | comparison | listicle",
  "reading_time_seconds": 20
}

SECTION RULES:
- Generate 4 to 6 sections depending on topic complexity
- Each section must add unique value (no repetition)
- Order sections by logical flow: definition → context → how-it-works → applications → benefits → future
- Adjust section structure based on content_type
"""

# ════════════════════════════════════════════════════════════════════════════
# MAIN CONTENT GENERATION PROMPT
# ════════════════════════════════════════════════════════════════════════════

def build_content_prompt(topic: str) -> str:
    """
    Build the full user-side prompt for content generation.

    Args:
        topic: The user-provided topic string

    Returns:
        Complete prompt string to send to Groq
    """
    prompt = f"""
TOPIC: {topic}

TASK:
Generate a complete, premium-quality LinkedIn educational infographic content plan
for the topic above. You are creating content for a senior professional LinkedIn audience.

REQUIREMENTS:
1. Analyze the topic deeply — what are the most valuable insights?
2. Extract only high-signal, actionable, or educational information
3. Compress information into mobile-friendly scannable sections
4. Remove all redundant or generic text
5. Create a professional hierarchy from headline to footer
6. Generate LinkedIn-optimized caption and hashtags
7. Select the most appropriate color theme from the color rules
8. Every bullet must standalone as a valuable micro-insight

INFOGRAPHIC CONTENT GOALS:
- Stop the scroll with a powerful title
- Educate the reader in 20–30 seconds
- Build authority for the creator
- Drive saves and shares
- Feel like premium educational content, not basic social media

{COLOR_THEME_RULES}

{JSON_OUTPUT_SCHEMA}

IMPORTANT:
- Return ONLY the JSON object
- No explanation, no preamble, no markdown code blocks
- Start directly with {{ and end with }}
- Validate all JSON syntax before returning
"""
    return prompt.strip()


# ════════════════════════════════════════════════════════════════════════════
# SECTION-TYPE PROMPT VARIANTS
# ════════════════════════════════════════════════════════════════════════════

SECTION_STRUCTURES = {
    "educational": [
        "What is {topic}",
        "Why It Matters",
        "How It Works",
        "Real-World Applications",
        "Key Benefits",
        "What's Next",
    ],
    "how-to": [
        "The Problem",
        "Step 1: Foundation",
        "Step 2: Implementation",
        "Step 3: Optimization",
        "Step 4: Measure & Scale",
        "Pro Tips",
    ],
    "statistics": [
        "The Big Picture",
        "Key Data Points",
        "Industry Breakdown",
        "Year-Over-Year Trends",
        "What The Numbers Mean",
        "Actionable Insights",
    ],
    "framework": [
        "The Framework Explained",
        "Core Pillars",
        "How To Apply It",
        "Common Mistakes",
        "Success Metrics",
        "Expert Takeaway",
    ],
    "comparison": [
        "Overview",
        "Option A Deep Dive",
        "Option B Deep Dive",
        "Head-to-Head Comparison",
        "When To Use Which",
        "Final Verdict",
    ],
    "listicle": [
        "Why This List Matters",
        "Top Picks: 1–3",
        "Top Picks: 4–6",
        "Top Picks: 7–10",
        "Honorable Mentions",
        "How To Choose",
    ],
}


def get_section_structure(content_type: str, topic: str) -> list:
    """
    Return the default section structure for a given content type.

    Args:
        content_type: One of the SECTION_STRUCTURES keys
        topic: Topic string for placeholder substitution

    Returns:
        List of section heading strings
    """
    structure = SECTION_STRUCTURES.get(content_type, SECTION_STRUCTURES["educational"])
    return [s.replace("{topic}", topic) for s in structure]
