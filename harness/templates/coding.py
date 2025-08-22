"""
Coding prompt templates for TokenForge.

This module provides templates for coding tasks like:
- Function implementation
- Code explanation
- Debugging
- Algorithm design
"""

from typing import Dict, List, Any, Optional
from . import PromptTemplate, library

# Function implementation template
function_implementation = PromptTemplate(
    name="function_implementation",
    description="Template for implementing a function in a specified language",
    template="""Write a {language} function that {task}.

Your function should:
- Be well-documented with comments
- Handle edge cases appropriately
- Follow best practices for {language}
- Be efficient in terms of time and space complexity

Function signature: {signature}

Your implementation:""",
    variables=["language", "task", "signature"]
)

# Code explanation template
code_explanation = PromptTemplate(
    name="code_explanation",
    description="Template for explaining code",
    template="""Explain the following {language} code in detail:

```{language}
{code}
```

In your explanation:
1. Describe what the code does at a high level
2. Explain the key components and their purpose
3. Identify any algorithms or data structures used
4. Note any potential issues or optimizations""",
    variables=["language", "code"]
)

# Debugging template
debugging = PromptTemplate(
    name="debugging",
    description="Template for debugging code",
    template="""The following {language} code has a bug:

```{language}
{code}
```

Error/Unexpected behavior: {error}

Expected behavior: {expected}

Please:
1. Identify the bug(s) in the code
2. Explain why the bug occurs
3. Provide a fixed version of the code""",
    variables=["language", "code", "error", "expected"]
)

# Algorithm design template
algorithm_design = PromptTemplate(
    name="algorithm_design",
    description="Template for designing algorithms",
    template="""Design an algorithm to solve the following problem:

Problem: {problem}

Requirements:
- Time complexity: {time_complexity}
- Space complexity: {space_complexity}
- Input: {input_description}
- Output: {output_description}

Provide:
1. A high-level description of your approach
2. Pseudocode or {language} code implementing your algorithm
3. An explanation of the time and space complexity
4. Examples showing how your algorithm works on test cases""",
    variables=["problem", "time_complexity", "space_complexity", "input_description", "output_description", "language"]
)

# Register templates with the library
library.add_template(function_implementation)
library.add_template(code_explanation)
library.add_template(debugging)
library.add_template(algorithm_design)
