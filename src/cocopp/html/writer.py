"""Safe file writing utilities for HTML output."""

import os

class HtmlWriter:
    """Handles safe writing of HTML files with atomic operations."""
    
    @staticmethod
    def write_safely(filepath, content):
        """Write content to file atomically using a temporary file.
        
        Args:
            filepath: Path to the output file
            content: HTML content to write
        """
        filepath = str(filepath)
        
        # creating parent directories (if they don't already exist)
        parent_dir = os.path.dirname(filepath)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir)
        
        try:
            with open(filepath, 'w', encoding='utf-8', newline='') as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())  # forcing writing to disk (for mac users)
        except Exception as e:
            raise IOError("Failed to write %s: %s" % (filepath, str(e)))