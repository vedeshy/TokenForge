#!/usr/bin/env python3
"""
Test script for the prompt templates library.
"""

import sys
import os

# Add the project root to the path so we can import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from harness.templates import utils as template_utils
from harness.templates import library

def test_template_library():
    """Test the template library functionality."""
    print("\n=== Testing Template Library ===\n")
    
    # List all available templates
    templates = template_utils.list_templates()
    print(f"Available templates ({len(templates)}):")
    for template in templates:
        print(f"  - {template}")
    
    # Test a few specific templates
    test_templates = [
        "factual_qa",
        "logical_reasoning",
        "function_implementation",
        "story_writing"
    ]
    
    for template_name in test_templates:
        print(f"\nTesting template: {template_name}")
        try:
            template = template_utils.get_template(template_name)
            print(f"  Description: {template.description}")
            print(f"  Variables: {', '.join(template.variables)}")
            
            # Create example variables
            example_vars = {}
            for var in template.variables:
                example_vars[var] = f"[Example {var}]"
            
            # Format the template
            formatted = template.format(**example_vars)
            print(f"\n  Formatted template (first 100 chars):\n  {formatted[:100]}...\n")
            
            print(f"  Template test successful: ✓")
        except Exception as e:
            print(f"  Error testing template: {e}")

def test_specific_templates():
    """Test specific templates with realistic values."""
    print("\n=== Testing Specific Templates with Real Values ===\n")
    
    # Test factual QA template
    print("Testing factual_qa template:")
    try:
        prompt = template_utils.generate_prompt("factual_qa", question="What is the capital of France?")
        print(f"  Generated prompt: {prompt}")
    except Exception as e:
        print(f"  Error: {e}")
    
    # Test logical reasoning template
    print("\nTesting logical_reasoning template:")
    try:
        prompt = template_utils.generate_prompt(
            "logical_reasoning", 
            problem="If all A are B, and all B are C, what can we conclude about the relationship between A and C?"
        )
        print(f"  Generated prompt: {prompt}")
    except Exception as e:
        print(f"  Error: {e}")
    
    # Test function implementation template
    print("\nTesting function_implementation template:")
    try:
        prompt = template_utils.generate_prompt(
            "function_implementation",
            language="Python",
            task="sorts a list of integers using the quicksort algorithm",
            signature="def quicksort(arr: list) -> list:"
        )
        print(f"  Generated prompt: {prompt}")
    except Exception as e:
        print(f"  Error: {e}")

def test_loading_examples():
    """Test loading examples from files."""
    print("\n=== Testing Loading Examples from Files ===\n")
    
    example_files = [
        "harness/templates/qa/factual_qa_examples.yaml",
        "harness/templates/reasoning/logical_reasoning_examples.yaml",
        "harness/templates/coding/function_implementation_examples.yaml",
        "harness/templates/creative/story_writing_examples.yaml"
    ]
    
    for file_path in example_files:
        print(f"Loading examples from {file_path}:")
        try:
            variables = template_utils.load_variables_from_file(file_path)
            if isinstance(variables, list):
                print(f"  Loaded {len(variables)} examples")
                if variables:
                    print(f"  First example: {variables[0]}")
            else:
                print(f"  Loaded example: {variables}")
        except Exception as e:
            print(f"  Error: {e}")

if __name__ == "__main__":
    test_template_library()
    test_specific_templates()
    test_loading_examples()
    print("\nTemplate tests completed!")
