"""Main interface for generating folder index pages."""

import logging
import os
from .generator import HtmlGenerator
from .writer import HtmlWriter
from .. import genericsettings

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
    
    This function only writes the HTML file once. Links are managed
    dynamically via JavaScript based on available algorithm directories.
    
    Args:
        parent_index_path: Path to the parent index.html file
        
    Raises:
        IOError: If there are issues reading/writing the index file
    """
    try:
        generator = HtmlGenerator()
        parent_dir = os.path.dirname(os.path.realpath(parent_index_path))
        
        # to collect data from available algorithms
        algo_data = collect_algorithm_data(parent_dir)
        
        # generating data structure for dynamic rendering
        data = generator.generate_parent_index_data(
            algo_data,
            genericsettings.single_algorithm_file_name,
            genericsettings.many_algorithm_file_name
        )
        
        # HTML rendering
        html = generator.render(data)
        
        # initial creation of the file (will be created only if it doesn't already exist)
        writer = HtmlWriter()
        if not os.path.isfile(parent_index_path):
            writer.write_safely(parent_index_path, html)
            logger.info("Created parent index at %s" % parent_index_path)
        else:
            logger.info("Parent index already exists at %s (using dynamic JS updates)" % parent_index_path)
        
    except Exception as e:
        logger.error("Failed to update parent index: %s" % str(e))
        raise IOError("Failed to update parent index: %s" % str(e))
        
def save_folder_index(filepath, image_extension):
    """Generate and save a folder index file.
    
    The HTML file is created once with static structure. Dynamic content
    is managed via JavaScript and server-side data updates.
    
    Args:
        filepath: Path where the index file should be saved
        image_extension: Extension for image files (e.g. 'svg', 'png')
    """
    if not filepath:
        return
    
    try:
        # content data generation
        generator = HtmlGenerator()
        current_dir = os.path.dirname(os.path.realpath(filepath))
        data = generator.generate_folder_content(current_dir, image_extension)
        
        # rendering to HTML
        html = generator.render(data)
        
        # initial creation of the file (created only if it doesn't already exist)
        writer = HtmlWriter()
        if not os.path.isfile(filepath):
            writer.write_safely(filepath, html)
            logger.info("Created folder index at %s" % filepath)
        else:
            logger.info("Folder index already exists at %s (using dynamic JS updates)" % filepath)
        
        # update parent index if needed
        parent_dir = os.path.dirname(current_dir)
        parent_index_path = os.path.join(parent_dir, 'index.html')
        if not os.path.isfile(parent_index_path):
            update_parent_index(parent_index_path)
            
    except Exception as e:
        logger.error("Failed to save folder index at %s: %s" % (filepath, str(e)))
        raise