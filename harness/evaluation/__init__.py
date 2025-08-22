"""
Evaluation metrics for TokenForge benchmarks.

This module provides various metrics for evaluating LLM responses:
- BLEU: Measures n-gram precision
- ROUGE: Measures n-gram recall
- Factual accuracy: Measures factual correctness
- Coherence: Measures text coherence
"""

from .metrics import (
    calculate_bleu,
    calculate_rouge,
    calculate_factual_accuracy,
    calculate_coherence,
    evaluate_response,
    evaluate_responses
)
