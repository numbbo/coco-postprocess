"""Safe file writing utilities for HTML output."""

import os
import shutil
from pathlib import Path
from typing import Union, Optional
import tempfile

class HtmlWriter:
    """Handles safe writing of HTML files with atomic operations."""
    
    @staticmethod
    def write_safely(filepath: Union[str, Path], content: str) -> None:
        """Write content to file atomically using a temporary file."""
        filepath = Path(filepath)
        
        # Create parent directories if they don't exist
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Write to temporary file first
        tmp = tempfile.NamedTemporaryFile(mode='w', delete=False, dir=str(filepath.parent))
        try:
            tmp.write(content)
            tmp.close()
            
            # Atomic replace
            shutil.move(tmp.name, str(filepath))
        except Exception as e:
            # Clean up temp file if anything goes wrong
            os.unlink(tmp.name)
            raise IOError(f"Failed to write {filepath}: {str(e)}")
            
    @staticmethod
    def backup_if_exists(filepath: Union[str, Path], max_backups: int = 5) -> None:
        """Create numbered backup of existing file."""
        filepath = Path(filepath)
        if not filepath.exists():
            return
            
        for i in range(max_backups - 1, 0, -1):
            backup = filepath.with_suffix(f'.html.{i}')
            prev_backup = filepath.with_suffix(f'.html.{i-1}')
            
            if prev_backup.exists():
                shutil.move(str(prev_backup), str(backup))
                
        backup = filepath.with_suffix('.html.1')
        shutil.copy2(str(filepath), str(backup))