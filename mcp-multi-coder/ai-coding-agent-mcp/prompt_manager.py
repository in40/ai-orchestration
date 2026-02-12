import os
from pathlib import Path
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class PromptManager:
    """
    Manager for prompt templates used by the AI coding agent.
    
    Handles loading, listing, and rendering of prompt templates.
    """
    
    def __init__(self, prompts_dir: str = "./prompts"):
        self.prompts_dir = Path(prompts_dir)
        self.prompts_dir.mkdir(exist_ok=True)
    
    def list_prompts(self) -> List[str]:
        """
        List all available prompt templates.
        
        Returns:
            List of prompt template names
        """
        prompt_files = list(self.prompts_dir.glob("*.txt"))
        return [file.stem for file in prompt_files]
    
    def get_prompt_template(self, name: str) -> str:
        """
        Get the content of a prompt template.
        
        Args:
            name: Name of the prompt template (without extension)
            
        Returns:
            Content of the prompt template
        """
        prompt_file = self.prompts_dir / f"{name}.txt"
        
        if not prompt_file.exists():
            raise FileNotFoundError(f"Prompt template '{name}' not found")
        
        with open(prompt_file, 'r', encoding='utf-8') as f:
            return f.read()
    
    def render_prompt(self, template_name: str, variables: Dict[str, str]) -> str:
        """
        Render a prompt template with the given variables.
        
        Args:
            template_name: Name of the prompt template
            variables: Dictionary of variables to substitute in the template
            
        Returns:
            Rendered prompt string
        """
        template = self.get_prompt_template(template_name)
        
        try:
            # Use string formatting to replace placeholders
            rendered_prompt = template.format(**variables)
            return rendered_prompt
        except KeyError as e:
            raise ValueError(f"Missing required variable in prompt template: {str(e)}")
        except Exception as e:
            raise ValueError(f"Error rendering prompt template: {str(e)}")


# Example usage
def main():
    prompt_manager = PromptManager()
    
    # List available prompts
    prompts = prompt_manager.list_prompts()
    print("Available prompts:", prompts)
    
    # Render a sample prompt
    if "coding_task" in prompts:
        variables = {
            "task_description": "Create a Python function that calculates factorial",
            "language": "Python",
            "additional_requirements": "Include error handling for negative inputs"
        }
        
        rendered = prompt_manager.render_prompt("coding_task", variables)
        print("\nRendered prompt:")
        print(rendered)


if __name__ == "__main__":
    main()