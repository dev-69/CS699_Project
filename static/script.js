// We wrap the whole script in this listener to ensure the DOM is ready
document.addEventListener('DOMContentLoaded', () => {

    // --- Global variables to track search state ---
    let currentPage = 1;
    let currentJobTitle = '';
    let currentCompanyName = '';
    let currentLocation = '';
    
    // A set for quick lookup of saved job IDs
    let savedJobIds = new Set();

    // --- Get DOM elements ---
    const searchForm = document.getElementById('search-form');
    const resultsContainer = document.getElementById('results-container');
    const loadingSpinner = document.getElementById('loading');
    const loadMoreBtn = document.getElementById('load-more-btn');

    /**
     * NEW: Handles clicking the "Save Job" button
     */
    async function handleSaveClick(event) {
        // Stop the click from navigating (if it was an <a> tag)
        event.preventDefault(); 
        
        const button = event.currentTarget;
        const jobId = button.dataset.jobId;

        if (!jobId) return;

        try {
            const response = await fetch('/toggle_save', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ job_id: jobId }),
            });

            if (!response.ok) {
                alert('Error saving job. Please try again.');
                return;
            }

            const result = await response.json();

            // Toggle the button's appearance
            if (result.status === 'saved') {
                button.classList.add('btn-success');
                button.classList.remove('btn-outline-success');
                button.textContent = 'Saved';
                savedJobIds.add(parseInt(jobId)); // Add to our local set
            } else if (result.status === 'unsaved') {
                button.classList.remove('btn-success');
                button.classList.add('btn-outline-success');
                button.textContent = 'Save';
                savedJobIds.delete(parseInt(jobId)); // Remove from our local set
            }

        } catch (error) {
            console.error('Error in handleSaveClick:', error);
            alert('An error occurred. Please check the console.');
        }
    }

    /**
     * Main function to fetch jobs from the backend
     */
    async function fetchAndDisplayJobs(isNewSearch = false) {
        
        if (isNewSearch) {
            currentPage = 1;
            resultsContainer.innerHTML = '';
        }

        loadingSpinner.classList.remove('d-none');
        loadMoreBtn.classList.add('d-none');

        try {
            const response = await fetch('/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    job_title: currentJobTitle,
                    company_name: currentCompanyName,
                    location: currentLocation,
                    page: currentPage
                }),
            });

            loadingSpinner.classList.add('d-none');

            if (!response.ok) {
                // ... (error handling) ...
                return;
            }

            const data = await response.json();
            const jobs = data.jobs;

            // --- NEW: Update our local set of saved jobs ---
            if (isNewSearch) {
                savedJobIds = new Set(data.saved_job_ids || []);
            }
            // --- END NEW ---

            if (jobs.length === 0 && isNewSearch) {
                resultsContainer.innerHTML = `<div class="col-12"><div class="alert alert-info">No jobs found for your search criteria.</div></div>`;
                return;
            }

            // --- We will build the cards and attach listeners separately ---
            const fragment = document.createDocumentFragment();

            jobs.forEach(job => {
                const companyName = job.company || 'N/A';
                let domain = companyName.toLowerCase().replace(" ", "").replace("inc.", "").replace(".com", "").replace("llc", "").replace(",", "");
                const logoUrl = `https://www.google.com/s2/favicons?domain=${domain}.com&sz=64`;
                
                const posted = job.date_posted || 'N/A';
                const applicants = job.num_applicants || 'N/A';

                // --- NEW: Check if this job is saved ---
                const isSaved = savedJobIds.has(job.id);
                const saveBtnClass = isSaved ? 'btn-success' : 'btn-outline-success';
                const saveBtnText = isSaved ? 'Saved' : 'Save';
                // --- END NEW ---

                // Create the card element
                const cardCol = document.createElement('div');
                cardCol.className = 'col-md-6 col-lg-4';
                
                cardCol.innerHTML = `
                    <div class="card h-100 job-card">
                        <div class="card-body d-flex flex-column">
                            
                            <div class="d-flex align-items-center mb-2">
                                <img src="${logoUrl}" alt="${companyName} logo" class="me-2" style="width: 32px; height: 32px; border-radius: 4px; object-fit: contain; background: #eee;">
                                <div style="flex: 1;">
                                    <h5 class="card-title mb-0">${job.title || 'No Title'}</h5>
                                    <h6 class="card-subtitle mt-1 text-muted">${companyName} - ${job.location || 'N/A'}</h6>
                                </div>
                            </div>
                            
                            <div class="d-flex justify-content-between text-muted small mb-2">
                                <span><svg...></svg> Posted: ${posted}</span>
                                ${(applicants !== 'N/A' && applicants) ? `<span><svg...></svg> ${applicants}</span>` : ''}
                            </div>
                            
                            <p class="card-text small">${(job.description || '').substring(0, 100)}...</p>
                            
                            <div class="mt-auto pt-2 d-flex justify-content-between align-items-center">
                                <div>
                                    <span class="badge bg-secondary me-1">${job.site || 'N/A'}</span>
                                    <span class="badge bg-light text-dark">${job.job_type || 'N/A'}</span>
                                </div>
                                <div class="btn-group">
                                    <button class="btn btn-sm ${saveBtnClass} btn-save" data-job-id="${job.id}">
                                        ${saveBtnText}
                                    </button>
                                    <a href="${job.job_url}" target="_blank" class="btn btn-sm btn-primary">View Job</a>
                                </div>
                            </div>
                            </div>
                    </div>
                `;
                
                // Add the new card to our fragment
                fragment.appendChild(cardCol);
            });

            // Append all new cards to the DOM at once
            resultsContainer.appendChild(fragment);

            // --- NEW: Attach all event listeners after adding to DOM ---
            // This is more efficient than adding one inside the loop
            document.querySelectorAll('.btn-save').forEach(button => {
                // We must remove any old listener before adding a new one
                button.removeEventListener('click', handleSaveClick);
                button.addEventListener('click', handleSaveClick);
            });

            // --- Pagination Button Logic (unchanged) ---
            if (data.current_page < data.total_pages) {
                loadMoreBtn.classList.remove('d-none');
            } else {
                loadMoreBtn.classList.add('d-none');
            }

        } catch (error) {
            loadingSpinner.classList.add('d-none');
            loadMoreBtn.classList.add('d-none');
            resultsContainer.innerHTML = `<div class="col-12"><div class="alert alert-danger">An unexpected error occurred. Please check the console.</div></div>`;
            console.error('Error:', error);
        }
    }

    // --- Event Listener for the Search Form ---
    searchForm.addEventListener('submit', async function(event) {
        event.preventDefault();
        
        currentJobTitle = document.getElementById('job_title').value;
        currentCompanyName = document.getElementById('company_name').value;
        currentLocation = document.getElementById('location').value;
        
        await fetchAndDisplayJobs(true);
    });

    // --- Event Listener for the "Load More" Button ---
    loadMoreBtn.addEventListener('click', async function(event) {
        event.preventDefault();
        
        currentPage++;
        await fetchAndDisplayJobs(false);
    });

});