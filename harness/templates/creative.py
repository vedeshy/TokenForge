"""
Creative writing prompt templates for TokenForge.

This module provides templates for creative tasks like:
- Story writing
- Poetry
- Dialogue
- Content creation
"""

from typing import Dict, List, Any, Optional
from . import PromptTemplate, library

# Story writing template
story_writing = PromptTemplate(
    name="story_writing",
    description="Template for creative story writing",
    template="""Write a {genre} story with the following elements:

Setting: {setting}
Main character: {character}
Theme: {theme}
Conflict: {conflict}

Your story should be engaging, creative, and approximately {length} words.""",
    variables=["genre", "setting", "character", "theme", "conflict", "length"]
)

# Poetry template
poetry = PromptTemplate(
    name="poetry",
    description="Template for poetry writing",
    template="""Write a {form} poem about {topic}.

Style: {style}
Mood: {mood}
Length: {length} lines

Your poem should evoke emotion and use vivid imagery.""",
    variables=["form", "topic", "style", "mood", "length"]
)

# Dialogue template
dialogue = PromptTemplate(
    name="dialogue",
    description="Template for writing dialogue",
    template="""Write a dialogue between {character1} and {character2} about {topic}.

Setting: {setting}
Relationship: {relationship}
Conflict: {conflict}

The dialogue should reveal character traits and advance the narrative.""",
    variables=["character1", "character2", "topic", "setting", "relationship", "conflict"]
)

# Content creation template
content_creation = PromptTemplate(
    name="content_creation",
    description="Template for creating marketing or educational content",
    template="""Create {content_type} about {topic} for {audience}.

Purpose: {purpose}
Tone: {tone}
Key points to include:
{key_points}

Length: Approximately {length} words.""",
    variables=["content_type", "topic", "audience", "purpose", "tone", "key_points", "length"]
)

# Register templates with the library
library.add_template(story_writing)
library.add_template(poetry)
library.add_template(dialogue)
library.add_template(content_creation)
