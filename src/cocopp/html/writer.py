"""Safe file writing utilities for HTML output."""

import os
import shutil
import tempfile

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
        
        # Create parent directories if they don't exist
        parent_dir = os.path.dirname(filepath)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir)
        
        # Write to temporary file first
        fd, tmp_path = tempfile.mkstemp(dir=parent_dir or '.', text=True)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8', newline='') as tmp:
                tmp.write(content)
            
            # Atomic move - replaces if exists
            shutil.move(tmp_path, filepath)
            
        except Exception as e:
            # Clean up temp file if anything goes wrong
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise IOError("Failed to write %s: %s" % (filepath, str(e)))