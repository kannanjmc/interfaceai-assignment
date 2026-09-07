/*
 * Meeting Assistant Mobile UI - Interactive Logic
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('Meeting Assistant UI loaded');

    // State
    let isRecording = true;
    let transcriptCount = 0;
    let sampleIndex = 0;

    // Meeting elements
    const recordBtn = document.getElementById('recordBtn');
    const thinkBtn = document.getElementById('thinkBtn');
    const uploadBtn = document.getElementById('uploadBtn');
    const fileInput = document.getElementById('fileInput');
    const summaryText = document.getElementById('summaryText');
    const summaryContent = document.getElementById('summaryContent');
    const transcriptList = document.getElementById('transcriptList');
    const transcriptTitle = document.querySelector('.transcript-section .section-title');
    const recordingSection = document.querySelector('.recording-section');
    const toggleRecording = document.querySelector('.toggle-recording');
    const sectionHeaders = document.querySelectorAll('.section-header');
    const tabButtons = document.querySelectorAll('.tab-btn');
    const endSession = document.querySelector('.end-session');

    // Settings toggles
    const toggles = document.querySelectorAll('.toggle');

    // Activity items
    const activityItems = document.querySelectorAll('.activity-item');

    // Technical section
    const technicalContent = document.getElementById('technicalContent');
    const summarySection = document.querySelector('.summary-section');
    const transcriptSection = document.querySelector('.transcript-section');

    // Recording toggle
    if (recordBtn) {
        recordBtn.addEventListener('click', function() {
            isRecording = !isRecording;
            this.classList.toggle('recording', isRecording);

            if (isRecording) {
                this.innerHTML = '<svg class="icon" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="2"></rect></svg>';
                updateRecordingStatus(true);
                showToast('Recording resumed');
            } else {
                this.innerHTML = '<svg class="icon" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>';
                updateRecordingStatus(false);
                showToast('Recording paused');
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

    // Tab switching (General / Technical)
    tabButtons.forEach(function(btn) {
        btn.addEventListener('click', function() {
            tabButtons.forEach(function(b) { b.classList.remove('active'); });
            this.classList.add('active');

            const tab = this.getAttribute('data-tab');
            if (tab === 'technical') {
                if (summarySection) summarySection.style.display = 'none';
                if (transcriptSection) transcriptSection.style.display = 'none';
                if (technicalContent) technicalContent.classList.remove('collapsed');
            } else {
                if (summarySection) summarySection.style.display = '';
                if (transcriptSection) transcriptSection.style.display = '';
                if (technicalContent) technicalContent.classList.add('collapsed');
            }
        });
    });

    // Think button - generate sample summary
    if (thinkBtn) {
        thinkBtn.addEventListener('click', function() {
            if (summaryContent) {
                summaryContent.classList.remove('collapsed');
            }

            if (summarySection) {
                const header = summarySection.querySelector('.section-header');
                if (header) header.classList.remove('collapsed');
            }

            if (summaryText) {
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
            }
        });
    }

    // Upload button - trigger file input
    if (uploadBtn) {
        uploadBtn.addEventListener('click', function() {
            if (fileInput) {
                fileInput.click();
            }
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
        const emptyState = transcriptList ? transcriptList.querySelector('.empty-state') : null;
        if (emptyState) {
            emptyState.remove();
        }

        transcriptCount++;
        if (transcriptTitle) {
            transcriptTitle.textContent = 'Transcript (' + transcriptCount + ')';
        }

        const item = document.createElement('div');
        item.className = 'transcript-item';
        item.innerHTML = `
            <div class="transcript-speaker">${escapeHtml(speaker)}</div>
            <div class="transcript-text">${escapeHtml(text)}</div>
            <div class="transcript-time">${escapeHtml(time)}</div>
        `;

        if (transcriptList) {
            transcriptList.appendChild(item);
            transcriptList.scrollTop = transcriptList.scrollHeight;
        }
    }

    // Simulate live transcript updates
    const sampleTranscripts = [
        { speaker: 'John Smith', text: 'Welcome everyone to our weekly sync meeting.', time: '0:05' },
        { speaker: 'Jane Doe', text: 'Thanks John. Let me start with the project update.', time: '0:12' },
        { speaker: 'John Smith', text: 'Great, please go ahead Jane.', time: '0:18' }
    ];

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

    // Settings toggles
    toggles.forEach(function(toggle) {
        toggle.addEventListener('click', function() {
            this.classList.toggle('active');
        });
    });

    // Activity item clicks
    activityItems.forEach(function(item) {
        item.addEventListener('click', function() {
            const text = this.querySelector('.activity-text');
            if (text) {
                showToast(text.textContent);
            }
        });
    });

    // End session button
    if (endSession) {
        endSession.addEventListener('click', function() {
            showToast('Meeting ended');
            setTimeout(function() {
                window.location.href = '/home';
            }, 1000);
        });
    }

    // Helper: Show loading state
    function showLoading(element) {
        if (!element) return;
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
});
