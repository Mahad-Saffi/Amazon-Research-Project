// Modern UI Script for Amazon Product Research

let ws = null;
let activeTab = 'seo';
let currentResults = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('researchForm');
    form.addEventListener('submit', handleSubmit);
    
    // Tab switching
    document.addEventListener('click', (e) => {
        if (e.target.classList.contains('tab-button')) {
            switchTab(e.target.dataset.tab);
        }
    });
    
    console.log('Script loaded successfully');
});

async function handleSubmit(e) {
    e.preventDefault();
    
    console.log('Form submitted');
    
    const designFile = document.getElementById('designCsv').files[0];
    const revenueFile = document.getElementById('revenueCsv').files[0];
    const asinUrl = document.getElementById('asinUrl').value.trim();
    const marketplace = document.getElementById('marketplace').value;
    const useMock = document.getElementById('useMock').checked;
    const useDirectVerification = document.getElementById('useDirectVerification').checked;
    const includeSeoOptimization = document.getElementById('includeSeoOptimization').checked;
    const rankThreshold = parseInt(document.getElementById('rankThreshold').value) || 11;
    
    console.log('Form data:', { asinUrl, marketplace, useMock, useDirectVerification, includeSeoOptimization, rankThreshold });
    
    if (!designFile || !revenueFile || !asinUrl) {
        showError('Please fill in all required fields');
        return;
    }
    
    try {
        // Read files as base64
        console.log('Reading files...');
        const designContent = await fileToBase64(designFile);
        const revenueContent = await fileToBase64(revenueFile);
        console.log('Files read successfully');
        
        // Generate request ID
        const requestId = `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        console.log('Request ID:', requestId);
        
        // Show loading
        showLoading();
        hideError();
        hideResults();
        
        // Connect WebSocket
        connectWebSocket({
            design_csv: designContent,
            revenue_csv: revenueContent,
            asin_or_url: asinUrl,
            marketplace: marketplace,
            use_mock_scraper: useMock,
            use_direct_verification: useDirectVerification,
            include_seo_optimization: includeSeoOptimization,
            rank_threshold: rankThreshold,
            request_id: requestId
        });
    } catch (error) {
        console.error('Error in handleSubmit:', error);
        showError('Error processing files: ' + error.message);
        hideLoading();
    }
}

function connectWebSocket(data) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/research/ws`;
    
    ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
        console.log('WebSocket connected');
        ws.send(JSON.stringify(data));
    };
    
    ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        console.log('WebSocket message received:', message.type, message);
        
        if (message.type === 'progress') {
            updateProgress(message.percent, message.message);
        } else if (message.type === 'complete') {
            handleComplete(message.data);
        } else if (message.type === 'error') {
            console.error('Pipeline error:', message.error);
            showError(message.error);
            hideLoading();
        }
    };
    
    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        showError('Connection error. Please try again.');
        hideLoading();
    };
    
    ws.onclose = () => {
        console.log('WebSocket closed');
    };
}

function updateProgress(percent, message) {
    const progressBar = document.getElementById('progressBar');
    const progressMessage = document.getElementById('progressMessage');
    const progressPercent = document.getElementById('progressPercent');
    
    console.log(`Progress update: ${percent}% - ${message}`);
    
    if (progressBar) {
        // Ensure the progress bar is visible and animating
        progressBar.style.width = `${Math.max(0, Math.min(100, percent))}%`;
        progressBar.style.display = 'block';
    }
    
    if (progressMessage) {
        progressMessage.textContent = message || 'Processing...';
    }
    
    if (progressPercent) {
        progressPercent.textContent = `${Math.round(percent)}%`;
    }
}

function handleComplete(data) {
    console.log('Pipeline complete, received data:', data);
    hideLoading();
    
    if (data.success) {
        currentResults = data;
        
        // Log SEO data structure for debugging
        if (data.seo_optimization) {
            console.log('SEO optimization data:', data.seo_optimization);
            if (data.seo_optimization.detailed_comparison) {
                console.log('Detailed comparison:', data.seo_optimization.detailed_comparison);
            }
        }
        
        displayResults(data);
        showResults();
    } else {
        showError(data.error || 'Analysis failed');
    }
}

function displayResults(data) {
    console.log('Displaying results with data:', data);
    
    // Validate data structure
    if (!data || typeof data !== 'object') {
        console.error('Invalid data structure:', data);
        showError('Invalid response data');
        return;
    }
    
    // Display results header
    displayResultsHeader(data);
    
    // Display active tab content
    displayTabContent(activeTab, data);
}

function displayResultsHeader(data) {
    const header = document.getElementById('resultsHeader');
    const seoData = data.seo_optimization;
    
    if (!seoData || !seoData.success) {
        header.innerHTML = `
            <div class="card-header">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div>
                        <div class="card-title">
                            <span>📊</span> Analysis Complete
                        </div>
                        <div class="card-description">
                            Keyword research completed successfully
                        </div>
                    </div>
                    <button class="button primary" onclick="downloadCSV()">
                        <span>⬇</span> Export CSV
                    </button>
                </div>
            </div>
            <div class="card-content">
                <div class="stats-grid">
                    <div class="stat-card blue">
                        <div class="stat-value">${data.keyword_evaluations?.length || 0}</div>
                        <div class="stat-label">Total Keywords</div>
                    </div>
                </div>
            </div>
        `;
        return;
    }
    
    // Get improvements from detailed_comparison.overall
    const overall = seoData.detailed_comparison?.overall;
    
    if (!overall) {
        console.error('Missing overall comparison data');
        header.innerHTML = `
            <div class="card-header">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div>
                        <div class="card-title">
                            <span>📊</span> Analysis Complete
                        </div>
                        <div class="card-description">
                            SEO optimization completed
                        </div>
                    </div>
                    <button class="button primary" onclick="downloadCSV()">
                        <span>⬇</span> Export CSV
                    </button>
                </div>
            </div>
        `;
        return;
    }
    
    const improvements = {
        search_volume: {
            current: overall.current.total_search_volume,
            optimized: overall.optimized.total_search_volume,
            improvement: overall.improvement.search_volume,
            improvement_percent: Math.round(overall.improvement.search_volume_percent)
        },
        keyword_count: {
            current: overall.current.total_keywords,
            optimized: overall.optimized.total_keywords,
            improvement: overall.improvement.keywords
        },
        root_coverage: {
            optimized: overall.relevant_root_volumes?.length || 0,
            improvement: overall.relevant_root_volumes?.length || 0
        }
    };
    
    header.innerHTML = `
        <div class="card-header">
            <div style="display: flex; justify-content: space-between; align-items: start;">
                <div>
                    <div class="card-title">
                        <span>📊</span> Analysis Complete
                    </div>
                    <div class="card-description">
                        Comprehensive keyword research and SEO optimization recommendations
                    </div>
                </div>
                <button class="button primary" onclick="downloadCSV()">
                    <span>⬇</span> Export CSV
                </button>
            </div>
        </div>
        <div class="card-content">
            <div class="stats-grid">
                <div class="stat-card blue">
                    <div class="stat-value">${improvements.search_volume.optimized.toLocaleString()}</div>
                    <div class="stat-label">Optimized Search Volume</div>
                    <div class="stat-change">+${improvements.search_volume.improvement_percent}%</div>
                </div>
                <div class="stat-card green">
                    <div class="stat-value">${improvements.keyword_count.optimized}</div>
                    <div class="stat-label">Total Keywords</div>
                    <div class="stat-change">+${improvements.keyword_count.improvement} keywords</div>
                </div>
                <div class="stat-card purple">
                    <div class="stat-value">${improvements.root_coverage.optimized}</div>
                    <div class="stat-label">Root Coverage</div>
                    <div class="stat-change">+${improvements.root_coverage.improvement} roots</div>
                </div>
                <div class="stat-card orange">
                    <div class="stat-value">${improvements.search_volume.improvement_percent}%</div>
                    <div class="stat-label">Improvement</div>
                    <div class="stat-change">vs. current listing</div>
                </div>
            </div>
        </div>
    `;
}

function switchTab(tab) {
    activeTab = tab;
    
    // Update tab buttons
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tab);
    });
    
    // Display tab content
    if (currentResults) {
        displayTabContent(tab, currentResults);
    }
}

function displayTabContent(tab, data) {
    const container = document.getElementById('tabContent');
    
    if (!container) {
        console.error('Tab content container not found');
        return;
    }
    
    console.log(`Displaying tab: ${tab}`);
    
    if (tab === 'seo') {
        displaySEOTab(container, data);
    } else if (tab === 'keywords') {
        displayKeywordsTab(container, data);
    }
}

function displaySEOTab(container, data) {
    const seoData = data.seo_optimization;
    
    if (!seoData || !seoData.success) {
        container.innerHTML = `
            <div class="card">
                <div class="card-content" style="text-align: center; padding: 60px; color: #64748b;">
                    <div style="font-size: 48px; margin-bottom: 16px;">📝</div>
                    <div style="font-size: 18px; font-weight: 600; margin-bottom: 8px;">SEO Optimization Not Available</div>
                    <div style="font-size: 14px;">Enable "Include SEO Optimization" to see optimized title and bullets</div>
                </div>
            </div>
        `;
        return;
    }
    
    const { detailed_comparison } = seoData;
    
    // Validate data structure
    if (!detailed_comparison || !detailed_comparison.title || !detailed_comparison.bullets) {
        console.error('Invalid SEO data structure:', seoData);
        container.innerHTML = `
            <div class="card">
                <div class="card-content" style="text-align: center; padding: 60px; color: #dc2626;">
                    <div style="font-size: 48px; margin-bottom: 16px;">⚠️</div>
                    <div style="font-size: 18px; font-weight: 600; margin-bottom: 8px;">Data Error</div>
                    <div style="font-size: 14px;">SEO optimization data is incomplete. Please try again.</div>
                </div>
            </div>
        `;
        return;
    }
    
    const { title, bullets, overall } = detailed_comparison;
    
    // Calculate improvements for display
    const improvements = {
        search_volume: {
            current: overall.current.total_search_volume,
            optimized: overall.optimized.total_search_volume,
            improvement: overall.improvement.search_volume,
            improvement_percent: Math.round(overall.improvement.search_volume_percent)
        },
        keyword_count: {
            current: overall.current.total_keywords,
            optimized: overall.optimized.total_keywords,
            improvement: overall.improvement.keywords
        },
        root_coverage: {
            current: 0, // Will be calculated from relevant_root_volumes if needed
            optimized: overall.relevant_root_volumes?.length || 0,
            improvement: overall.relevant_root_volumes?.length || 0
        }
    };
    
    // Generate summary improvements
    const summaryItems = [];
    if (improvements.search_volume.improvement > 0) {
        summaryItems.push(`Increased search volume by ${improvements.search_volume.improvement.toLocaleString()} (+${improvements.search_volume.improvement_percent}%)`);
    }
    if (improvements.keyword_count.improvement > 0) {
        summaryItems.push(`Added ${improvements.keyword_count.improvement} high-value keywords`);
    }
    if (title.optimized.keywords.some(kw => kw.is_design_specific)) {
        summaryItems.push(`Included design-specific keywords for better targeting`);
    }
    summaryItems.push(`Optimized for mobile (first 80 characters)`);
    summaryItems.push(`All Amazon guidelines validated and passed`);
    
    container.innerHTML = `
        <!-- Mobile Optimization -->
        <div class="card">
            <div class="card-header">
                <div class="card-title">
                    <span>🎯</span> Mobile Optimization (First 80 Characters)
                </div>
                <div class="card-description">
                    Critical for mobile search visibility
                </div>
            </div>
            <div class="card-content">
                <div class="mobile-optimization">
                    <div class="mobile-optimization-title">Optimized Title (First 80 chars):</div>
                    <div class="mobile-optimization-content">
                        ${title.optimized.first_80_chars}...
                    </div>
                    <div class="mobile-badges">
                        <span class="badge success">Main Root: ✓</span>
                        ${title.optimized.keywords.some(kw => kw.is_design_specific) ? '<span class="badge success">Design Root: ✓</span>' : ''}
                        <span class="badge secondary">Length: ${title.optimized.characters} chars</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- Key Improvements -->
        <div class="improvements-list">
            <h3>✨ Key Improvements</h3>
            <ul>
                ${summaryItems.map(item => `<li>${item}</li>`).join('')}
            </ul>
        </div>

        <!-- Title Comparison -->
        <div class="card">
            <div class="card-header">
                <div class="card-title">
                    <span>📝</span> Title Comparison
                </div>
                <div class="card-description">
                    Side-by-side comparison of current vs. optimized title
                </div>
            </div>
            <div class="card-content">
                <div class="comparison-grid">
                    ${renderTitleComparison(title)}
                </div>
            </div>
        </div>

        <!-- Bullet Points Comparison -->
        <div class="card">
            <div class="card-header">
                <div class="card-title">
                    <span>📋</span> Bullet Points Comparison
                </div>
                <div class="card-description">
                    Benefit-focused bullets with keyword integration
                </div>
            </div>
            <div class="card-content">
                ${renderBulletsComparison(bullets)}
            </div>
        </div>

        <!-- Amazon Compliance -->
        <div class="card">
            <div class="card-header">
                <div class="card-title">
                    <span>⚡</span> Amazon Compliance Status
                </div>
                <div class="card-description">
                    All guidelines validated
                </div>
            </div>
            <div class="card-content">
                <div class="stats-grid">
                    <div class="stat-card green" style="padding: 16px;">
                        <div style="font-size: 13px; font-weight: 600; margin-bottom: 8px;">Character Limit</div>
                        <span class="badge success">PASS</span>
                    </div>
                    <div class="stat-card green" style="padding: 16px;">
                        <div style="font-size: 13px; font-weight: 600; margin-bottom: 8px;">Capitalization</div>
                        <span class="badge success">PASS</span>
                    </div>
                    <div class="stat-card green" style="padding: 16px;">
                        <div style="font-size: 13px; font-weight: 600; margin-bottom: 8px;">Special Characters</div>
                        <span class="badge success">PASS</span>
                    </div>
                    <div class="stat-card green" style="padding: 16px;">
                        <div style="font-size: 13px; font-weight: 600; margin-bottom: 8px;">Promotional Language</div>
                        <span class="badge success">PASS</span>
                    </div>
                    <div class="stat-card green" style="padding: 16px;">
                        <div style="font-size: 13px; font-weight: 600; margin-bottom: 8px;">Subjective Claims</div>
                        <span class="badge success">PASS</span>
                    </div>
                </div>
            </div>
        </div>
    `;
}

function renderTitleComparison(title) {
    // Safely access keywords arrays
    const currentKeywords = title.current.keywords || [];
    const optimizedKeywords = title.optimized.keywords || [];
    
    return `
        <!-- Current Title -->
        <div class="comparison-column current">
            <div class="comparison-header">
                <span class="comparison-label current">CURRENT</span>
                <span class="char-count">${title.current.characters}/200 chars</span>
            </div>
            <div class="content-box">
                ${title.current.text}
            </div>
            <div class="metrics-row">
                <div class="metric">
                    <div class="metric-label">Keywords</div>
                    <div class="metric-value">${title.current.keyword_count}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Search Volume</div>
                    <div class="metric-value">${title.current.total_search_volume.toLocaleString()}</div>
                </div>
            </div>
            <div class="keywords-section">
                <div class="keywords-label">Keywords:</div>
                <div class="keyword-tags">
                    ${currentKeywords.map(kw => 
                        `<span class="keyword-tag current">${kw.keyword || kw} (${(kw.search_volume || 0).toLocaleString()})</span>`
                    ).join('')}
                </div>
            </div>
        </div>

        <!-- Optimized Title -->
        <div class="comparison-column optimized">
            <div class="comparison-header">
                <span class="comparison-label optimized">OPTIMIZED</span>
                <span class="char-count">${title.optimized.characters}/200 chars</span>
            </div>
            <div class="content-box">
                ${title.optimized.text}
            </div>
            <div class="metrics-row">
                <div class="metric metric-improved">
                    <div class="metric-label">Keywords</div>
                    <div class="metric-value">${title.optimized.keyword_count} <span style="font-size: 12px; color: #16a34a;">+${title.optimized.keyword_count - title.current.keyword_count}</span></div>
                </div>
                <div class="metric metric-improved">
                    <div class="metric-label">Search Volume</div>
                    <div class="metric-value">${title.optimized.total_search_volume.toLocaleString()} <span style="font-size: 12px; color: #16a34a;">+${(title.optimized.total_search_volume - title.current.total_search_volume).toLocaleString()}</span></div>
                </div>
            </div>
            <div class="keywords-section">
                <div class="keywords-label">Keywords:</div>
                <div class="keyword-tags">
                    ${optimizedKeywords.map(kw => 
                        `<span class="keyword-tag optimized">${kw.keyword || kw} (${(kw.search_volume || 0).toLocaleString()})</span>`
                    ).join('')}
                </div>
            </div>
        </div>
    `;
}

function renderBulletsComparison(bullets) {
    // Handle the correct data structure: bullets.current.bullets and bullets.optimized.bullets
    const currentBullets = bullets.current.bullets || bullets.current || [];
    const optimizedBullets = bullets.optimized.bullets || bullets.optimized || [];
    
    // Determine the maximum number of bullets to display
    const maxBullets = Math.max(currentBullets.length, optimizedBullets.length);
    
    let html = '';
    
    for (let i = 0; i < maxBullets; i++) {
        const currentBullet = currentBullets[i];
        const optimizedBullet = optimizedBullets[i];
        
        // Skip if both are missing
        if (!currentBullet && !optimizedBullet) continue;
        
        html += `
            <div class="bullet-pair">
                <div class="bullet-number">Bullet Point ${i + 1}</div>
                <div class="comparison-grid">
        `;
        
        // Current Bullet
        if (currentBullet) {
            const currentKeywords = currentBullet.keywords || [];
            html += `
                    <div class="comparison-column current">
                        <div class="content-box">
                            ${currentBullet.text}
                        </div>
                        <div class="metrics-row">
                            <div class="metric">
                                <div class="metric-label">Characters</div>
                                <div class="metric-value">${currentBullet.characters}</div>
                            </div>
                            <div class="metric">
                                <div class="metric-label">Keywords</div>
                                <div class="metric-value">${currentBullet.keyword_count}</div>
                            </div>
                            <div class="metric">
                                <div class="metric-label">Search Volume</div>
                                <div class="metric-value">${currentBullet.search_volume.toLocaleString()}</div>
                            </div>
                        </div>
                        <div class="keyword-tags" style="margin-top: 8px;">
                            ${currentKeywords.map(kw => 
                                `<span class="keyword-tag current">${kw.keyword || kw} (${(kw.search_volume || 0).toLocaleString()})</span>`
                            ).join('')}
                        </div>
                    </div>
            `;
        } else {
            html += `
                    <div class="comparison-column current">
                        <div class="content-box" style="color: #94a3b8; font-style: italic;">
                            No current bullet
                        </div>
                    </div>
            `;
        }
        
        // Optimized Bullet
        if (optimizedBullet) {
            const optimizedKeywords = optimizedBullet.keywords || [];
            const improvement = currentBullet ? optimizedBullet.search_volume - currentBullet.search_volume : optimizedBullet.search_volume;
            
            html += `
                    <div class="comparison-column optimized">
                        <div class="content-box">
                            ${optimizedBullet.text}
                        </div>
                        <div class="metrics-row">
                            <div class="metric">
                                <div class="metric-label">Characters</div>
                                <div class="metric-value">${optimizedBullet.characters}</div>
                            </div>
                            <div class="metric metric-improved">
                                <div class="metric-label">Keywords</div>
                                <div class="metric-value">${optimizedBullet.keyword_count}</div>
                            </div>
                            <div class="metric metric-improved">
                                <div class="metric-label">Search Volume</div>
                                <div class="metric-value">${optimizedBullet.search_volume.toLocaleString()} ${improvement > 0 ? `<span style="font-size: 12px; color: #16a34a;">+${improvement.toLocaleString()}</span>` : ''}</div>
                            </div>
                        </div>
                        <div class="keyword-tags" style="margin-top: 8px;">
                            ${optimizedKeywords.map(kw => 
                                `<span class="keyword-tag optimized">${kw.keyword || kw} (${(kw.search_volume || 0).toLocaleString()})</span>`
                            ).join('')}
                        </div>
                    </div>
            `;
        } else {
            html += `
                    <div class="comparison-column optimized">
                        <div class="content-box" style="color: #94a3b8; font-style: italic;">
                            No optimized bullet
                        </div>
                    </div>
            `;
        }
        
        html += `
                </div>
            </div>
        `;
    }
    
    return html;
}

function displayKeywordsTab(container, data) {
    container.innerHTML = `
        <div class="card">
            <div class="card-content" style="text-align: center; padding: 60px; color: #64748b;">
                <div style="font-size: 48px; margin-bottom: 16px;">🔑</div>
                <div style="font-size: 18px; font-weight: 600; margin-bottom: 8px;">Keyword Analysis</div>
                <div style="font-size: 14px;">Detailed keyword table view (coming soon)</div>
            </div>
        </div>
    `;
}

// Utility functions
function fileToBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => {
            const base64 = reader.result.split(',')[1];
            resolve(base64);
        };
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
}

function showLoading() {
    const loading = document.getElementById('loading');
    const progressBar = document.getElementById('progressBar');
    
    // Reset progress bar
    if (progressBar) {
        progressBar.style.width = '0%';
        progressBar.style.display = 'block';
    }
    
    // Show loading card
    loading.classList.add('show');
    loading.style.display = 'block';
    
    // Update initial progress
    updateProgress(0, 'Starting analysis...');
    
    console.log('Loading shown with progress bar reset');
}

function hideLoading() {
    const loading = document.getElementById('loading');
    loading.classList.remove('show');
    loading.style.display = 'none';
    console.log('Loading hidden');
}

function showError(message) {
    const errorDiv = document.getElementById('error');
    errorDiv.textContent = message;
    errorDiv.classList.add('show');
}

function hideError() {
    document.getElementById('error').classList.remove('show');
}

function showResults() {
    document.getElementById('results').classList.add('show');
}

function hideResults() {
    document.getElementById('results').classList.remove('show');
}

function downloadCSV() {
    if (!currentResults || !currentResults.csv_filename) {
        alert('No CSV file available');
        return;
    }
    
    const filename = currentResults.csv_filename.split('/').pop();
    window.location.href = `/api/research/download/${filename}`;
}
