"""Main interface for generating folder index pages."""

from pathlib import Path
from typing import List, Dict
import logging
from .generator import HtmlGenerator, HtmlContent  
from .writer import HtmlWriter
from .. import genericsettings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def collect_algorithm_data(directory: Path) -> Dict[str, List[str]]:
    """Collect algorithm data from directory structure.
    
    Args:
        directory: Path to scan for algorithm data
        
    Returns:
        Dictionary with 'single' and 'comparison' algorithm lists
    """
    try:
        data = {
            'single': [],
            'comparison': []
        }
        
        for item in directory.iterdir():
            if not item.is_dir():
                continue
                
            # Check for single algorithm results
            single_file = item / f"{genericsettings.single_algorithm_file_name}.html"
            if single_file.exists():
                data['single'].append(item.name)
                
            # Check for comparison results    
            many_file = item / f"{genericsettings.many_algorithm_file_name}.html"
            if many_file.exists():
                data['comparison'].append(item.name)
                
        return data
    except Exception as e:
        logger.error(f"Error collecting algorithm data: {str(e)}")
        return {'single': [], 'comparison': []}

def update_parent_index(parent_index: Path) -> None:
    """Update the parent index.html file with links to algorithm results.
    
    This function scans the parent directory for algorithm results and 
    generates a new index page with organized links to single algorithm
    and comparison results.
    
    Args:
        parent_index: Path to the parent index.html file
        
    Raises:
        IOError: If there are issues reading/writing the index file
    """
    try:
        generator = HtmlGenerator()
        parent_dir = parent_index.parent
        
        # Collect data about available algorithms
        algo_data = collect_algorithm_data(parent_dir)
        
        # Generate links sections
        links = []
        
        # Add comparison section if we have any
        if algo_data['comparison']:
            links.append('<H2>Comparison Data</H2>')
            for algo in sorted(algo_data['comparison']):
                link = generator.add_link(
                    path=str(Path(algo) / f"{genericsettings.many_algorithm_file_name}.html"),
                    label=algo,
                    indent='&nbsp;&nbsp;'
                )
                links.append(link)
                
        # Add single algorithm section
        if algo_data['single']:
            links.append('<H2>Single Algorithm Data</H2>')
            for algo in sorted(algo_data['single']):
                link = generator.add_link(
                    path=str(Path(algo) / f"{genericsettings.single_algorithm_file_name}.html"),
                    label=algo,
                    indent='&nbsp;&nbsp;'
                )
                links.append(link)
                
        # Create content object
        content = HtmlContent(
            title="COCO Post-Processing Results",
            header="COCO Post-Processing Results",
            body="",
            links=links,
            images=[],
            footer=""
        )
        
        # Render HTML
        html = generator.render(content)
        
        # Safely write the file
        writer = HtmlWriter()
        writer.backup_if_exists(parent_index)
        writer.write_safely(parent_index, html)
        
        logger.info(f"Successfully updated parent index at {parent_index}")
        
    except Exception as e:
        logger.error(f"Failed to update parent index: {str(e)}")
        raise IOError(f"Failed to update parent index: {str(e)}")
        
def save_folder_index(filepath: str, image_extension: str) -> None:
    """Generate and save a folder index file.
    
    Args:
        filepath: Path where the index file should be saved
        image_extension: Extension for image files (e.g. 'svg', 'png')
    """
    if not filepath:
        return
        
    # Generate content
    generator = HtmlGenerator()
    current_dir = str(Path(filepath).parent)
    content = generator.generate_folder_content(current_dir, image_extension)
    
    # Render to HTML
    html = generator.render(content)
    
    # Safely write to file with backup
    writer = HtmlWriter()
    writer.backup_if_exists(filepath)
    writer.write_safely(filepath, html)
    
    # Update parent index if needed
    parent_index = Path(filepath).parent.parent / 'index.html'
    if parent_index.exists():
        update_parent_index(parent_index)