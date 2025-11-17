// Data injected by server
var contentData = window.contentData || {};

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
document.addEventListener('DOMContentLoaded', function() {
    if (contentData) {
        renderLinks(contentData);
        renderImages(contentData);
    }
});
