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
    const sectionHeaders = document.querySelectorAll('.section-header');
    const endSession = document.getElementById('endSession');

    // Summary options
    const optionChips = document.querySelectorAll('.option-chip');
    const summaryTitle = document.getElementById('summaryTitle');

    // Settings toggles
    const toggles = document.querySelectorAll('.toggle');
    const aiOptionToggles = document.querySelectorAll('.toggle[data-ai-option]');

    // Activity items
    const activityItems = document.querySelectorAll('.activity-item');

    // AI Summary Options localStorage helpers
    const AI_OPTIONS_KEY = 'aiSummaryOptions';
    const DEFAULT_AI_OPTIONS = ['summary', 'qa'];

    function getAiSummaryOptions() {
        try {
            const saved = localStorage.getItem(AI_OPTIONS_KEY);
            if (saved) {
                return JSON.parse(saved);
            }
        } catch (e) {
            console.error('Error reading AI options:', e);
        }
        return DEFAULT_AI_OPTIONS;
    }

    function setAiSummaryOptions(options) {
        try {
            localStorage.setItem(AI_OPTIONS_KEY, JSON.stringify(options));
        } catch (e) {
            console.error('Error saving AI options:', e);
        }
    }

    function isAiOptionEnabled(option) {
        return getAiSummaryOptions().includes(option);
    }

    function updateOptionChipsVisibility() {
        if (!optionChips.length) return;

        let firstVisible = null;
        let hasActive = false;

        optionChips.forEach(function(chip) {
            const option = chip.getAttribute('data-option');
            const enabled = isAiOptionEnabled(option);

            if (enabled) {
                chip.style.display = '';
                if (!firstVisible) {
                    firstVisible = chip;
                }
                if (chip.classList.contains('active')) {
                    hasActive = true;
                }
            } else {
                chip.style.display = 'none';
                chip.classList.remove('active');
            }
        });

        // Ensure at least one visible chip is active
        if (firstVisible && !hasActive) {
            optionChips.forEach(function(c) { c.classList.remove('active'); });
            firstVisible.classList.add('active');

            // Also reset summary text to default if title/text exist
            if (summaryTitle && summaryText) {
                const option = firstVisible.getAttribute('data-option');
                if (summaryData[option]) {
                    summaryTitle.textContent = summaryData[option].title;
                    summaryText.textContent = 'Tap Think to generate the ' + summaryData[option].title + '.';
                }
            }
        }
    }

    function initAiOptionToggles() {
        const enabledOptions = getAiSummaryOptions();

        aiOptionToggles.forEach(function(toggle) {
            const option = toggle.getAttribute('data-ai-option');
            const enabled = enabledOptions.includes(option);
            toggle.classList.toggle('active', enabled);

            toggle.addEventListener('click', function() {
                this.classList.toggle('active');
                const isActive = this.classList.contains('active');
                const currentOptions = getAiSummaryOptions();
                const option = this.getAttribute('data-ai-option');

                if (isActive) {
                    if (!currentOptions.includes(option)) {
                        currentOptions.push(option);
                    }
                } else {
                    if (currentOptions.length > 1) {
                        const index = currentOptions.indexOf(option);
                        if (index > -1) {
                            currentOptions.splice(index, 1);
                        }
                    } else {
                        // Keep at least one option enabled
                        this.classList.add('active');
                        showToast('At least one AI summary option is required');
                        return;
                    }
                }

                setAiSummaryOptions(currentOptions);
                showToast('AI summary options updated');
            });
        });
    }

    // Initialize settings AI option toggles
    if (aiOptionToggles.length) {
        initAiOptionToggles();
    }

    // Initialize meeting page option chips
    if (optionChips.length) {
        updateOptionChipsVisibility();
    }

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
            recordingText.style.color = recording ? 'var(--danger)' : 'var(--text-secondary)';
        }

        if (recordingDot) {
            recordingDot.style.animation = recording ? 'pulse 1.5s infinite' : 'none';
            recordingDot.style.backgroundColor = recording ? 'var(--danger)' : 'var(--text-muted)';
        }
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

    // Summary option chips
    const summaryData = {
        summary: {
            title: 'AI Summary',
            text: `
                <strong>Meeting Summary</strong><br><br>
                <strong>Key Points:</strong><br>
                • Discussed Q4 roadmap and priorities<br>
                • Reviewed progress on migration project<br>
                • Action items assigned to team leads<br>
                • Follow-up meeting scheduled for Friday
            `
        },
        qa: {
            title: 'Questions & Answers',
            text: `
                <strong>Q: What is the deadline for the migration?</strong><br>
                A: End of Q4.<br><br>
                <strong>Q: Who owns the testing allocation?</strong><br>
                A: Jane Doe will coordinate with the QA team.<br><br>
                <strong>Q: Next follow-up?</strong><br>
                A: Friday at 2 PM.
            `
        },
        actions: {
            title: 'Action Items',
            text: `
                <strong>Action Items</strong><br><br>
                • John: Draft architecture proposal by Monday<br>
                • Jane: Allocate QA resources by Wednesday<br>
                • Team: Review migration plan before Friday<br>
                • All: Update project timeline in Jira
            `
        },
        decisions: {
            title: 'Decisions',
            text: `
                <strong>Decisions Made</strong><br><br>
                • Move forward with the new architecture proposal<br>
                • Allocate additional QA resources for testing<br>
                • Keep weekly sync cadence until launch<br>
                • Escalate blockers to leadership within 24 hours
            `
        }
    };

    optionChips.forEach(function(chip) {
        chip.addEventListener('click', function() {
            optionChips.forEach(function(c) { c.classList.remove('active'); });
            this.classList.add('active');

            const option = this.getAttribute('data-option');
            if (summaryData[option] && summaryText && summaryTitle) {
                showLoading(summaryText);
                setTimeout(function() {
                    summaryTitle.textContent = summaryData[option].title;
                    summaryText.innerHTML = summaryData[option].text;
                    summaryText.style.color = 'var(--text-primary)';
                }, 600);
            }
        });
    });

    // Think button - generate selected AI summary
    if (thinkBtn) {
        thinkBtn.addEventListener('click', function() {
            if (summaryContent) {
                summaryContent.classList.remove('collapsed');
            }

            const activeChip = document.querySelector('.option-chip.active');
            const option = activeChip ? activeChip.getAttribute('data-option') : 'summary';

            if (summaryText && summaryTitle && summaryData[option]) {
                showLoading(summaryText);

                setTimeout(function() {
                    summaryTitle.textContent = summaryData[option].title;
                    summaryText.innerHTML = summaryData[option].text;
                    summaryText.style.color = 'var(--text-primary)';
                    showToast(summaryData[option].title + ' generated');
                }, 1200);
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

    // Settings toggles (non-AI)
    toggles.forEach(function(toggle) {
        if (toggle.hasAttribute('data-ai-option')) {
            return;
        }
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
