"""
Reasoning prompt templates for TokenForge.

This module provides templates for reasoning tasks like:
- Logical reasoning
- Mathematical problem solving
- Chain of thought
- Analogical reasoning
"""

from typing import Dict, List, Any, Optional
from . import PromptTemplate, library

# Logical reasoning template
logical_reasoning = PromptTemplate(
    name="logical_reasoning",
    description="Template for logical reasoning tasks",
    template="""You are tasked with solving a logical reasoning problem.

Problem: {problem}

Think through this step by step:
1. Identify the key facts and constraints
2. Consider what logical rules apply
3. Draw conclusions based on the facts and rules
4. Provide your final answer

Your solution:""",
    variables=["problem"]
)

# Mathematical problem solving template
math_problem = PromptTemplate(
    name="math_problem",
    description="Template for mathematical problem solving",
    template="""Solve the following mathematical problem step by step:

Problem: {problem}

Show your work clearly, explaining each step of your solution process.

Solution:""",
    variables=["problem"]
)

# Chain of thought template
chain_of_thought = PromptTemplate(
    name="chain_of_thought",
    description="Template for chain of thought reasoning",
    template="""Question: {question}

Let's think through this step by step:""",
    variables=["question"]
)

# Analogical reasoning template
analogical_reasoning = PromptTemplate(
    name="analogical_reasoning",
    description="Template for analogical reasoning tasks",
    template="""Consider the following analogy:

{source_domain}: {source_relation}

How does this analogy apply to:

{target_domain}?

Explain the mapping between the source and target domains, and describe the relationship in the target domain.""",
    variables=["source_domain", "source_relation", "target_domain"]
)

# Register templates with the library
library.add_template(logical_reasoning)
library.add_template(math_problem)
library.add_template(chain_of_thought)
library.add_template(analogical_reasoning)
