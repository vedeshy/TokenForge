"""
Prompt Templates Library for TokenForge

This module provides standardized prompt templates for different tasks
to ensure consistent benchmarking across models and runtimes.
"""

import os
import yaml
import json
from typing import Dict, List, Any, Optional, Union

class PromptTemplate:
    """Base class for all prompt templates."""
    
    def __init__(self, name: str, description: str, template: str, variables: List[str]):
        """
        Initialize a prompt template.
        
        Args:
            name: Name of the template
            description: Description of the template
            template: Template string with placeholders for variables
            variables: List of variable names used in the template
        """
        self.name = name
        self.description = description
        self.template = template
        self.variables = variables
        
    def format(self, **kwargs) -> str:
        """
        Format the template with the provided variables.
        
        Args:
            **kwargs: Variables to substitute in the template
            
        Returns:
            Formatted prompt string
        """
        # Validate that all required variables are provided
        missing_vars = [var for var in self.variables if var not in kwargs]
        if missing_vars:
            raise ValueError(f"Missing required variables: {', '.join(missing_vars)}")
        
        # Format the template
        return self.template.format(**kwargs)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the template to a dictionary.
        
        Returns:
            Dictionary representation of the template
        """
        return {
            "name": self.name,
            "description": self.description,
            "template": self.template,
            "variables": self.variables
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PromptTemplate':
        """
        Create a template from a dictionary.
        
        Args:
            data: Dictionary representation of the template
            
        Returns:
            PromptTemplate instance
        """
        return cls(
            name=data["name"],
            description=data["description"],
            template=data["template"],
            variables=data["variables"]
        )
    
    @classmethod
    def from_file(cls, file_path: str) -> 'PromptTemplate':
        """
        Load a template from a YAML or JSON file.
        
        Args:
            file_path: Path to the template file
            
        Returns:
            PromptTemplate instance
        """
        with open(file_path, 'r') as f:
            if file_path.endswith('.yaml') or file_path.endswith('.yml'):
                data = yaml.safe_load(f)
            elif file_path.endswith('.json'):
                data = json.load(f)
            else:
                raise ValueError(f"Unsupported file format: {file_path}")
        
        return cls.from_dict(data)
    
    def save(self, file_path: str) -> None:
        """
        Save the template to a YAML or JSON file.
        
        Args:
            file_path: Path to save the template
        """
        data = self.to_dict()
        
        with open(file_path, 'w') as f:
            if file_path.endswith('.yaml') or file_path.endswith('.yml'):
                yaml.dump(data, f, default_flow_style=False)
            elif file_path.endswith('.json'):
                json.dump(data, f, indent=2)
            else:
                raise ValueError(f"Unsupported file format: {file_path}")


class TemplateLibrary:
    """Library of prompt templates."""
    
    def __init__(self):
        """Initialize an empty template library."""
        self.templates = {}
        
    def add_template(self, template: PromptTemplate) -> None:
        """
        Add a template to the library.
        
        Args:
            template: PromptTemplate instance to add
        """
        self.templates[template.name] = template
        
    def get_template(self, name: str) -> PromptTemplate:
        """
        Get a template by name.
        
        Args:
            name: Name of the template
            
        Returns:
            PromptTemplate instance
        """
        if name not in self.templates:
            raise ValueError(f"Template not found: {name}")
        
        return self.templates[name]
    
    def list_templates(self) -> List[str]:
        """
        List all available templates.
        
        Returns:
            List of template names
        """
        return list(self.templates.keys())
    
    def load_from_directory(self, directory: str) -> None:
        """
        Load all templates from a directory.
        
        Args:
            directory: Directory containing template files
        """
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith(('.yaml', '.yml', '.json')):
                    file_path = os.path.join(root, file)
                    try:
                        template = PromptTemplate.from_file(file_path)
                        self.add_template(template)
                    except Exception as e:
                        print(f"Error loading template {file_path}: {e}")
    
    def save_to_directory(self, directory: str, format: str = 'yaml') -> None:
        """
        Save all templates to a directory.
        
        Args:
            directory: Directory to save templates
            format: File format ('yaml' or 'json')
        """
        os.makedirs(directory, exist_ok=True)
        
        for name, template in self.templates.items():
            file_name = f"{name}.{format}"
            file_path = os.path.join(directory, file_name)
            template.save(file_path)


# Create a global template library instance
library = TemplateLibrary()
