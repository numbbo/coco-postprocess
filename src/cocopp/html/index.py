"""Main interface for generating folder index pages."""

import logging
import os
from .generator import HtmlGenerator, HtmlContent  
from .writer import HtmlWriter
from .. import genericsettings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def collect_algorithm_data(directory):
    """Collect algorithm data from directory structure."""
    data = {'single': [], 'comparison': []}
    
    if not os.path.isdir(directory):
        return data
    
    try:
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            if not os.path.isdir(item_path):
                continue
            
            single_file = os.path.join(item_path, '%s.html' % genericsettings.single_algorithm_file_name)
            if os.path.isfile(single_file):
                data['single'].append(item)
            
            many_file = os.path.join(item_path, '%s.html' % genericsettings.many_algorithm_file_name)
            if os.path.isfile(many_file):
                data['comparison'].append(item)
    except OSError as e:
        logger.warning("Error reading directory %s: %s" % (directory, str(e)))
    
    return data

def update_parent_index(parent_index_path):
    """Update the parent index.html file with links to algorithm results.
    
    This function scans the parent directory for algorithm results and 
    generates a new index page with organized links to single algorithm
    and comparison results.
    
    Args:
        parent_index_path: Path to the parent index.html file
        
    Raises:
        IOError: If there are issues reading/writing the index file
    """
    try:
        generator = HtmlGenerator()
        parent_dir = os.path.dirname(os.path.realpath(parent_index_path))
        
        # Collect data about available algorithms
        algo_data = collect_algorithm_data(parent_dir)
        
        # Generate links sections
        links = []
        
        # Add comparison section if we have any
        if algo_data['comparison']:
            links.append('<H2>Comparison Data</H2>')
            for algo in sorted(algo_data['comparison']):
                # Use absolute path for checking, relative for linking
                abs_path = os.path.join(parent_dir, algo, '%s.html' % genericsettings.many_algorithm_file_name)
                rel_path = os.path.join(algo, '%s.html' % genericsettings.many_algorithm_file_name)
                if os.path.isfile(abs_path):
                    link = generator.add_link(rel_path, algo, '&nbsp;&nbsp;')
                    links.append(link)
                
        # Add single algorithm section
        if algo_data['single']:
            links.append('<H2>Single Algorithm Data</H2>')
            for algo in sorted(algo_data['single']):
                # Use absolute path for checking, relative for linking
                abs_path = os.path.join(parent_dir, algo, '%s.html' % genericsettings.single_algorithm_file_name)
                rel_path = os.path.join(algo, '%s.html' % genericsettings.single_algorithm_file_name)
                if os.path.isfile(abs_path):
                    link = generator.add_link(rel_path, algo, '&nbsp;&nbsp;')
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
        writer.backup_if_exists(parent_index_path)
        writer.write_safely(parent_index_path, html)
        
        logger.info("Successfully updated parent index at %s" % parent_index_path)
        
    except Exception as e:
        logger.error("Failed to update parent index: %s" % str(e))
        raise IOError("Failed to update parent index: %s" % str(e))
        
def save_folder_index(filepath, image_extension):
    """Generate and save a folder index file.
    
    Args:
        filepath: Path where the index file should be saved
        image_extension: Extension for image files (e.g. 'svg', 'png')
    """
    if not filepath:
        return
    
    try:
        # Generate content
        generator = HtmlGenerator()
        current_dir = os.path.dirname(os.path.realpath(filepath))
        content = generator.generate_folder_content(current_dir, image_extension)
        
        # Render to HTML
        html = generator.render(content)
        
        # Safely write to file with backup
        writer = HtmlWriter()
        writer.backup_if_exists(filepath)
        writer.write_safely(filepath, html)
        
        # Update parent index if needed
        parent_dir = os.path.dirname(current_dir)
        parent_index_path = os.path.join(parent_dir, 'index.html')
        if os.path.isfile(parent_index_path):
            update_parent_index(parent_index_path)
            
    except Exception as e:
        logger.error("Failed to save folder index at %s: %s" % (filepath, str(e)))
        raise