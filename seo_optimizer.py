"""
seo_optimizer.py
================
Linkphobot - Phase 6: LinkedIn Caption Generator
SEO Optimization Engine
"""

import re
import sys
import os
import json
from typing import List, Dict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

STOP_WORDS = {
    "a","an","the","and","or","but","in","on","at","to","for","of","with",
    "by","from","as","is","was","are","were","be","been","being","have",
    "has","had","do","does","did","will","would","could","should","may",
    "might","shall","can","not","this","that","these","those","it","its"
}

POWER_WORDS = {
    "proven","essential","critical","ultimate","complete","comprehensive",
    "actionable","practical","effective","strategic","advanced","expert",
    "professional","optimized","data-driven","evidence-based","results",
    "framework","system","method","approach","strategy","insight","guide"
}

ENGAGEMENT_WORDS = {
    "you","your","we","our","how","why","what","which","who","when",
    "discover","learn","understand","master","unlock","transform","achieve"
}


def extract_keywords(text: str, top_n: int = 10) -> List[str]:
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    freq  = {}
    for w in words:
        if w not in STOP_WORDS:
            freq[w] = freq.get(w, 0) + 1
    sorted_words = sorted(freq.items(), key=lambda x: -x[1])
    return [w for w, _ in sorted_words[:top_n]]


def score_caption_seo(caption: str, topic: str) -> dict:
    topic_words = set(re.findall(r'\b\w+\b', topic.lower())) - STOP_WORDS
    cap_lower   = caption.lower()
    cap_words   = re.findall(r'\b\w+\b', cap_lower)

    keyword_hits    = sum(1 for w in topic_words if w in cap_lower)
    power_hits      = sum(1 for w in POWER_WORDS if w in cap_lower)
    engagement_hits = sum(1 for w in ENGAGEMENT_WORDS if w in cap_lower)

    word_count = len(cap_words)
    has_numbers= bool(re.search(r'\d', caption))
    has_stats  = bool(re.search(r'\d+%|\$\d|\d+x|\d+\s*(billion|million|trillion)', caption.lower()))
    lines      = caption.split('\n')
    short_paras= sum(1 for l in lines if 0 < len(l.split()) <= 25)

    score = 0
    score += min(30, keyword_hits * 8)
    score += min(20, power_hits  * 5)
    score += min(15, engagement_hits * 3)
    score += 10 if has_numbers else 0
    score += 10 if has_stats   else 0
    score += min(15, short_paras * 3)

    issues = []
    if keyword_hits == 0:
        issues.append("Include topic keywords in first 3 lines for LinkedIn SEO")
    if word_count < 100:
        issues.append(f"Caption too short ({word_count} words). Aim for 150-220.")
    if word_count > 250:
        issues.append(f"Caption too long ({word_count} words). Trim to 220.")
    if not has_numbers:
        issues.append("Add a specific number or stat — improves credibility and reach")
    if short_paras < 3:
        issues.append("Break text into shorter paragraphs for mobile readability")

    return {
        "seo_score":       min(100, score),
        "word_count":      word_count,
        "keyword_hits":    keyword_hits,
        "power_word_hits": power_hits,
        "has_statistics":  has_stats,
        "mobile_friendly": short_paras >= 3,
        "issues":          issues,
        "grade":           "A" if score >= 80 else ("B" if score >= 60 else ("C" if score >= 40 else "D")),
    }


def optimize_caption_text(caption: str, topic: str, keywords: List[str] = None) -> str:
    optimized = caption
    optimized = re.sub(r'[ \t]{2,}', ' ', optimized)
    optimized = re.sub(r'\n{3,}', '\n\n', optimized)
    optimized = optimized.strip()

    cliche_map = {
        r'\bin today\'s fast.paced world\b': f'in {topic}',
        r'\bit is no secret that\b': '',
        r'\bi am excited to share\b': '',
        r'\bgame.changer\b': 'major shift',
        r'\bleverage\b': 'use',
        r'\bsynergy\b': 'collaboration',
        r'\bparadigm shift\b': 'fundamental change',
    }
    for pattern, replacement in cliche_map.items():
        optimized = re.sub(pattern, replacement, optimized, flags=re.IGNORECASE)

    return optimized.strip()


def compute_readability(text: str) -> dict:
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    words     = re.findall(r'\b\w+\b', text)
    syllables = sum(_count_syllables(w) for w in words)

    if not sentences or not words:
        return {"score": 50, "level": "medium", "avg_sentence_length": 0}

    avg_sent_len = len(words) / len(sentences)
    avg_syl_word = syllables / len(words) if words else 1

    flesch = 206.835 - 1.015 * avg_sent_len - 84.6 * avg_syl_word
    flesch = max(0, min(100, flesch))

    if flesch >= 70:   level = "easy"
    elif flesch >= 50: level = "medium"
    else:              level = "professional"

    return {
        "flesch_score":         round(flesch, 1),
        "level":                level,
        "avg_sentence_length":  round(avg_sent_len, 1),
        "word_count":           len(words),
        "sentence_count":       len(sentences),
    }


def _count_syllables(word: str) -> int:
    word    = word.lower().strip(".,!?")
    vowels  = re.findall(r'[aeiouy]+', word)
    count   = len(vowels)
    if word.endswith('e') and count > 1:
        count -= 1
    return max(1, count)


def generate_seo_report(caption: str, topic: str, hashtags: List[str]) -> dict:
    seo      = score_caption_seo(caption, topic)
    readable = compute_readability(caption)
    keywords = extract_keywords(caption + " " + topic, top_n=8)

    return {
        "overall_score":    seo["seo_score"],
        "grade":            seo["grade"],
        "seo_analysis":     seo,
        "readability":      readable,
        "top_keywords":     keywords,
        "hashtag_count":    len(hashtags),
        "recommendations":  seo["issues"],
        "linkedin_ready":   seo["seo_score"] >= 60 and readable["level"] in ("easy","medium"),
    }
