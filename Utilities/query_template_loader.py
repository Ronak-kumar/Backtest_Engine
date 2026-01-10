import os
import re
from typing import Dict, Optional


class QueryTemplateLoader:
    """
    Utility class to load and use specific query templates from the options_sql file.
    
    Usage:
        loader = QueryTemplateLoader()
        query = loader.get_template(1, table_name="options")
        # Use query with parameters in ClickHouse client
    """
    
    def __init__(self, query_file_path: Optional[str] = None):
        """
        Initialize the QueryTemplateLoader.
        
        Args:
            query_file_path: Path to the options_sql file. If None, uses default path.
        """
        if query_file_path is None:
            # Default path relative to this utility file
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            query_file_path = os.path.join(base_path, 'queries', 'options_sql')
        
        self.query_file_path = query_file_path
        self._templates_cache: Dict[int, str] = {}
        self._load_templates()
    
    def _load_templates(self):
        """Load and parse all query templates from the file."""
        if not os.path.exists(self.query_file_path):
            raise FileNotFoundError(f"Query template file not found: {self.query_file_path}")
        
        with open(self.query_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split by template sections (numbered templates)
        # Pattern matches: "-- N. TEMPLATE NAME" where N is a number
        pattern = r'-- =+?\n-- (\d+)\.\s+([^\n]+)\n-- =+?\n'
        matches = list(re.finditer(pattern, content))
        
        for i, match in enumerate(matches):
            template_num = int(match.group(1))
            start_pos = match.end()
            
            # Find the end of this template (start of next template or end of file)
            if i + 1 < len(matches):
                end_pos = matches[i + 1].start()
            else:
                # Last template - find next major section or end of file
                next_section = re.search(r'-- =+?\n-- COMMON TABLE COLUMNS', content[start_pos:])
                if next_section:
                    end_pos = start_pos + next_section.start()
                else:
                    end_pos = len(content)
            
            # Extract the query (remove comments and blank lines at start/end)
            template_content = content[start_pos:end_pos].strip()
            
            # Remove parameter documentation comments
            lines = template_content.split('\n')
            query_lines = []
            skip_until_blank = False
            
            for line in lines:
                if line.strip().startswith('-- Parameters:'):
                    skip_until_blank = True
                    continue
                if skip_until_blank:
                    if line.strip() == '':
                        skip_until_blank = False
                    continue
                if not line.strip().startswith('--') or line.strip() == '--':
                    query_lines.append(line)
            
            query = '\n'.join(query_lines).strip()
            
            # Remove extra blank lines
            query = re.sub(r'\n\s*\n\s*\n', '\n\n', query)
            
            self._templates_cache[template_num] = query
    
    def get_template(self, template_number: int, table_name: str = "options", **kwargs) -> str:
        """
        Get a specific query template and replace placeholders.
        
        Args:
            template_number: The template number (1-15)
            table_name: The table name to replace {table_name} placeholder
            **kwargs: Additional placeholder replacements (e.g., custom_column="Timestamp, Close")
        
        Returns:
            The query string with placeholders replaced
        
        Example:
            query = loader.get_template(1, table_name="options")
            query = loader.get_template(2, table_name="options", custom_column="Timestamp, Close")
        """
        if template_number not in self._templates_cache:
            raise ValueError(f"Template {template_number} not found. Available templates: {sorted(self._templates_cache.keys())}")
        
        query = self._templates_cache[template_number]
        
        # Replace {table_name} placeholder
        query = query.replace('{table_name}', table_name)
        
        # Replace any additional placeholders from kwargs
        for key, value in kwargs.items():
            placeholder = f'{{{key}}}'
            query = query.replace(placeholder, str(value))
        
        return query
    
    def list_templates(self) -> Dict[int, str]:
        """
        List all available templates with their numbers and names.
        
        Returns:
            Dictionary mapping template numbers to template names
        """
        if not os.path.exists(self.query_file_path):
            return {}
        
        with open(self.query_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        pattern = r'-- =+?\n-- (\d+)\.\s+([^\n]+)\n-- =+?\n'
        matches = re.findall(pattern, content)
        
        return {int(num): name.strip() for num, name in matches}
    
    def get_template_info(self, template_number: int) -> Dict[str, str]:
        """
        Get information about a specific template including its description and parameters.
        
        Args:
            template_number: The template number
            
        Returns:
            Dictionary with 'name', 'query', and 'parameters' keys
        """
        if template_number not in self._templates_cache:
            raise ValueError(f"Template {template_number} not found")
        
        if not os.path.exists(self.query_file_path):
            return {}
        
        with open(self.query_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find template name
        pattern = r'-- =+?\n-- (\d+)\.\s+([^\n]+)\n-- =+?\n'
        matches = list(re.finditer(pattern, content))
        
        template_name = None
        for match in matches:
            if int(match.group(1)) == template_number:
                template_name = match.group(2).strip()
                start_pos = match.end()
                break
        
        # Extract parameter documentation
        param_section = re.search(
            r'-- Parameters:\n((?:--\s+[^\n]+\n?)+)',
            content[start_pos:start_pos + 2000] if 'start_pos' in locals() else content
        )
        
        parameters = ""
        if param_section:
            parameters = param_section.group(1).strip()
        
        return {
            'name': template_name or f"Template {template_number}",
            'query': self._templates_cache[template_number],
            'parameters': parameters
        }


# Example usage
if __name__ == "__main__":
    # Initialize loader
    loader = QueryTemplateLoader()
    
    # List all available templates
    print("Available Templates:")
    templates = loader.list_templates()
    for num, name in templates.items():
        print(f"  {num}. {name}")
    
    print("\n" + "="*60 + "\n")
    
    # Get a specific template
    print("Example: Getting Template 1 (Basic Query)")
    query = loader.get_template(1, table_name="options")
    print(query)
    
    print("\n" + "="*60 + "\n")
    
    # Get template info
    print("Template 2 Info:")
    info = loader.get_template_info(2)
    print(f"Name: {info['name']}")
    print(f"\nParameters:\n{info['parameters']}")
    print(f"\nQuery:\n{info['query']}")
