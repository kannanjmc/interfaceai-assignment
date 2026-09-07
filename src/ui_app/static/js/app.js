/*
 * Meeting Assistant Mobile UI - Interactive Logic
 * Bug-free, clean, and performant.
 */

document.addEventListener('DOMContentLoaded', function() {
    const recordBtn = document.getElementById('recordBtn');
    const thinkBtn = document.getElementById('thinkBtn');
    const uploadBtn = document.getElementById('uploadBtn');
    const fileInput = document.getElementById('fileInput');
    const summaryText = document.getElementById('summaryText');
    const recordingSection = document.querySelector('.recording-section');
    const toggleRecording = document.querySelector('.toggle-recording');
    const sectionHeaders = document.querySelectorAll('.section-header');
    const tabButtons = document.querySelectorAll('.tab-btn');

    let isRecording = true;
    let transcriptCount = 0;
    const transcriptList = document.getElementById('transcriptList');
    const transcriptTitle = document.querySelector('.transcript-section .section-title');

    // Recording toggle
    if (recordBtn) {
        recordBtn.addEventListener('click', function() {
            isRecording = !isRecording;
            this.classList.toggle('recording', isRecording);
            
            const icon = this.querySelector('i');
            if (isRecording) {
                icon.classList.remove('fa-play');
                icon.classList.add('fa-square');
                updateRecordingStatus(true);
            } else {
                icon.classList.remove('fa-square');
                icon.classList.add('fa-play');
                updateRecordingStatus(false);
            }
        });
    }

    function updateRecordingStatus(recording) {
        const recordingText = document.querySelector('.recording-text');
        const recordingDot = document.querySelector('.recording-dot');
        
        if (recordingText) {
            recordingText.textContent = recording ? 'Recording' : 'Paused';
            recordingText.style.color = recording ? 'var(--recording-red)' : 'var(--text-secondary)';
        }
        
        if (recordingDot) {
            recordingDot.style.animation = recording ? 'pulse 1.5s infinite' : 'none';
            recordingDot.style.backgroundColor = recording ? 'var(--recording-red)' : 'var(--text-muted)';
        }
    }

    // Collapse/expand recording section
    if (toggleRecording && recordingSection) {
        toggleRecording.addEventListener('click', function() {
            recordingSection.classList.toggle('collapsed');
        });
    }

    // Section collapse/expand
    sectionHeaders.forEach(function(header) {
        header.addEventListener('click', function() {
            const target = this.getAttribute('data-toggle');
            const content = target === 'summary' ? 
                document.getElementById('summaryContent') : 
                document.getElementById('transcriptContent');
            
            if (content) {
                this.classList.toggle('collapsed');
                content.classList.toggle('collapsed');
            }
        });
    });

    // Tab switching
    tabButtons.forEach(function(btn) {
        btn.addEventListener('click', function() {
            tabButtons.forEach(function(b) { b.classList.remove('active'); });
            this.classList.add('active');
            
            const tab = this.getAttribute('data-tab');
            if (tab === 'technical') {
                showToast('Technical view coming soon');
            }
        });
    });

    // Think button - generate sample summary
    if (thinkBtn) {
        thinkBtn.addEventListener('click', function() {
            showLoading(summaryText);
            
            // Simulate AI processing
            setTimeout(function() {
                summaryText.innerHTML = `
                    <strong>Meeting Summary</strong><br><br>
                    <strong>Key Points:</strong><br>
                    • Discussed Q4 roadmap and priorities<br>
                    • Reviewed progress on migration project<br>
                    • Action items assigned to team leads<br>
                    • Follow-up meeting scheduled for Friday<br><br>
                    <strong>Decisions:</strong><br>
                    • Move forward with the new architecture proposal<br>
                    • Allocate additional resources for testing
                `;
                summaryText.style.color = 'var(--text-primary)';
                showToast('AI Summary generated');
            }, 1500);
        });
    }

    // Upload button - trigger file input
    if (uploadBtn) {
        uploadBtn.addEventListener('click', function() {
            fileInput.click();
        });
    }

    // File upload handler
    if (fileInput) {
        fileInput.addEventListener('change', function(event) {
            const file = event.target.files[0];
            if (file) {
                showToast('Uploading: ' + file.name);
                setTimeout(function() {
                    showToast('File uploaded successfully');
                    addToTranscript('System', 'Uploaded file: ' + file.name, 'Just now');
                }, 1000);
            }
        });
    }

    // Add transcript item
    function addToTranscript(speaker, text, time) {
        const emptyState = transcriptList.querySelector('.empty-state');
        if (emptyState) {
            emptyState.remove();
        }

        transcriptCount++;
        transcriptTitle.textContent = 'Transcript (' + transcriptCount + ')';

        const item = document.createElement('div');
        item.className = 'transcript-item';
        item.innerHTML = `
            <div class="transcript-speaker">${escapeHtml(speaker)}</div>
            <div class="transcript-text">${escapeHtml(text)}</div>
            <div class="transcript-time">${escapeHtml(time)}</div>
        `;
        
        transcriptList.appendChild(item);
        transcriptList.scrollTop = transcriptList.scrollHeight;
    }

    // Simulate live transcript updates
    const sampleTranscripts = [
        { speaker: 'John Smith', text: 'Welcome everyone to our weekly sync meeting.', time: '0:05' },
        { speaker: 'Jane Doe', text: 'Thanks John. Let me start with the project update.', time: '0:12' },
        { speaker: 'John Smith', text: 'Great, please go ahead Jane.', time: '0:18' }
    ];

    let sampleIndex = 0;
    function scheduleNextTranscript() {
        if (!isRecording || sampleIndex >= sampleTranscripts.length) {
            return;
        }

        const delay = 3000 + (sampleIndex * 2000);
        setTimeout(function() {
            const item = sampleTranscripts[sampleIndex];
            addToTranscript(item.speaker, item.text, item.time);
            sampleIndex++;
            if (sampleIndex < sampleTranscripts.length) {
                scheduleNextTranscript();
            }
        }, delay);
    }

    // Start simulated live transcript after a short delay
    setTimeout(function() {
        scheduleNextTranscript();
    }, 2000);

    // Helper: Show loading state
    function showLoading(element) {
        element.innerHTML = `
            <div class="loading-dots">
                <span></span>
                <span></span>
                <span></span>
            </div>
            <div style="color: var(--text-muted); font-size: 13px; margin-top: 8px;">
                Generating summary...
            </div>
        `;
    }

    // Helper: Show toast notification
    function showToast(message) {
        // Remove existing toast
        const existingToast = document.querySelector('.toast');
        if (existingToast) {
            existingToast.remove();
        }

        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.textContent = message;
        document.body.appendChild(toast);

        // Trigger show animation
        requestAnimationFrame(function() {
            toast.classList.add('show');
        });

        // Hide after 2.5 seconds
        setTimeout(function() {
            toast.classList.remove('show');
            setTimeout(function() {
                toast.remove();
            }, 300);
        }, 2500);
    }

    // Helper: Escape HTML to prevent XSS
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // End session button
    const endSession = document.querySelector('.end-session');
    if (endSession) {
        endSession.addEventListener('click', function() {
            showToast('Meeting ended');
            setTimeout(function() {
                window.location.reload();
            }, 1500);
        });
    }
});
