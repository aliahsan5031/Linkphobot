"""
hashtag_engine.py
=================
Linkphobot - Phase 6: LinkedIn Caption Generator
Hashtag Intelligence Engine

Features:
- Topic-to-hashtag mapping database
- Reach-tier classification (broad/medium/niche)
- Industry-specific hashtag sets
- Dynamic hashtag scoring
- Hashtag deduplication and ranking
- AI-powered hashtag generation via Groq
- Fallback hashtag library (no-API mode)
"""

import re
import sys
import os
import json
from typing import List, Dict, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# ════════════════════════════════════════════════════════════════════════════
# HASHTAG DATABASE  –  curated by topic domain
# ════════════════════════════════════════════════════════════════════════════

HASHTAG_DB = {
    # ── AI / Machine Learning ─────────────────────────────────────────
    "ai": {
        "broad":   ["#ArtificialIntelligence", "#AI", "#MachineLearning", "#Technology"],
        "medium":  ["#AIStrategy", "#DeepLearning", "#MLOps", "#AIInnovation"],
        "niche":   ["#GenerativeAI", "#LLM", "#PromptEngineering", "#AIEthics"],
    },
    "machine learning": {
        "broad":   ["#MachineLearning", "#AI", "#DataScience", "#Technology"],
        "medium":  ["#MLOps", "#DeepLearning", "#NeuralNetworks", "#AIResearch"],
        "niche":   ["#ReinforcementLearning", "#ComputerVision", "#NLP", "#ModelDeployment"],
    },
    # ── Healthcare ────────────────────────────────────────────────────
    "healthcare": {
        "broad":   ["#Healthcare", "#HealthTech", "#MedicalInnovation", "#DigitalHealth"],
        "medium":  ["#HealthcareAI", "#MedTech", "#PatientCare", "#ClinicalInnovation"],
        "niche":   ["#HealthcareTransformation", "#MedicalAI", "#HealthData", "#Telemedicine"],
    },
    # ── Finance / Business ────────────────────────────────────────────
    "finance": {
        "broad":   ["#Finance", "#Business", "#Investment", "#Economy"],
        "medium":  ["#FinTech", "#WealthManagement", "#FinancialStrategy", "#CFO"],
        "niche":   ["#FinancialModeling", "#PrivateEquity", "#VentureCapital", "#FinanceLeaders"],
    },
    "business": {
        "broad":   ["#Business", "#Entrepreneurship", "#Leadership", "#Strategy"],
        "medium":  ["#BusinessStrategy", "#StartupLife", "#B2B", "#BusinessGrowth"],
        "niche":   ["#ScaleUp", "#BusinessTransformation", "#ExecutiveLeadership", "#GTM"],
    },
    # ── Leadership ────────────────────────────────────────────────────
    "leadership": {
        "broad":   ["#Leadership", "#Management", "#PersonalDevelopment", "#ProfessionalGrowth"],
        "medium":  ["#ExecutiveLeadership", "#TeamManagement", "#LeadershipDevelopment", "#CEO"],
        "niche":   ["#ThoughtLeadership", "#LeadershipCoaching", "#HighPerformance", "#LeadershipMindset"],
    },
    # ── Marketing ─────────────────────────────────────────────────────
    "marketing": {
        "broad":   ["#Marketing", "#DigitalMarketing", "#ContentMarketing", "#Growth"],
        "medium":  ["#MarketingStrategy", "#SEO", "#SocialMediaMarketing", "#BrandBuilding"],
        "niche":   ["#DemandGeneration", "#GrowthHacking", "#ConversionOptimization", "#MarTech"],
    },
    # ── Software / Engineering ────────────────────────────────────────
    "software": {
        "broad":   ["#SoftwareDevelopment", "#Technology", "#Coding", "#Tech"],
        "medium":  ["#SoftwareEngineering", "#DevOps", "#CloudComputing", "#API"],
        "niche":   ["#SystemDesign", "#BackendDevelopment", "#Microservices", "#PlatformEngineering"],
    },
    # ── Data ──────────────────────────────────────────────────────────
    "data": {
        "broad":   ["#DataScience", "#BigData", "#Analytics", "#DataDriven"],
        "medium":  ["#DataEngineering", "#BusinessIntelligence", "#DataStrategy", "#SQL"],
        "niche":   ["#DataPipeline", "#DataGovernance", "#DataMesh", "#RealTimeAnalytics"],
    },
    # ── Productivity ──────────────────────────────────────────────────
    "productivity": {
        "broad":   ["#Productivity", "#PersonalDevelopment", "#WorkSmarter", "#Efficiency"],
        "medium":  ["#TimeManagement", "#Focus", "#WorkLifeBalance", "#HabitsOfSuccess"],
        "niche":   ["#DeepWork", "#GettingThingsDone", "#SystemsThinking", "#MindfulProductivity"],
    },
    # ── Cybersecurity ─────────────────────────────────────────────────
    "cybersecurity": {
        "broad":   ["#Cybersecurity", "#InfoSec", "#Security", "#Privacy"],
        "medium":  ["#ZeroTrust", "#ThreatIntelligence", "#SecurityOps", "#CISO"],
        "niche":   ["#PenTesting", "#CyberResilience", "#IncidentResponse", "#SecurityAutomation"],
    },
    # ── Sustainability ────────────────────────────────────────────────
    "sustainability": {
        "broad":   ["#Sustainability", "#ESG", "#ClimateChange", "#GreenTech"],
        "medium":  ["#NetZero", "#CircularEconomy", "#SustainableBusiness", "#ClimateAction"],
        "niche":   ["#CarbonFootprint", "#SustainableInvesting", "#GreenInnovation", "#ClimateLeadership"],
    },
    # ── General Professional ──────────────────────────────────────────
    "general": {
        "broad":   ["#LinkedIn", "#ProfessionalDevelopment", "#Learning", "#Innovation"],
        "medium":  ["#CareerGrowth", "#SkillsDevelopment", "#WorkplaceCulture", "#FutureOfWork"],
        "niche":   ["#ProfessionalTips", "#CareerAdvice", "#LinkedInLearning", "#LifelongLearning"],
    },
}

# ── Industry role hashtags ────────────────────────────────────────────────
ROLE_HASHTAGS = {
    "executive":    ["#CEO", "#CTO", "#CFO", "#CISO", "#CMO", "#ExecutiveLeadership"],
    "developer":    ["#Developer", "#SoftwareEngineer", "#Programmer", "#DevLife"],
    "analyst":      ["#DataAnalyst", "#BusinessAnalyst", "#FinancialAnalyst", "#Analyst"],
    "marketer":     ["#Marketer", "#DigitalMarketer", "#GrowthMarketer", "#ContentCreator"],
    "hr":           ["#HRProfessional", "#PeopleAndCulture", "#HumanResources", "#TalentManagement"],
    "entrepreneur": ["#Entrepreneur", "#Founder", "#Startup", "#StartupFounder"],
    "consultant":   ["#Consultant", "#Strategy", "#Management", "#Advisory"],
}


# ════════════════════════════════════════════════════════════════════════════
# TOPIC MATCHER
# ════════════════════════════════════════════════════════════════════════════

def match_topic_to_db(topic: str) -> str:
    """
    Match a topic string to the closest hashtag database key.

    Returns:
        matched key from HASHTAG_DB
    """
    topic_lower = topic.lower()

    # Direct keyword match
    for key in HASHTAG_DB:
        if key in topic_lower or topic_lower in key:
            return key

    # Partial word match
    topic_words = set(re.findall(r'\b\w+\b', topic_lower))
    best_match  = "general"
    best_score  = 0

    for key in HASHTAG_DB:
        key_words = set(re.findall(r'\b\w+\b', key))
        overlap   = len(topic_words & key_words)
        if overlap > best_score:
            best_score = overlap
            best_match = key

    return best_match


# ════════════════════════════════════════════════════════════════════════════
# HASHTAG GENERATOR  –  rule-based (no API needed)
# ════════════════════════════════════════════════════════════════════════════

def generate_hashtags_rule_based(topic: str,
                                  content_type: str = "educational",
                                  n_hashtags: int = 8) -> dict:
    """
    Generate LinkedIn hashtags using the curated database.
    Works without any API call.

    Args:
        topic        : topic string
        content_type : content type string
        n_hashtags   : total hashtags to return (max 8)

    Returns:
        dict with primary, secondary, niche hashtags + full_set + string
    """
    db_key      = match_topic_to_db(topic)
    tag_pool    = HASHTAG_DB.get(db_key, HASHTAG_DB["general"])
    general     = HASHTAG_DB["general"]

    n_hashtags  = min(8, n_hashtags)

    # Select hashtags by tier
    primary     = tag_pool["broad"][:2]
    secondary   = tag_pool["medium"][:3]
    niche       = tag_pool["niche"][:2]

    # Fill remaining from general pool if needed
    full_set    = primary + secondary + niche
    remaining   = n_hashtags - len(full_set)
    if remaining > 0:
        gen_extra = [t for t in general["medium"] if t not in full_set]
        full_set += gen_extra[:remaining]

    full_set = list(dict.fromkeys(full_set))[:n_hashtags]  # dedupe

    # Add content-type hashtag
    ct_tags = {
        "educational": "#LinkedIn",
        "how-to":      "#HowTo",
        "statistics":  "#DataDriven",
        "framework":   "#BusinessStrategy",
        "comparison":  "#ProfessionalDevelopment",
        "listicle":    "#CareerTips",
    }
    ct_tag = ct_tags.get(content_type, "#LinkedIn")
    if ct_tag not in full_set:
        full_set[-1] = ct_tag

    return {
        "primary_hashtags":   primary,
        "secondary_hashtags": secondary,
        "niche_hashtags":     niche,
        "full_set":           full_set,
        "hashtag_string":     " ".join(full_set),
        "reach_estimate":     "medium",
        "strategy_note":      (f"Mix of broad {db_key} tags and niche audience tags "
                               f"for balanced reach and engagement."),
        "source":             "rule_based",
    }


# ════════════════════════════════════════════════════════════════════════════
# HASHTAG GENERATOR  –  AI-powered via Groq
# ════════════════════════════════════════════════════════════════════════════

def generate_hashtags_ai(topic: str,
                          content_type: str,
                          key_points: list,
                          client=None,
                          model: str = "llama-3.3-70b-versatile") -> dict:
    """
    Generate optimised hashtags using the Groq LLM.

    Args:
        topic        : topic string
        content_type : content type
        key_points   : list of key point strings
        client       : Groq client (or None to create one)
        model        : model identifier

    Returns:
        dict with hashtag data
    """
    from linkedin_prompt_templates import build_hashtag_prompt

    try:
        if client is None:
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "phase1_compat"))
            # Try loading groq_client from parent linkphobot directory
            import importlib.util
            for search_path in [
                os.path.join(os.path.dirname(__file__), ".."),
                "/content/linkphobot",
                "/tmp/linkphobot",
            ]:
                gc_path = os.path.join(search_path, "groq_client.py")
                if os.path.isfile(gc_path):
                    spec = importlib.util.spec_from_file_location("groq_client", gc_path)
                    gc   = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(gc)
                    client = gc.create_groq_client()
                    break

        if client is None:
            raise RuntimeError("Could not create Groq client")

        prompt   = build_hashtag_prompt(topic, content_type, key_points)
        messages = [{"role": "user", "content": prompt}]
        response = client.chat.completions.create(
            model=model, messages=messages,
            temperature=0.5, max_tokens=600
        )
        raw  = response.choices[0].message.content.strip()

        # Clean and parse JSON
        raw = re.sub(r"```(?:json)?\s*", "", raw)
        raw = re.sub(r"```\s*$", "", raw, flags=re.MULTILINE)
        data = json.loads(raw)
        data["source"] = "ai_generated"
        return data

    except Exception as e:
        # Fallback to rule-based
        result = generate_hashtags_rule_based(topic, content_type)
        result["fallback_reason"] = str(e)
        return result


# ════════════════════════════════════════════════════════════════════════════
# HASHTAG SCORER
# ════════════════════════════════════════════════════════════════════════════

def score_hashtag_set(hashtags: List[str]) -> dict:
    """
    Score a hashtag set for LinkedIn effectiveness.

    Returns:
        dict with scores and recommendations
    """
    n = len(hashtags)
    issues = []
    score  = 100

    if n > 8:
        score -= 20
        issues.append(f"Too many hashtags ({n}). LinkedIn penalises 9+. Use max 8.")
    if n < 3:
        score -= 15
        issues.append(f"Too few hashtags ({n}). Use 5-8 for best reach.")

    # Check for spaces
    spaced = [h for h in hashtags if " " in h]
    if spaced:
        score -= 10
        issues.append(f"Hashtags with spaces won't work: {spaced}")

    # Check for # prefix
    no_hash = [h for h in hashtags if not h.startswith("#")]
    if no_hash:
        score -= 5
        issues.append(f"Missing # prefix: {no_hash}")

    # Check for very long hashtags
    long_tags = [h for h in hashtags if len(h) > 25]
    if long_tags:
        score -= 5
        issues.append(f"Very long hashtags may reduce readability: {long_tags}")

    return {
        "score":           max(0, score),
        "n_hashtags":      n,
        "issues":          issues,
        "recommendation":  "Good hashtag set" if score >= 80 else "Needs improvement",
    }


# ════════════════════════════════════════════════════════════════════════════
# HASHTAG FORMATTER
# ════════════════════════════════════════════════════════════════════════════

def format_hashtags_for_linkedin(hashtags: List[str],
                                  per_line: int = 4) -> str:
    """
    Format hashtags into LinkedIn-ready string.
    Groups them for mobile readability.
    """
    clean = []
    for h in hashtags:
        h = h.strip()
        if not h.startswith("#"):
            h = "#" + h
        h = h.replace(" ", "")
        clean.append(h)

    # Group into lines
    lines = []
    for i in range(0, len(clean), per_line):
        lines.append(" ".join(clean[i:i+per_line]))

    return "\n".join(lines)


def clean_hashtag(tag: str) -> str:
    """Normalise a single hashtag string."""
    tag = tag.strip()
    if not tag.startswith("#"):
        tag = "#" + tag
    tag = re.sub(r"\s+", "", tag)
    tag = re.sub(r"[^\w#]", "", tag)
    return tag
