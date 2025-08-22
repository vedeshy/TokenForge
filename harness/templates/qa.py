"""
Question-answering prompt templates for TokenForge.

This module provides templates for Q&A tasks like:
- Factual Q&A
- Open-ended Q&A
- Multiple choice Q&A
- Explanatory Q&A
"""

from typing import Dict, List, Any, Optional
from . import PromptTemplate, library

# Factual Q&A template
factual_qa = PromptTemplate(
    name="factual_qa",
    description="Template for factual question answering",
    template="""Answer the following factual question accurately and concisely:

Question: {question}

Answer:""",
    variables=["question"]
)

# Open-ended Q&A template
open_ended_qa = PromptTemplate(
    name="open_ended_qa",
    description="Template for open-ended question answering",
    template="""Provide a thoughtful response to the following open-ended question:

Question: {question}

Consider multiple perspectives and provide a nuanced answer.""",
    variables=["question"]
)

# Multiple choice Q&A template
multiple_choice_qa = PromptTemplate(
    name="multiple_choice_qa",
    description="Template for multiple choice question answering",
    template="""Answer the following multiple choice question:

Question: {question}

Options:
{options}

Choose the best answer and explain your reasoning.""",
    variables=["question", "options"]
)

# Explanatory Q&A template
explanatory_qa = PromptTemplate(
    name="explanatory_qa",
    description="Template for explanatory question answering",
    template="""Explain the following concept in detail:

Topic: {topic}

Your explanation should:
- Define key terms
- Provide examples
- Explain underlying principles
- Address common misconceptions
- Be accessible to someone with {knowledge_level} knowledge""",
    variables=["topic", "knowledge_level"]
)

# Register templates with the library
library.add_template(factual_qa)
library.add_template(open_ended_qa)
library.add_template(multiple_choice_qa)
library.add_template(explanatory_qa)
