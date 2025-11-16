"""HTML content generator for COCO post-processing."""

import json
import os
from .. import genericsettings, testbedsettings

class HtmlGenerator:
    """Generates HTML content with dynamic JavaScript updates."""
    
    STATIC_TEMPLATE = """<!DOCTYPE html>
<HTML>
<HEAD>
   <META NAME="description" CONTENT="COCO/BBOB figures by function">
   <META NAME="keywords" CONTENT="COCO, BBOB">
   <META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=utf-8">
   <TITLE>COCO Post-Processing Results</TITLE>
   <SCRIPT SRC="sorttable.js"></SCRIPT>
   <style>
       body { font-family: Arial, sans-serif; margin: 20px; }
       h1 { color: #333; }
       h2 { color: #666; margin-top: 30px; }
       a { color: #0066cc; text-decoration: none; }
       a:hover { text-decoration: underline; }
       #linksContainer { margin: 20px 0; }
       .link-item { margin: 8px 0; }
       .nav-link { font-weight: bold; margin: 5px 0; }
   </style>
</HEAD>
<BODY>
<H1>COCO Post-Processing Results</H1>
<div id="linksContainer"></div>
<div id="imagesContainer"></div>

<script>
// Data injected by server
var contentData = {data};

function renderLinks(data) {
    var container = document.getElementById('linksContainer');
    var html = '';
    
    // Navigation links
    if (data.nav_links && data.nav_links.length > 0) {
        data.nav_links.forEach(function(link) {
            if (link) {
                html += '<div class="nav-link">' + link + '</div>';
            }
        });
    }
    
    // Comparison section
    if (data.comparison && data.comparison.length > 0) {
        html += '<h2>Comparison Data</h2>';
        data.comparison.forEach(function(algo) {
            var path = algo + '/' + data.many_file_name + '.html';
            html += '<div class="link-item">&nbsp;&nbsp;<a href="' + path + '">' + algo + '</a></div>';
        });
    }
    
    // Single algorithm section
    if (data.single && data.single.length > 0) {
        html += '<h2>Single Algorithm Data</h2>';
        data.single.forEach(function(algo) {
            var path = algo + '/' + data.single_file_name + '.html';
            html += '<div class="link-item">&nbsp;&nbsp;<a href="' + path + '">' + algo + '</a></div>';
        });
    }
    
    container.innerHTML = html;
}

function renderImages(data) {
    var container = document.getElementById('imagesContainer');
    var html = '';
    
    if (data.images && data.images.length > 0) {
        data.images.forEach(function(img) {
            html += '<div><a href="' + img + '"><img src="' + img + '" height="380em"></a></div>';
        });
    }
    
    container.innerHTML = html;
}

// Render on page load
if (contentData) {
    renderLinks(contentData);
    renderImages(contentData);
}
</script>

</BODY>
</HTML>"""
    
    def __init__(self):
        pass
    
    def generate_parent_index_data(self, algo_data, single_file_name, many_file_name):
        """Generate data structure for parent index."""
        return {
            'title': 'COCO Post-Processing Results',
            'header': 'COCO Post-Processing Results',
            'nav_links': [],
            'single': sorted(algo_data.get('single', [])),
            'comparison': sorted(algo_data.get('comparison', [])),
            'images': [],
            'single_file_name': single_file_name,
            'many_file_name': many_file_name
        }
    
    def generate_folder_content(self, current_dir, image_extension):
        """Generate data structure for folder index."""
        nav_links = [
            '<a href="../index.html">Home</a>',
            '<a href="pprldflex.html">Runtime profiles (with arrow keys navigation)</a>',
            '<a href="pptable.html">Tables for selected targets</a>',
            '<a href="pprldistr.html">Runtime profiles for selected targets</a>'
        ]
        
        images = []
        image_path = 'pprldmany-single-functions/pprldmany.%s' % image_extension
        if os.path.isfile(os.path.join(current_dir, image_path)):
            images.append(image_path)
        
        return {
            'title': 'COCO Post-Processing Results',
            'header': 'Results Overview',
            'nav_links': nav_links,
            'single': [],
            'comparison': [],
            'images': images,
            'single_file_name': '',
            'many_file_name': ''
        }
    
    def render(self, data):
        """Render HTML with injected data."""
        json_data = json.dumps(data, ensure_ascii=False)
        html = self.STATIC_TEMPLATE.replace('{data}', json_data)
        return html