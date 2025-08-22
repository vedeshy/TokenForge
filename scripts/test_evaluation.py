#!/usr/bin/env python3
"""
Test script for the evaluation metrics.
"""

import sys
import os

# Add the project root to the path so we can import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from harness.evaluation import (
    calculate_bleu,
    calculate_rouge,
    calculate_factual_accuracy,
    calculate_coherence,
    evaluate_response
)
from harness.evaluation.references import (
    get_reference_for_question,
    get_reference_for_logical_problem,
    get_reference_for_code
)

def test_individual_metrics():
    """Test individual evaluation metrics."""
    print("\n=== Testing Individual Metrics ===\n")
    
    # Test data
    reference = "The capital of France is Paris."
    hypothesis_good = "Paris is the capital of France."
    hypothesis_bad = "The capital of France is Berlin."
    
    # Test BLEU
    print("Testing BLEU score:")
    bleu_good = calculate_bleu(hypothesis_good, reference)
    bleu_bad = calculate_bleu(hypothesis_bad, reference)
    print(f"  Good response BLEU: {bleu_good:.4f}")
    print(f"  Bad response BLEU: {bleu_bad:.4f}")
    
    # Test ROUGE
    print("\nTesting ROUGE scores:")
    rouge_good = calculate_rouge(hypothesis_good, reference)
    rouge_bad = calculate_rouge(hypothesis_bad, reference)
    print(f"  Good response ROUGE-1: {rouge_good['rouge1']:.4f}")
    print(f"  Good response ROUGE-L: {rouge_good['rougeL']:.4f}")
    print(f"  Bad response ROUGE-1: {rouge_bad['rouge1']:.4f}")
    print(f"  Bad response ROUGE-L: {rouge_bad['rougeL']:.4f}")
    
    # Test factual accuracy
    print("\nTesting factual accuracy:")
    facts = ["Paris", "capital of France"]
    factual_good = calculate_factual_accuracy(hypothesis_good, facts)
    factual_bad = calculate_factual_accuracy(hypothesis_bad, facts)
    print(f"  Good response factual accuracy: {factual_good:.4f}")
    print(f"  Bad response factual accuracy: {factual_bad:.4f}")
    
    # Test coherence
    print("\nTesting coherence:")
    coherent_text = "The sky is blue. Blue is a calming color. Many people find calm colors relaxing."
    incoherent_text = "The sky is blue. Elephants have long trunks. Python is a programming language."
    coherence_good = calculate_coherence(coherent_text)
    coherence_bad = calculate_coherence(incoherent_text)
    print(f"  Coherent text score: {coherence_good:.4f}")
    print(f"  Incoherent text score: {coherence_bad:.4f}")

def test_combined_evaluation():
    """Test combined evaluation function."""
    print("\n=== Testing Combined Evaluation ===\n")
    
    # Test data
    reference = "The capital of France is Paris."
    hypothesis = "Paris is the capital of France."
    facts = ["Paris", "capital of France"]
    
    # Evaluate with all metrics
    print("Evaluating with all metrics:")
    result = evaluate_response(hypothesis, reference, facts)
    for metric, score in result.items():
        print(f"  {metric}: {score:.4f}")
    
    # Evaluate with specific metrics
    print("\nEvaluating with specific metrics:")
    result = evaluate_response(hypothesis, reference, facts, metrics=["bleu", "factual"])
    for metric, score in result.items():
        print(f"  {metric}: {score:.4f}")

def test_reference_data():
    """Test reference data retrieval."""
    print("\n=== Testing Reference Data Retrieval ===\n")
    
    # Test factual QA references
    questions = [
        "What is the capital of France?",
        "Who wrote the novel '1984'?",
        "What is the boiling point of water in Celsius?"
    ]
    
    print("Testing factual QA references:")
    for question in questions:
        reference = get_reference_for_question(question)
        print(f"  Question: {question}")
        print(f"  Reference: {reference['reference']}")
        print(f"  Facts: {reference['facts']}")
        print()
    
    # Test logical reasoning references
    problems = [
        "If all A are B, and all B are C, what can we conclude about the relationship between A and C?",
        "If it's not raining, then Susan walks to work. Susan is not walking to work. What can we conclude?"
    ]
    
    print("Testing logical reasoning references:")
    for problem in problems:
        reference = get_reference_for_logical_problem(problem)
        print(f"  Problem: {problem}")
        print(f"  Reference: {reference['reference'][:100]}..." if reference['reference'] else "No reference found")
        print(f"  Facts: {reference['facts']}")
        print()
    
    # Test code references
    tasks = [
        "sorts a list of integers using the quicksort algorithm",
        "implements a binary search algorithm"
    ]
    
    print("Testing code references:")
    for task in tasks:
        reference = get_reference_for_code(task, "Python")
        print(f"  Task: {task}")
        print(f"  Reference: {reference['reference'][:100]}..." if reference['reference'] else "No reference found")
        print(f"  Facts: {reference['facts']}")
        print()

def test_evaluation_workflow():
    """Test the complete evaluation workflow."""
    print("\n=== Testing Complete Evaluation Workflow ===\n")
    
    # Sample LLM response
    question = "What is the capital of France?"
    llm_response = "The capital of France is Paris, which is located in the north-central part of the country."
    
    # Get reference data
    reference_data = get_reference_for_question(question)
    
    # Evaluate response
    evaluation = evaluate_response(
        llm_response,
        reference=reference_data["reference"],
        facts=reference_data["facts"]
    )
    
    print(f"Question: {question}")
    print(f"LLM response: {llm_response}")
    print(f"Reference: {reference_data['reference']}")
    print(f"Facts: {reference_data['facts']}")
    print("\nEvaluation results:")
    for metric, score in evaluation.items():
        print(f"  {metric}: {score:.4f}")

if __name__ == "__main__":
    test_individual_metrics()
    test_combined_evaluation()
    test_reference_data()
    test_evaluation_workflow()
    print("\nEvaluation tests completed!")
