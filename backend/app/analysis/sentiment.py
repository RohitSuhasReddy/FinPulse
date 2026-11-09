"""Transparent finance-domain heuristic; optional offline FinBERT inference.

Rule classifications are estimates of language polarity, NEVER stock performance.
No model weights are downloaded automatically. Set FINPULSE_SENTIMENT=finbert
and pre-cache model weights to opt into optional FinBERT.
"""
import os
import re
from functools import lru_cache

POSITIVE = {'growth', 'grew', 'surged', 'strong', 'improved', 'increase', 'increased',
            'outperformed', 'exceeded', 'gain', 'gains', 'record', 'resilient', 'beat',
            'profit', 'profitable', 'higher', 'accelerated', 'expansion'}
NEGATIVE = {'decline', 'declined', 'fell', 'weak', 'risk', 'risks', 'uncertain', 'loss',
            'losses', 'pressure', 'slower', 'miss', 'missed', 'below', 'headwind',
            'headwinds', 'downturn', 'shortfall', 'reduced', 'lower', 'challenging'}
NEGATIONS = {'not', 'never', 'no', 'without'}


def rules_sentiment(text: str) -> str:
    words = re.findall(r"[a-z]+", text.lower())
    score = 0
    for index, word in enumerate(words):
        polarity = int(word in POSITIVE) - int(word in NEGATIVE)
        if polarity and any(neg in NEGATIONS for neg in words[max(0, index - 3):index]):
            polarity *= -1
        score += polarity
    return 'positive' if score >= 2 else 'negative' if score <= -2 else 'neutral'


@lru_cache(maxsize=1)
def _finbert():
    from transformers import pipeline
    return pipeline('text-classification', model='ProsusAI/finbert',
                    tokenizer='ProsusAI/finbert', model_kwargs={'local_files_only': True})


def classify(text: str) -> tuple[str, str]:
    if os.getenv('FINPULSE_SENTIMENT', 'rules').lower() == 'finbert':
        try:
            # Model truncation is explicit; avoid presenting a long document as one passage.
            labels = [_finbert()(text[i:i + 700], truncation=True)[0]['label'].lower()
                      for i in range(0, min(len(text), 3500), 700)]
            return max(('positive', 'negative', 'neutral'), key=labels.count), 'FinBERT (local, sampled passages)'
        except (ImportError, OSError, RuntimeError, ValueError):
            pass
    return rules_sentiment(text), 'rules-v1 (estimated)'
