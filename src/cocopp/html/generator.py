"""HTML content generator for COCO post-processing."""

from dataclasses import dataclass
from typing import List, Optional
import os
from .. import genericsettings, testbedsettings

@dataclass
class HtmlContent:
    """Container for HTML content sections."""
    title: str
    header: str
    body: str
    links: List[str]
    images: List[str]
    footer: str

class HtmlGenerator:
    """Generates HTML content without file I/O concerns."""
    
    def __init__(self):
        self.templates = {
            'header': """<HTML>
<HEAD>
   <META NAME="description" CONTENT="COCO/BBOB figures by function">
   <META NAME="keywords" CONTENT="COCO, BBOB">
   <META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=iso-8859-1">
   <TITLE>{title}</TITLE>
   <SCRIPT SRC="sorttable.js"></SCRIPT>
</HEAD>
<BODY>
<H1>{header}</H1>
{links}
""",
            'footer': "\n</BODY>\n</HTML>"
        }

    def add_image(self, image_name: str, add_link: bool = True, height: int = 160) -> str:
        """Generate HTML for an image."""
        if add_link:
            return f'<a href="{image_name}"><IMG SRC="{image_name}" height="{height}em"></a>'
        return f'<IMG SRC="{image_name}" height="{height}em">'

    def add_link(self, path: str, label: str, indent: str = '') -> str:
        """Generate HTML for a link."""
        if os.path.isfile(path):
            return f'{indent}<a href="{path}">{label}</a><br>\n'
        return ''

    def generate_folder_content(self, current_dir: str, image_extension: str) -> HtmlContent:
        """Generate content for a folder index."""
        links = []
        images = []
        
        # Add navigation links
        links.extend([
            self.add_link('../index.html', 'Home'),
            self.add_link('pprldflex.html', 'Runtime profiles (with arrow keys navigation)'),
            self.add_link('pptable.html', 'Tables for selected targets'),
            self.add_link('pprldistr.html', 'Runtime profiles for selected targets')
        ])

        # Add summary image if exists
        image_path = f'pprldmany-single-functions/pprldmany.{image_extension}'
        if os.path.isfile(os.path.join(current_dir, image_path)):
            images.append(self.add_image(image_path, True, 380))

        return HtmlContent(
            title="COCO Post-Processing Results",
            header="Results Overview",
            body="",
            links=links,
            images=images,
            footer=self.templates['footer']
        )

    def render(self, content: HtmlContent) -> str:
        """Render HTML content to string."""
        html = self.templates['header'].format(
            title=content.title,
            header=content.header,
            links='\n'.join(content.links)
        )
        
        if content.body:
            html += content.body
            
        if content.images:
            html += '\n'.join(content.images)
            
        html += content.footer
        return html