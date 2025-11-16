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
        fd, tmp_path = tempfile.mkstemp(dir=parent_dir, text=True)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as tmp:
                tmp.write(content)
            
            # Atomic replace
            if os.path.exists(filepath):
                os.remove(filepath)
            shutil.move(tmp_path, filepath)
        except Exception as e:
            # Clean up temp file if anything goes wrong
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise IOError(f"Failed to write {filepath}: {str(e)}")
            
    @staticmethod
    def backup_if_exists(filepath, max_backups=5):
        """Create numbered backup of existing file.
        
        Args:
            filepath: Path to the file to backup
            max_backups: Maximum number of backups to keep
        """
        filepath = str(filepath)
        if not os.path.exists(filepath):
            return
            
        # Rotate existing backups
        for i in range(max_backups - 1, 0, -1):
            backup = filepath + '.%d' % i
            prev_backup = filepath + '.%d' % (i - 1)
            
            if os.path.exists(prev_backup):
                if os.path.exists(backup):
                    os.remove(backup)
                shutil.move(prev_backup, backup)
        
        # Create new backup
        backup = filepath + '.1'
        if os.path.exists(backup):
            os.remove(backup)
        shutil.copy2(filepath, backup)