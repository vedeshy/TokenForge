"""
Evaluation metrics for TokenForge benchmarks.
"""

import re
import json
import nltk
import numpy as np
from typing import Dict, List, Any, Optional, Union, Tuple
from rouge_score import rouge_scorer
import evaluate

# Download necessary NLTK data
try:
    nltk.download('punkt', quiet=True)
    nltk.download('wordnet', quiet=True)
except:
    print("Warning: Could not download NLTK data. Some metrics may not work correctly.")

# Load evaluation metrics
try:
    bleu = evaluate.load('bleu')
    bertscore = evaluate.load('bertscore')
except Exception as e:
    print(f"Warning: Could not load some evaluation metrics: {e}")
    bleu = None
    bertscore = None

def calculate_bleu(hypothesis: str, reference: str) -> float:
    """
    Calculate BLEU score between hypothesis and reference.
    
    Args:
        hypothesis: Model-generated text
        reference: Reference text (ground truth)
        
    Returns:
        BLEU score (0-1)
    """
    if not bleu:
        return 0.0
    
    try:
        # Tokenize
        hypothesis_tokens = nltk.word_tokenize(hypothesis.lower())
        reference_tokens = nltk.word_tokenize(reference.lower())
        
        # Calculate BLEU
        result = bleu.compute(predictions=[hypothesis_tokens], references=[[reference_tokens]])
        return result['bleu']
    except Exception as e:
        print(f"Error calculating BLEU: {e}")
        return 0.0

def calculate_rouge(hypothesis: str, reference: str) -> Dict[str, float]:
    """
    Calculate ROUGE scores between hypothesis and reference.
    
    Args:
        hypothesis: Model-generated text
        reference: Reference text (ground truth)
        
    Returns:
        Dictionary of ROUGE scores (rouge1, rouge2, rougeL)
    """
    try:
        scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)
        scores = scorer.score(reference, hypothesis)
        
        return {
            'rouge1': scores['rouge1'].fmeasure,
            'rouge2': scores['rouge2'].fmeasure,
            'rougeL': scores['rougeL'].fmeasure
        }
    except Exception as e:
        print(f"Error calculating ROUGE: {e}")
        return {'rouge1': 0.0, 'rouge2': 0.0, 'rougeL': 0.0}

def calculate_factual_accuracy(response: str, facts: List[str]) -> float:
    """
    Calculate factual accuracy by checking if key facts are present in the response.
    
    Args:
        response: Model-generated text
        facts: List of key facts that should be present
        
    Returns:
        Factual accuracy score (0-1)
    """
    if not facts:
        return 0.0
    
    response_lower = response.lower()
    
    # Count how many facts are present in the response
    facts_present = sum(1 for fact in facts if fact.lower() in response_lower)
    
    # Calculate accuracy
    return facts_present / len(facts)

def calculate_coherence(text: str) -> float:
    """
    Calculate coherence score based on sentence transitions.
    
    Args:
        text: Text to evaluate
        
    Returns:
        Coherence score (0-1)
    """
    try:
        # Split into sentences
        sentences = nltk.sent_tokenize(text)
        
        if len(sentences) <= 1:
            return 1.0  # Single sentence is coherent by default
        
        # Calculate cosine similarity between adjacent sentences
        similarities = []
        
        for i in range(len(sentences) - 1):
            # Simple word overlap as a proxy for similarity
            words1 = set(nltk.word_tokenize(sentences[i].lower()))
            words2 = set(nltk.word_tokenize(sentences[i + 1].lower()))
            
            if not words1 or not words2:
                continue
                
            overlap = len(words1.intersection(words2))
            similarity = overlap / (len(words1) + len(words2) - overlap)  # Jaccard similarity
            similarities.append(similarity)
        
        # Average similarity as coherence score
        if similarities:
            return sum(similarities) / len(similarities)
        else:
            return 0.0
    except Exception as e:
        print(f"Error calculating coherence: {e}")
        return 0.0

def calculate_bert_score(hypothesis: str, reference: str) -> Dict[str, float]:
    """
    Calculate BERTScore between hypothesis and reference.
    
    Args:
        hypothesis: Model-generated text
        reference: Reference text (ground truth)
        
    Returns:
        Dictionary of BERTScore components (precision, recall, f1)
    """
    if not bertscore:
        return {'precision': 0.0, 'recall': 0.0, 'f1': 0.0}
    
    try:
        result = bertscore.compute(predictions=[hypothesis], references=[reference], lang="en")
        return {
            'precision': float(result['precision'][0]),
            'recall': float(result['recall'][0]),
            'f1': float(result['f1'][0])
        }
    except Exception as e:
        print(f"Error calculating BERTScore: {e}")
        return {'precision': 0.0, 'recall': 0.0, 'f1': 0.0}

def evaluate_response(
    response: str,
    reference: Optional[str] = None,
    facts: Optional[List[str]] = None,
    metrics: Optional[List[str]] = None
) -> Dict[str, float]:
    """
    Evaluate a response using multiple metrics.
    
    Args:
        response: Model-generated text
        reference: Reference text (ground truth)
        facts: List of key facts that should be present
        metrics: List of metrics to calculate
        
    Returns:
        Dictionary of evaluation metrics
    """
    if metrics is None:
        metrics = ['bleu', 'rouge', 'factual', 'coherence', 'bertscore']
    
    results = {}
    
    # Calculate requested metrics
    if 'bleu' in metrics and reference:
        results['bleu'] = calculate_bleu(response, reference)
    
    if 'rouge' in metrics and reference:
        rouge_scores = calculate_rouge(response, reference)
        results.update(rouge_scores)
    
    if 'factual' in metrics and facts:
        results['factual_accuracy'] = calculate_factual_accuracy(response, facts)
    
    if 'coherence' in metrics:
        results['coherence'] = calculate_coherence(response)
    
    if 'bertscore' in metrics and reference:
        bertscore_results = calculate_bert_score(response, reference)
        results['bertscore_precision'] = bertscore_results['precision']
        results['bertscore_recall'] = bertscore_results['recall']
        results['bertscore_f1'] = bertscore_results['f1']
    
    return results

def evaluate_responses(
    responses: List[str],
    references: Optional[List[str]] = None,
    facts_list: Optional[List[List[str]]] = None,
    metrics: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Evaluate multiple responses using multiple metrics.
    
    Args:
        responses: List of model-generated texts
        references: List of reference texts (ground truths)
        facts_list: List of lists of key facts
        metrics: List of metrics to calculate
        
    Returns:
        Dictionary of evaluation metrics with averages
    """
    if metrics is None:
        metrics = ['bleu', 'rouge', 'factual', 'coherence', 'bertscore']
    
    all_results = []
    
    # Evaluate each response
    for i, response in enumerate(responses):
        reference = references[i] if references and i < len(references) else None
        facts = facts_list[i] if facts_list and i < len(facts_list) else None
        
        result = evaluate_response(response, reference, facts, metrics)
        all_results.append(result)
    
    # Calculate averages
    averages = {}
    for metric in all_results[0].keys():
        values = [result.get(metric, 0.0) for result in all_results]
        averages[metric] = sum(values) / len(values)
    
    return {
        'individual': all_results,
        'average': averages
    }
