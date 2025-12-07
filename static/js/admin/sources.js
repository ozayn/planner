// Source Management Functions
// Note: allSources is stored in window.allSources (no local declaration)

async function loadSources() {
    try {
        const response = await fetch('/api/admin/sources');
        
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Failed to load sources: ${response.status} ${errorText}`);
        }
        
        const data = await response.json();
        
        // Check if response has error property
        if (data.error) {
            throw new Error(data.error);
        }
        
        // Handle both array and object with sources property
        let sources = Array.isArray(data) ? data : (data.sources || []);
        
        // Sort by most recently updated first (descending)
        sources.sort((a, b) => {
            const aDate = new Date(a.updated_at || a.created_at || 0);
            const bDate = new Date(b.updated_at || b.created_at || 0);
            return bDate - aDate; // Descending order (most recent first)
        });
        
        window.allSources = sources;
        window.filteredSources = null; // Reset filters
        
        populateSourceFilters();
        
        // Update filter summary
        const summary = document.getElementById('sourceFilterSummary');
        if (summary) {
            summary.textContent = `Showing all ${window.allSources.length} sources`;
        }
        
        // Always try to render - renderSourcesTable will handle visibility checks
        renderSourcesTable();
        
    } catch (error) {
        console.error('Error loading sources:', error);
        const tableBody = document.getElementById('sourcesTable');
        if (tableBody) {
            tableBody.innerHTML = `<tr><td colspan="8" class="loading" style="color: #dc3545;">❌ Error loading sources: ${error.message}</td></tr>`;
        }
    }
}

function renderSourcesTable() {
    const data = window.filteredSources || window.allSources || [];
    
    // Ensure the section exists
    const sourcesSection = document.getElementById('sources');
    if (!sourcesSection) {
        console.error('Sources section not found, skipping render');
        return;
    }
    
    // Ensure the section is visible
    sourcesSection.style.setProperty('display', 'block', 'important');
    sourcesSection.style.setProperty('visibility', 'visible', 'important');
    sourcesSection.style.setProperty('opacity', '1', 'important');
    sourcesSection.style.setProperty('position', 'relative', 'important');
    sourcesSection.style.setProperty('width', '100%', 'important');
    sourcesSection.style.setProperty('min-height', '500px', 'important');
    
    // Ensure the table container is visible before rendering
    const tableContainer = sourcesSection.querySelector('.table-container');
    if (tableContainer) {
        tableContainer.style.setProperty('display', 'block', 'important');
        tableContainer.style.setProperty('visibility', 'visible', 'important');
        tableContainer.style.setProperty('opacity', '1', 'important');
        tableContainer.style.setProperty('min-height', '400px', 'important');
        tableContainer.style.setProperty('height', 'auto', 'important');
        tableContainer.style.setProperty('position', 'relative', 'important');
        tableContainer.style.setProperty('z-index', '1', 'important');
    } else {
        console.error('Table container not found in sources section');
    }
    
    // Always render - renderDynamicTable will handle the table visibility
    // Use requestAnimationFrame to ensure DOM is ready
    requestAnimationFrame(() => {
        renderDynamicTable('sourcesTable', data, 'sources');
    });
}

function editSource(id) {
    const source = window.allSources.find(s => s.id == id);
    if (!source) {
        alert('Source not found');
        return;
    }
    
    // Populate edit form
    document.getElementById('editSourceId').value = source.id;
    document.getElementById('editSourceName').value = source.name;
    document.getElementById('editSourceHandle').value = source.handle;
    document.getElementById('editSourceType').value = source.source_type;
    document.getElementById('editSourceCity').value = source.city_id;
    document.getElementById('editSourceUrl').value = source.url || '';
    document.getElementById('editSourceDescription').value = source.description || '';
    document.getElementById('editSourceReliability').value = source.reliability_score || 5;
    document.getElementById('editSourceFrequency').value = source.posting_frequency || '';
    document.getElementById('editSourceEventTypes').value = source.event_types ? JSON.parse(source.event_types).join(', ') : '';
    document.getElementById('editSourceNotes').value = source.notes || '';
    document.getElementById('editSourceScrapingPattern').value = source.scraping_pattern || '';
    document.getElementById('editSourceActive').checked = source.is_active;
    
    document.getElementById('editSourceModal').style.display = 'block';
}

function deleteSource(id) {
    if (confirm('Are you sure you want to delete this source?')) {
        fetch(`/api/delete-source/${id}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                alert('Source deleted successfully!');
                loadSources();
            } else {
                alert('Error: ' + result.error);
            }
        })
        .catch(error => {
            alert('Error deleting source: ' + error.message);
        });
    }
}

function applySourceFilters() {
    if (!window.allSources) return;
    
    const searchTerm = document.getElementById('sourceSearch').value.toLowerCase();
    const typeFilter = document.getElementById('sourceTypeFilter').value;
    const cityFilter = document.getElementById('sourceCityFilter').value;
    
    window.filteredSources = window.allSources.filter(source => {
        const matchesSearch = !searchTerm || 
            source.name.toLowerCase().includes(searchTerm) ||
            source.handle.toLowerCase().includes(searchTerm) ||
            (source.description && source.description.toLowerCase().includes(searchTerm));
        
        const matchesType = !typeFilter || source.source_type === typeFilter;
        const matchesCity = !cityFilter || source.city_id == cityFilter;
        
        return matchesSearch && matchesType && matchesCity;
    });
    
    // Sort by most recently updated first (descending) - default sort order
    window.filteredSources.sort((a, b) => {
        const aDate = new Date(a.updated_at || a.created_at || 0);
        const bDate = new Date(b.updated_at || b.created_at || 0);
        return bDate - aDate; // Descending order (most recent first)
    });
    
    // Update filter summary
    const summary = document.getElementById('sourceFilterSummary');
    if (summary) {
        const activeFilters = [];
        if (searchTerm) activeFilters.push(`Search: "${searchTerm}"`);
        if (typeFilter) activeFilters.push(`Type: ${typeFilter}`);
        if (cityFilter) activeFilters.push(`City: ${document.getElementById('sourceCityFilter').selectedOptions[0]?.text || cityFilter}`);
        
        summary.textContent = activeFilters.length > 0 ? 
            `Showing ${window.filteredSources.length} of ${window.allSources.length} sources (${activeFilters.join(', ')})` : 
            `Showing all ${window.allSources.length} sources`;
    }
    
    renderSourcesTable();
}

function clearSourceFilters() {
    document.getElementById('sourceSearch').value = '';
    document.getElementById('sourceTypeFilter').value = '';
    document.getElementById('sourceCityFilter').value = '';
    
    // Reset filtered sources to show all
    window.filteredSources = null;
    renderSourcesTable();
    
    const summary = document.getElementById('sourceFilterSummary');
    if (summary) {
        summary.textContent = `Showing all ${window.allSources.length} sources`;
    }
}

function openAddSourceModal() {
    // Load cities for the dropdown
    loadCitiesForSourceModal();
    document.getElementById('addSourceModal').style.display = 'block';
    document.getElementById('addSourceForm').reset();
}

function loadCitiesForSourceModal() {
    fetch('/api/admin/cities')
        .then(response => response.json())
        .then(cities => {
            const citySelects = ['sourceCity', 'editSourceCity'];
            citySelects.forEach(selectId => {
                const select = document.getElementById(selectId);
                if (select) {
                    // Clear existing options except the first one
                    while (select.children.length > 1) {
                        select.removeChild(select.lastChild);
                    }
                    
                    cities.forEach(city => {
                        const option = document.createElement('option');
                        option.value = city.id;
                        option.textContent = city.display_name || `${city.name}, ${city.country}`;
                        select.appendChild(option);
                    });
                }
            });
        })
        .catch(error => console.error('Error loading cities:', error));
}

function populateSourceFilters() {
    const cityFilter = document.getElementById('sourceCityFilter');
    
    if (cityFilter) {
        // Clear existing options except the first one
        while (cityFilter.children.length > 1) {
            cityFilter.removeChild(cityFilter.lastChild);
        }
        
        // Get unique cities from sources
        const cityMap = new Map();
        window.allSources.forEach(source => {
            if (source.city_id && source.city_name) {
                cityMap.set(source.city_id, source.city_name);
            }
        });
        
        // Sort cities by name for better UX
        const sortedCities = Array.from(cityMap.entries()).sort((a, b) => a[1].localeCompare(b[1]));
        
        sortedCities.forEach(([cityId, cityName]) => {
            const option = document.createElement('option');
            option.value = cityId;
            option.textContent = cityName;
            cityFilter.appendChild(option);
        });
    }
}

// Form handlers
document.getElementById('addSourceForm').addEventListener('submit', handleAddSource);
document.getElementById('editSourceForm').addEventListener('submit', handleEditSource);

function detectSourceType(input) {
    // Detect if input is Instagram handle or website URL
    if (input.startsWith('@')) {
        return {
            type: 'instagram',
            handle: input,
            url: `https://www.instagram.com/${input.substring(1)}/`,
            name: input.substring(1).replace(/[-_]/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
        };
    } else if (input.includes('instagram.com')) {
        // Extract handle from Instagram URL
        const match = input.match(/instagram\.com\/([^\/\?]+)/);
        if (match) {
            const handle = `@${match[1]}`;
            return {
                type: 'instagram',
                handle: handle,
                url: input,
                name: match[1].replace(/[-_]/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
            };
        }
    } else if (input.startsWith('http://') || input.startsWith('https://')) {
        // Website URL
        const domain = new URL(input).hostname;
        return {
            type: 'website',
            handle: domain,
            url: input,
            name: domain.replace('www.', '').split('.')[0].replace(/[-_]/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
        };
    } else {
        // Assume it's a handle without @
        return {
            type: 'instagram',
            handle: `@${input}`,
            url: `https://www.instagram.com/${input}/`,
            name: input.replace(/[-_]/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
        };
    }
}

async function handleAddSource(event) {
    event.preventDefault();
    
    const sourceInput = document.getElementById('sourceInput').value.trim();
    const cityId = parseInt(document.getElementById('sourceCity').value);
    
    if (!sourceInput || !cityId) {
        alert('Please enter a source handle/URL and select a city');
        return;
    }
    
    // Detect source type and auto-fill fields
    const detected = detectSourceType(sourceInput);
    
    const formData = {
        name: detected.name,
        handle: detected.handle,
        source_type: detected.type,
        city_id: cityId,
        url: detected.url,
        description: document.getElementById('sourceDescription').value.trim() || '',
        reliability_score: parseFloat(document.getElementById('sourceReliability').value) || 7.0,
        posting_frequency: document.getElementById('sourceFrequency').value || 'weekly',
        event_types: JSON.stringify(document.getElementById('sourceEventTypes').value.split(',').map(t => t.trim()).filter(t => t)),
        notes: document.getElementById('sourceNotes').value.trim() || '',
        scraping_pattern: document.getElementById('sourceScrapingPattern').value.trim() || '',
        is_active: document.getElementById('sourceActive').checked
    };
    
    try {
        const response = await fetch('/api/admin/add-source', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            alert('Source added successfully!');
            closeModal('addSourceModal');
            loadSources();
        } else {
            alert('Error: ' + result.error);
        }
    } catch (error) {
        alert('Error adding source: ' + error.message);
    }
}

async function handleEditSource(event) {
    event.preventDefault();
    
    const editData = {
        id: parseInt(document.getElementById('editSourceId').value),
        name: document.getElementById('editSourceName').value.trim(),
        handle: document.getElementById('editSourceHandle').value.trim(),
        source_type: document.getElementById('editSourceType').value,
        city_id: parseInt(document.getElementById('editSourceCity').value),
        url: document.getElementById('editSourceUrl').value.trim(),
        description: document.getElementById('editSourceDescription').value.trim(),
        reliability_score: parseFloat(document.getElementById('editSourceReliability').value),
        posting_frequency: document.getElementById('editSourceFrequency').value,
        event_types: JSON.stringify(document.getElementById('editSourceEventTypes').value.split(',').map(t => t.trim()).filter(t => t)),
        notes: document.getElementById('editSourceNotes').value.trim(),
        scraping_pattern: document.getElementById('editSourceScrapingPattern').value.trim(),
        is_active: document.getElementById('editSourceActive').checked
    };
    
    try {
        const response = await fetch('/api/admin/edit-source', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(editData)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            alert('Source updated successfully!');
            closeModal('editSourceModal');
            loadSources();
        } else {
            alert('Error: ' + result.error);
        }
    } catch (error) {
        alert('Error updating source: ' + error.message);
    }
}

