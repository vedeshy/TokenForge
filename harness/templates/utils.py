"""
Utility functions for working with prompt templates.
"""

import os
import random
import yaml
import json
from typing import Dict, List, Any, Optional, Union

from . import PromptTemplate, TemplateLibrary, library
from . import reasoning, coding, creative, qa

def load_all_templates():
    """
    Load all templates from the template modules.
    
    Note: This is done automatically when the modules are imported.
    """
    # The templates are already loaded when the modules are imported
    pass

def get_template(name: str) -> PromptTemplate:
    """
    Get a template by name.
    
    Args:
        name: Name of the template
        
    Returns:
        PromptTemplate instance
    """
    return library.get_template(name)

def list_templates() -> List[str]:
    """
    List all available templates.
    
    Returns:
        List of template names
    """
    return library.list_templates()

def generate_prompt(template_name: str, **kwargs) -> str:
    """
    Generate a prompt using a template.
    
    Args:
        template_name: Name of the template
        **kwargs: Variables to substitute in the template
        
    Returns:
        Formatted prompt string
    """
    template = get_template(template_name)
    return template.format(**kwargs)

def load_variables_from_file(file_path: str) -> Dict[str, Any]:
    """
    Load template variables from a YAML or JSON file.
    
    Args:
        file_path: Path to the variables file
        
    Returns:
        Dictionary of variables
    """
    with open(file_path, 'r') as f:
        if file_path.endswith('.yaml') or file_path.endswith('.yml'):
            return yaml.safe_load(f)
        elif file_path.endswith('.json'):
            return json.load(f)
        else:
            raise ValueError(f"Unsupported file format: {file_path}")

def generate_prompt_from_file(template_name: str, variables_file: str) -> str:
    """
    Generate a prompt using a template and variables from a file.
    
    Args:
        template_name: Name of the template
        variables_file: Path to the variables file
        
    Returns:
        Formatted prompt string
    """
    variables = load_variables_from_file(variables_file)
    return generate_prompt(template_name, **variables)

def save_template_examples(output_dir: str, format: str = 'yaml') -> None:
    """
    Save example variable files for all templates.
    
    Args:
        output_dir: Directory to save example files
        format: File format ('yaml' or 'json')
    """
    os.makedirs(output_dir, exist_ok=True)
    
    for name in list_templates():
        template = get_template(name)
        
        # Create example variables
        example_vars = {}
        for var in template.variables:
            example_vars[var] = f"[Example {var}]"
        
        # Save example file
        file_name = f"{name}_example.{format}"
        file_path = os.path.join(output_dir, file_name)
        
        with open(file_path, 'w') as f:
            if format == 'yaml':
                yaml.dump(example_vars, f, default_flow_style=False)
            elif format == 'json':
                json.dump(example_vars, f, indent=2)
            else:
                raise ValueError(f"Unsupported format: {format}")

def generate_batch_prompts(template_name: str, variables_list: List[Dict[str, Any]]) -> List[str]:
    """
    Generate multiple prompts using the same template.
    
    Args:
        template_name: Name of the template
        variables_list: List of variable dictionaries
        
    Returns:
        List of formatted prompt strings
    """
    template = get_template(template_name)
    return [template.format(**vars) for vars in variables_list]
