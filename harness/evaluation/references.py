"""
Reference data for evaluating model responses.
"""

from typing import Dict, List, Any

# Factual QA references
FACTUAL_QA_REFERENCES = {
    "What is the capital of France?": {
        "reference": "The capital of France is Paris.",
        "facts": ["Paris", "capital of France"]
    },
    "Who wrote the novel '1984'?": {
        "reference": "George Orwell wrote the novel '1984'.",
        "facts": ["George Orwell", "1984"]
    },
    "What is the boiling point of water in Celsius?": {
        "reference": "The boiling point of water is 100 degrees Celsius at standard atmospheric pressure.",
        "facts": ["100 degrees", "Celsius", "standard atmospheric pressure"]
    },
    "What is the largest planet in our solar system?": {
        "reference": "Jupiter is the largest planet in our solar system.",
        "facts": ["Jupiter", "largest planet"]
    },
    "Who painted the Mona Lisa?": {
        "reference": "Leonardo da Vinci painted the Mona Lisa.",
        "facts": ["Leonardo da Vinci", "Mona Lisa"]
    },
    "What is the chemical symbol for gold?": {
        "reference": "The chemical symbol for gold is Au.",
        "facts": ["Au", "chemical symbol", "gold"]
    },
    "What is the tallest mountain in the world?": {
        "reference": "Mount Everest is the tallest mountain in the world above sea level.",
        "facts": ["Mount Everest", "tallest mountain", "above sea level"]
    },
    "What year did World War II end?": {
        "reference": "World War II ended in 1945.",
        "facts": ["1945", "World War II"]
    },
    "What is the speed of light?": {
        "reference": "The speed of light in a vacuum is approximately 299,792,458 meters per second.",
        "facts": ["299,792,458", "meters per second", "vacuum"]
    },
    "Who is the current Secretary-General of the United Nations?": {
        "reference": "António Guterres is the current Secretary-General of the United Nations.",
        "facts": ["António Guterres", "Secretary-General", "United Nations"]
    }
}

# Logical reasoning references
LOGICAL_REASONING_REFERENCES = {
    "If all A are B, and all B are C, what can we conclude about the relationship between A and C?": {
        "reference": "If all A are B, and all B are C, then all A are C. This follows from the transitive property of logical implication.",
        "facts": ["all A are C", "transitive property"]
    },
    "There are five houses in a row, each painted a different color. The green house is next to the white house. The red house is on the far left. The yellow house is two houses away from the blue house. The white house is on the far right. What is the order of the houses from left to right?": {
        "reference": "The order of the houses from left to right is: red, yellow, blue, green, white.",
        "facts": ["red, yellow, blue, green, white", "left to right"]
    },
    "If it's not raining, then Susan walks to work. Susan is not walking to work. What can we conclude?": {
        "reference": "If it's not raining, then Susan walks to work. Susan is not walking to work. Using modus tollens (denying the consequent), we can conclude that it is raining.",
        "facts": ["it is raining", "modus tollens"]
    }
}

# Code function references
CODE_FUNCTION_REFERENCES = {
    "Python quicksort": {
        "reference": """
def quicksort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quicksort(left) + middle + quicksort(right)
""",
        "facts": ["partition", "recursive", "pivot", "quicksort"]
    },
    "Python binary search": {
        "reference": """
def binary_search(arr, target):
    left, right = 0, len(arr) - 1
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1
""",
        "facts": ["binary search", "mid point", "divide and conquer", "O(log n)"]
    }
}

def get_reference_for_question(question: str) -> Dict[str, Any]:
    """
    Get reference data for a factual question.
    
    Args:
        question: The question to get reference data for
        
    Returns:
        Dictionary with reference text and facts
    """
    # Try exact match
    if question in FACTUAL_QA_REFERENCES:
        return FACTUAL_QA_REFERENCES[question]
    
    # Try partial match
    for q, ref in FACTUAL_QA_REFERENCES.items():
        if question.lower() in q.lower() or q.lower() in question.lower():
            return ref
    
    # No match found
    return {"reference": None, "facts": []}

def get_reference_for_logical_problem(problem: str) -> Dict[str, Any]:
    """
    Get reference data for a logical reasoning problem.
    
    Args:
        problem: The logical reasoning problem
        
    Returns:
        Dictionary with reference solution and facts
    """
    # Try exact match
    if problem in LOGICAL_REASONING_REFERENCES:
        return LOGICAL_REASONING_REFERENCES[problem]
    
    # Try partial match
    for p, ref in LOGICAL_REASONING_REFERENCES.items():
        if problem.lower() in p.lower() or p.lower() in problem.lower():
            return ref
    
    # No match found
    return {"reference": None, "facts": []}

def get_reference_for_code(task: str, language: str) -> Dict[str, Any]:
    """
    Get reference data for a coding task.
    
    Args:
        task: The coding task description
        language: The programming language
        
    Returns:
        Dictionary with reference code and facts
    """
    key = f"{language} {task}"
    
    # Try to find a matching reference
    for k, ref in CODE_FUNCTION_REFERENCES.items():
        if task.lower() in k.lower() or k.lower() in task.lower():
            return ref
    
    # No match found
    return {"reference": None, "facts": []}
