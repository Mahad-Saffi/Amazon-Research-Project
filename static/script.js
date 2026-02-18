let currentProgress = 0;
let targetProgress = 0;
let progressAnimationFrame = null;

document.getElementById('researchForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    // Hide previous results/errors
    document.getElementById('results').style.display = 'none';
    document.getElementById('error').style.display = 'none';
    
    // Show loading
    document.getElementById('loading').style.display = 'block';
    document.getElementById('submitBtn').disabled = true;
    
    // Reset progress
    currentProgress = 0;
    targetProgress = 0;
    updateProgress(0, 'Starting...', 'Preparing to analyze product');
    
    // Generate request ID
    const requestId = 'req_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    
    // Start smooth progress animation
    startSmoothProgress();
    
    try {
        // Read files as base64
        const designFile = document.getElementById('designCsv').files[0];
        const revenueFile = document.getElementById('revenueCsv').files[0];
        
        const designBase64 = await fileToBase64(designFile);
        const revenueBase64 = await fileToBase64(revenueFile);
        
        // Create WebSocket connection
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/api/research/ws`;
        const ws = new WebSocket(wsUrl);
        
        // Handle WebSocket open
        ws.onopen = () => {
            console.log('WebSocket connected');
            // Send data to server
            ws.send(JSON.stringify({
                design_csv: designBase64,
                revenue_csv: revenueBase64,
                asin_or_url: document.getElementById('asinUrl').value,
                marketplace: document.getElementById('marketplace').value,
                use_mock_scraper: document.getElementById('useMock').checked,
                use_direct_verification: document.getElementById('useDirectVerification').checked,
                include_seo_optimization: document.getElementById('includeSeoOptimization').checked,
                rank_threshold: parseInt(document.getElementById('rankThreshold').value) || 11,
                request_id: requestId
            }));
        };
        
        // Handle WebSocket messages
        ws.onmessage = async (event) => {
            const message = JSON.parse(event.data);
            
            if (message.type === 'progress') {
                targetProgress = message.percent;
                updateProgress(message.percent, message.message, getProgressDetails(message.percent));
            } else if (message.type === 'complete') {
                stopSmoothProgress();
                targetProgress = 100;
                updateProgress(100, 'Complete!', 'Analysis finished successfully');
                
                // Small delay to show 100%
                await new Promise(resolve => setTimeout(resolve, 500));
                
                const data = message.data;
                if (data.success) {
                    displayResults(data);
                } else {
                    throw new Error(data.error || 'Unknown error');
                }
                
                ws.close();
            } else if (message.type === 'error') {
                throw new Error(message.error);
            }
        };
        
        // Handle WebSocket errors
        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            throw new Error('WebSocket connection failed');
        };
        
        // Handle WebSocket close
        ws.onclose = () => {
            console.log('WebSocket closed');
            stopSmoothProgress();
            document.getElementById('loading').style.display = 'none';
            document.getElementById('submitBtn').disabled = false;
        };
        
    } catch (error) {
        stopSmoothProgress();
        document.getElementById('error').textContent = `Error: ${error.message}`;
        document.getElementById('error').style.display = 'block';
        document.getElementById('loading').style.display = 'none';
        document.getElementById('submitBtn').disabled = false;
    }
});

// Helper function to convert file to base64
function fileToBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => {
            // Remove the data:*/*;base64, prefix
            const base64 = reader.result.split(',')[1];
            resolve(base64);
        };
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
}

function startSmoothProgress() {
    function animate() {
        if (currentProgress < targetProgress) {
            // Smooth interpolation
            const diff = targetProgress - currentProgress;
            currentProgress += diff * 0.1; // Smooth catch-up
            
            if (Math.abs(targetProgress - currentProgress) < 0.5) {
                currentProgress = targetProgress;
            }
            
            const progressBar = document.getElementById('progressBar');
            progressBar.style.width = currentProgress + '%';
            progressBar.textContent = Math.round(currentProgress) + '%';
        }
        
        progressAnimationFrame = requestAnimationFrame(animate);
    }
    animate();
}

function stopSmoothProgress() {
    if (progressAnimationFrame) {
        cancelAnimationFrame(progressAnimationFrame);
        progressAnimationFrame = null;
    }
}

function updateProgress(percent, message, details) {
    targetProgress = percent;
    document.getElementById('progressMessage').textContent = message;
    if (details) {
        document.getElementById('progressDetails').textContent = details;
    }
}

function getProgressDetails(percent) {
    if (percent < 15) return 'Reading and parsing CSV files...';
    if (percent < 25) return 'Removing duplicate keywords...';
    if (percent < 30) return 'Calculating relevancy scores...';
    if (percent < 33) return 'Extracting root keywords from data...';
    if (percent < 36) return 'Detecting branded keywords with AI...';
    if (percent < 45) return 'Filtering out branded keywords...';
    if (percent < 55) return 'Fetching product data from Amazon...';
    if (percent < 65) return 'Analyzing product with AI...';
    if (percent < 90) return 'Evaluating keyword relevance (this may take a moment)...';
    if (percent < 95) return 'Categorizing keywords into relevance levels...';
    if (percent < 100) return 'Saving results to file...';
    return 'Complete!';
}

let allEvaluations = [];
let currentSort = 'relevance';
let currentFilter = 'all';
let currentCategoryFilter = 'all';
let lastCsvFilename = '';

function displayResults(data) {
    const metadata = data.metadata || {};
    allEvaluations = data.keyword_evaluations || [];
    const summary = data.product_summary || [];
    lastCsvFilename = data.csv_filename || '';
    
    // Show saved file info or warning
    const savedFileDiv = document.getElementById('savedFile');
    if (data.csv_filename) {
        let message = `✓ Results saved to: results/${data.csv_filename}`;
        if (data.log_file) {
            message += `\n📋 Log file: ${data.log_file}`;
        }
        savedFileDiv.textContent = message;
        savedFileDiv.style.display = 'block';
        savedFileDiv.style.borderColor = 'green';
        savedFileDiv.style.background = '#efe';
        savedFileDiv.style.color = 'green';
        savedFileDiv.style.whiteSpace = 'pre-line';
    } else if (metadata.warning) {
        savedFileDiv.textContent = `⚠ Warning: ${metadata.warning}`;
        savedFileDiv.style.display = 'block';
        savedFileDiv.style.borderColor = 'orange';
        savedFileDiv.style.background = '#fff3cd';
        savedFileDiv.style.color = '#856404';
    }
    
    // Display metadata
    let metadataHtml = `
        <div class="metadata-item"><strong>ASIN/URL:</strong> ${escapeHtml(metadata.asin_or_url || 'N/A')}</div>
        <div class="metadata-item"><strong>Marketplace:</strong> ${escapeHtml(metadata.marketplace || 'N/A')}</div>
        <div class="metadata-item"><strong>Keywords Evaluated:</strong> ${metadata.keywords_final || 0}</div>
        <div class="metadata-item"><strong>Branded Keywords Removed:</strong> ${metadata.branded_keywords_removed || 0}</div>
        <div class="metadata-item"><strong>Design Rows Processed:</strong> ${metadata.design_rows_filtered || 0}</div>
        <div class="metadata-item"><strong>Revenue Rows Processed:</strong> ${metadata.revenue_rows_filtered || 0}</div>
        <div class="metadata-item"><strong>Top Root Keywords:</strong> ${(metadata.top_10_roots || []).join(', ')}</div>
    `;
    
    // Show warning if present
    if (metadata.warning) {
        metadataHtml += `<div class="metadata-item" style="color: orange;"><strong>⚠ Warning:</strong> ${escapeHtml(metadata.warning)}</div>`;
    }
    
    document.getElementById('metadata').innerHTML = metadataHtml;
    
    // Display product summary
    if (summary.length > 0) {
        const summaryHtml = `
            <h3>Product Summary</h3>
            <ul>
                ${summary.map(item => `<li>${escapeHtml(item)}</li>`).join('')}
            </ul>
        `;
        document.getElementById('summary').innerHTML = summaryHtml;
        document.getElementById('summary').style.display = 'block';
    } else {
        document.getElementById('summary').style.display = 'none';
    }
    
    // Display SEO Optimization if available
    if (data.seo_optimization && data.seo_optimization.success) {
        displaySEOOptimization(data.seo_optimization);
    }
    
    // Set up event listeners for sorting and filtering
    document.getElementById('sortBy').addEventListener('change', function(e) {
        currentSort = e.target.value;
        renderTable();
    });
    
    document.getElementById('filterBrand').addEventListener('change', function(e) {
        currentFilter = e.target.value;
        renderTable();
    });
    
    document.getElementById('filterCategory').addEventListener('change', function(e) {
        currentCategoryFilter = e.target.value;
        renderTable();
    });
    
    // Set up download button
    document.getElementById('downloadCsvBtn').addEventListener('click', downloadCsv);
    
    // Initial render
    renderTable();
    
    // Show results
    document.getElementById('results').style.display = 'block';
    
    // Scroll to results
    document.getElementById('results').scrollIntoView({ behavior: 'smooth' });
}

function downloadCsv() {
    if (!lastCsvFilename) {
        alert('No CSV file available for download');
        return;
    }
    
    // Extract just the filename from the path
    const filename = lastCsvFilename.split('/').pop();
    
    // Create download link
    const link = document.createElement('a');
    link.href = `/api/research/download/${encodeURIComponent(filename)}`;
    link.download = filename;
    link.style.visibility = 'hidden';
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

function renderTable() {
    if (allEvaluations.length === 0) {
        document.getElementById('tableHead').innerHTML = '';
        document.getElementById('tableBody').innerHTML = '<tr><td class="no-data">No data available</td></tr>';
        document.getElementById('resultCount').textContent = '0 results';
        return;
    }
    
    // Filter data
    let filteredData = [...allEvaluations];
    
    // Brand filter
    if (currentFilter === 'branded') {
        filteredData = filteredData.filter(row => row.category === 'branded');
    } else if (currentFilter === 'non-branded') {
        filteredData = filteredData.filter(row => row.category !== 'branded');
    }
    
    // Category filter
    if (currentCategoryFilter !== 'all') {
        filteredData = filteredData.filter(row => row.category === currentCategoryFilter);
    }
    
    // Sort data
    filteredData.sort((a, b) => {
        if (currentSort === 'relevance') {
            // For branded keywords (relevance_score = 0), sort by search volume instead
            const scoreA = a.relevance_score || 0;
            const scoreB = b.relevance_score || 0;
            if (scoreA === 0 && scoreB === 0) {
                return parseInt(b['Search Volume'] || 0) - parseInt(a['Search Volume'] || 0);
            }
            return scoreB - scoreA;
        } else if (currentSort === 'relevance-asc') {
            const scoreA = a.relevance_score || 0;
            const scoreB = b.relevance_score || 0;
            if (scoreA === 0 && scoreB === 0) {
                return parseInt(a['Search Volume'] || 0) - parseInt(b['Search Volume'] || 0);
            }
            return scoreA - scoreB;
        } else if (currentSort === 'volume') {
            return parseInt(b['Search Volume'] || 0) - parseInt(a['Search Volume'] || 0);
        } else if (currentSort === 'volume-asc') {
            return parseInt(a['Search Volume'] || 0) - parseInt(b['Search Volume'] || 0);
        }
        return 0;
    });
    
    // Update result count
    document.getElementById('resultCount').textContent = `${filteredData.length} results`;
    
    if (filteredData.length === 0) {
        document.getElementById('tableHead').innerHTML = '';
        document.getElementById('tableBody').innerHTML = '<tr><td class="no-data">No results match the filter</td></tr>';
        return;
    }
    
    // Get columns
    const columns = Object.keys(filteredData[0]);
    
    // Create table header
    const headerHtml = '<tr>' + columns.map(col => `<th>${escapeHtml(col)}</th>`).join('') + '</tr>';
    document.getElementById('tableHead').innerHTML = headerHtml;
    
    // Create table body
    const bodyHtml = filteredData.map(row => {
        return '<tr>' + columns.map(col => {
            const value = row[col];
            
            // Special formatting for category
            if (col === 'category') {
                const className = `category-${value}`;
                const displayValue = value ? value.replace('_', '-').toUpperCase() : '';
                return `<td><span class="${className}">${escapeHtml(displayValue)}</span></td>`;
            }
            
            // Special formatting for tag (language tag)
            if (col === 'tag') {
                if (value && value !== 'null' && value !== null) {
                    return `<td><span class="language-tag">${escapeHtml(String(value).toUpperCase())}</span></td>`;
                }
                return `<td></td>`;
            }
            
            // Special formatting for relevance_score (show N/A for branded keywords)
            if (col === 'relevance_score' && value === 0 && row.category === 'branded') {
                return `<td style="color: #999;">N/A</td>`;
            }
            
            return `<td>${escapeHtml(String(value || ''))}</td>`;
        }).join('') + '</tr>';
    }).join('');
    document.getElementById('tableBody').innerHTML = bodyHtml;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}


function displaySEOOptimization(seoData) {
    // Create SEO section if it doesn't exist
    let seoSection = document.getElementById('seoOptimization');
    if (!seoSection) {
        seoSection = document.createElement('div');
        seoSection.id = 'seoOptimization';
        seoSection.className = 'seo-optimization';
        
        // Insert before keyword evaluations
        const results = document.getElementById('results');
        const keywordHeading = results.querySelector('h2');
        results.insertBefore(seoSection, keywordHeading);
    }
    
    const comparison = seoData.detailed_comparison;
    
    let html = `
        <h2>📈 SEO Optimization</h2>
        
        <div class="seo-improvements">
            <h3>Improvements</h3>
            <div class="improvement-stats">
                <div class="stat">
                    <span class="stat-label">Search Volume</span>
                    <span class="stat-value">+${seoData.improvements.search_volume.improvement.toLocaleString()} (${seoData.improvements.search_volume.improvement_percent}%)</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Keywords</span>
                    <span class="stat-value">+${seoData.improvements.keyword_count.improvement}</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Root Coverage</span>
                    <span class="stat-value">+${seoData.improvements.root_coverage.improvement} roots</span>
                </div>
            </div>
        </div>
        
        <div class="seo-comparison">
            <h3>Title Comparison</h3>
            <div class="comparison-grid">
                <div class="comparison-column current">
                    <h4>Current Title</h4>
                    <div class="content-box">
                        <p>${escapeHtml(comparison.title.current.text)}</p>
                        <div class="metrics">
                            <span>Characters: ${comparison.title.current.characters}</span>
                            <span>Keywords: ${comparison.title.current.keyword_count}</span>
                            <span>Search Volume: ${comparison.title.current.total_search_volume.toLocaleString()}</span>
                        </div>
                        ${comparison.title.current.keywords.length > 0 ? `
                            <div class="keywords-list">
                                <strong>Keywords:</strong>
                                ${comparison.title.current.keywords.map(kw => `<span class="keyword-tag">${escapeHtml(kw.display)}</span>`).join('')}
                            </div>
                        ` : ''}
                        ${comparison.title.current.duplicates.length > 0 ? `
                            <div class="duplicates-warning">
                                ⚠️ Duplicates: ${comparison.title.current.duplicates.map(d => `${d.keyword} (${d.count}x)`).join(', ')}
                            </div>
                        ` : ''}
                    </div>
                </div>
                
                <div class="comparison-column optimized">
                    <h4>Optimized Title</h4>
                    <div class="content-box">
                        <p>${escapeHtml(comparison.title.optimized.text)}</p>
                        <div class="metrics">
                            <span>Characters: ${comparison.title.optimized.characters}</span>
                            <span>Keywords: ${comparison.title.optimized.keyword_count}</span>
                            <span>Search Volume: ${comparison.title.optimized.total_search_volume.toLocaleString()}</span>
                        </div>
                        ${comparison.title.optimized.keywords.length > 0 ? `
                            <div class="keywords-list">
                                <strong>Keywords:</strong>
                                ${comparison.title.optimized.keywords.map(kw => `<span class="keyword-tag ${kw.is_design_specific ? 'design-specific' : ''}">${escapeHtml(kw.display)}</span>`).join('')}
                            </div>
                        ` : ''}
                        ${comparison.title.optimized.duplicates.length > 0 ? `
                            <div class="duplicates-warning">
                                ⚠️ Duplicates: ${comparison.title.optimized.duplicates.map(d => `${d.keyword} (${d.count}x)`).join(', ')}
                            </div>
                        ` : ''}
                    </div>
                </div>
            </div>
            
            <h3>Bullet Points Comparison</h3>
            <div class="comparison-grid">
                <div class="comparison-column current">
                    <h4>Current Bullets</h4>
                    ${comparison.bullets.current.bullets.map(bullet => `
                        <div class="bullet-box">
                            <p><strong>${bullet.bullet_number}.</strong> ${escapeHtml(bullet.text)}</p>
                            <div class="metrics">
                                <span>Characters: ${bullet.characters}</span>
                                <span>Keywords: ${bullet.keyword_count}</span>
                                <span>Search Volume: ${bullet.search_volume.toLocaleString()}</span>
                            </div>
                            ${bullet.keywords.length > 0 ? `
                                <div class="keywords-list">
                                    ${bullet.keywords.map(kw => `<span class="keyword-tag">${escapeHtml(kw.display)}</span>`).join('')}
                                </div>
                            ` : ''}
                        </div>
                    `).join('')}
                    <div class="total-metrics">
                        <strong>Total Search Volume: ${comparison.bullets.current.total_search_volume.toLocaleString()}</strong>
                    </div>
                </div>
                
                <div class="comparison-column optimized">
                    <h4>Optimized Bullets</h4>
                    ${comparison.bullets.optimized.bullets.map(bullet => `
                        <div class="bullet-box">
                            <p><strong>${bullet.bullet_number}.</strong> ${escapeHtml(bullet.text)}</p>
                            <div class="metrics">
                                <span>Characters: ${bullet.characters}</span>
                                <span>Keywords: ${bullet.keyword_count}</span>
                                <span>Search Volume: ${bullet.search_volume.toLocaleString()}</span>
                            </div>
                            ${bullet.keywords.length > 0 ? `
                                <div class="keywords-list">
                                    ${bullet.keywords.map(kw => `<span class="keyword-tag ${kw.is_design_specific ? 'design-specific' : ''}">${escapeHtml(kw.display)}</span>`).join('')}
                                </div>
                            ` : ''}
                        </div>
                    `).join('')}
                    <div class="total-metrics">
                        <strong>Total Search Volume: ${comparison.bullets.optimized.total_search_volume.toLocaleString()}</strong>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    seoSection.innerHTML = html;
    seoSection.style.display = 'block';
}
