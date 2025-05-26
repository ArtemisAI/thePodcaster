const API_BASE_URL = '/api'; // Assuming the backend is served on the same domain or proxied

document.addEventListener('DOMContentLoaded', () => {
    showView('uploadView'); // Default view
    document.getElementById('uploadForm').addEventListener('submit', handleUploadAndProcess);
    // Add event listeners for nav buttons if not already handled by onclick
    // Example: document.querySelector('nav button[onclick*="uploadView"]').addEventListener('click', () => showView('uploadView'));
});

function showView(viewId) {
    document.querySelectorAll('.view').forEach(view => {
        view.style.display = 'none';
    });
    const targetView = document.getElementById(viewId);
    if (targetView) {
        targetView.style.display = 'block';
    } else {
        console.error(`View with ID ${viewId} not found.`);
    }
}

async function handleUploadAndProcess(event) {
    event.preventDefault();
    const form = event.target;
    const formData = new FormData();
    const mainTrackInput = document.getElementById('mainTrack');
    const introTrackInput = document.getElementById('introTrack');
    const outroTrackInput = document.getElementById('outroTrack');

    const mainTrack = mainTrackInput.files[0];
    const introTrack = introTrackInput.files[0];
    const outroTrack = outroTrackInput.files[0];

    if (!mainTrack) {
        alert("Main audio track is required!");
        return;
    }

    formData.append('main_track', mainTrack, mainTrack.name);
    if (introTrack) formData.append('intro', introTrack, introTrack.name);
    if (outroTrack) formData.append('outro', outroTrack, outroTrack.name);

    const uploadResponseDiv = document.getElementById('uploadResponse');
    uploadResponseDiv.className = ''; // Clear previous classes
    uploadResponseDiv.textContent = 'Uploading audio files...';

    try {
        const uploadRes = await fetch(`${API_BASE_URL}/audio/upload`, {
            method: 'POST',
            body: formData,
        });

        const uploadData = await uploadRes.json();

        if (!uploadRes.ok) {
            throw new Error(uploadData.detail || `Upload failed with status: ${uploadRes.status}`);
        }
        
        uploadResponseDiv.textContent = `Upload successful! Session ID: ${uploadData.upload_session_id}. Starting processing...`;
        uploadResponseDiv.classList.add('success');

        const processRes = await fetch(`${API_BASE_URL}/audio/process/${uploadData.upload_session_id}`, {
            method: 'POST',
        });
        const processData = await processRes.json();

        if (!processRes.ok) {
            throw new Error(processData.detail || `Processing failed with status: ${processRes.status}`);
        }

        uploadResponseDiv.textContent = `Processing started! Job ID: ${processData.job_id}. You can check its status in the 'View Jobs' tab.`;
        uploadResponseDiv.classList.add('success');
        form.reset(); // Clear the form

    } catch (error) {
        console.error('Error during upload/process:', error);
        uploadResponseDiv.textContent = `Error: ${error.message}`;
        uploadResponseDiv.classList.add('error');
    }
}

async function fetchJobs() {
    const jobsList = document.getElementById('jobsList');
    jobsList.innerHTML = '<li>Loading jobs...</li>';

    // Placeholder: This needs a backend endpoint like GET /api/jobs/all
    // For now, we'll just show a message.
    // To make this somewhat useful, let's imagine the user can input a job ID to check.
    // We can add an input field for that in index.html later if needed.
    
    // A more advanced version would fetch all jobs, or recent jobs.
    // Example:
    // try {
    //     const response = await fetch(`${API_BASE_URL}/jobs/all`); // This endpoint doesn't exist yet
    //     if (!response.ok) throw new Error(`Failed to fetch jobs: ${response.status}`);
    //     const jobs = await response.json();
    //     if (jobs.length === 0) {
    //         jobsList.innerHTML = '<li>No jobs found.</li>';
    //         return;
    //     }
    //     jobsList.innerHTML = ''; // Clear loading
    //     jobs.forEach(job => {
    //         const li = document.createElement('li');
    //         li.innerHTML = `<span>ID:</span> ${job.id} | <span>Type:</span> ${job.job_type} | <span>Status:</span> ${job.status} | <span>Output:</span> ${job.output_file_path ? `<a href="${API_BASE_URL}/audio/download/${job.id}" target="_blank">Download</a>` : 'N/A'}`;
    //         jobsList.appendChild(li);
    //     });
    // } catch (error) {
    //     console.error('Error fetching jobs:', error);
    //     jobsList.innerHTML = `<li>Error fetching jobs: ${error.message}</li>`;
    // }
    jobsList.innerHTML = '<li>Job listing functionality requires a backend endpoint to list all jobs. (Placeholder - No /api/jobs/all endpoint yet)</li>';
}


async function fetchLibrary() {
    const libraryList = document.getElementById('libraryList');
    libraryList.innerHTML = '<li>Loading library items...</li>';
    
    // Placeholder: This needs a backend endpoint to list completed, downloadable items.
    // e.g., GET /api/library/processed or filter completed jobs from /api/jobs/all
    // For example, it could list all jobs with status "COMPLETED" and an "output_file_path".
    
    // Example of how it might work if /api/jobs/all existed and returned all jobs:
    // try {
    //     const response = await fetch(`${API_BASE_URL}/jobs/all`); // This endpoint doesn't exist
    //     if (!response.ok) throw new Error(`Failed to fetch library items: ${response.status}`);
    //     const jobs = await response.json();
    //     const completedJobs = jobs.filter(job => job.status === 'COMPLETED' && job.output_file_path);

    //     if (completedJobs.length === 0) {
    //         libraryList.innerHTML = '<li>No processed media found in the library.</li>';
    //         return;
    //     }
    //     libraryList.innerHTML = ''; // Clear loading
    //     completedJobs.forEach(job => {
    //         const li = document.createElement('li');
    //         let downloadUrl = '';
    //         let mediaType = 'File';
    //         // Determine download URL based on job type
    //         if (job.job_type === 'audio_processing') {
    //             downloadUrl = `${API_BASE_URL}/audio/download/${job.id}`;
    //             mediaType = 'Processed Audio';
    //         } else if (job.job_type === 'video_generation') {
    //             downloadUrl = `${API_BASE_URL}/video/download/${job.id}`;
    //             mediaType = 'Generated Video';
    //         } else if (job.job_type === 'transcription') {
    //             // Transcripts have two files, srt and txt.
    //             // The job.output_file_path typically stores the .srt path for transcriptions.
    //             const srtUrl = `${API_BASE_URL}/transcription/transcript/${job.id}/srt`;
    //             const txtUrl = `${API_BASE_URL}/transcription/transcript/${job.id}/txt`;
    //             li.innerHTML = `<span>${mediaType} (Job ${job.id}):</span> ${job.output_file_path} 
    //                           (<a href="${srtUrl}" target="_blank">SRT</a>, <a href="${txtUrl}" target="_blank">TXT</a>)`;
    //             libraryList.appendChild(li);
    //             return; // Skip default link for transcript
    //         }
            
    //         if (downloadUrl) {
    //             li.innerHTML = `<span>${mediaType} (Job ${job.id}):</span> ${job.output_file_path} <a href="${downloadUrl}" target="_blank">Download</a>`;
    //         } else {
    //             li.innerHTML = `<span>${mediaType} (Job ${job.id}):</span> ${job.output_file_path} (Download link not determined)`;
    //         }
    //         libraryList.appendChild(li);
    //     });
    // } catch (error) {
    //     console.error('Error fetching library:', error);
    //     libraryList.innerHTML = `<li>Error fetching library: ${error.message}</li>`;
    // }
     libraryList.innerHTML = '<li>Library functionality requires a backend endpoint to list processed files. (Placeholder - No /api/jobs/all or /api/library endpoint yet)</li>';
}

// Expose functions to global scope for HTML onclick, or use event listeners
window.showView = showView;
window.fetchJobs = fetchJobs;
window.fetchLibrary = fetchLibrary;
