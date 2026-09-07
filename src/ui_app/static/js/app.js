/*
 * Meeting Assistant Mobile UI - Interactive Logic
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('Meeting Assistant UI loaded');

    // State
    let isRecording = true;
    let transcriptCount = 0;
    let sampleIndex = 0;

    // 50 AI summary options
    const ALL_OPTIONS = [
        { key: 'summary', label: 'Summary' },
        { key: 'qa', label: 'Q&A' },
        { key: 'actions', label: 'Action Items' },
        { key: 'decisions', label: 'Decisions' },
        { key: 'takeaways', label: 'Key Takeaways' },
        { key: 'minutes', label: 'Meeting Minutes' },
        { key: 'followups', label: 'Follow-ups' },
        { key: 'attendees', label: 'Attendees' },
        { key: 'sentiment', label: 'Sentiment' },
        { key: 'topics', label: 'Topics' },
        { key: 'blockers', label: 'Blockers' },
        { key: 'risks', label: 'Risks' },
        { key: 'highlights', label: 'Highlights' },
        { key: 'nextsteps', label: 'Next Steps' },
        { key: 'deliverables', label: 'Deliverables' },
        { key: 'agreements', label: 'Agreements' },
        { key: 'disagreements', label: 'Disagreements' },
        { key: 'timeline', label: 'Timeline' },
        { key: 'budget', label: 'Budget' },
        { key: 'resources', label: 'Resources' },
        { key: 'goals', label: 'Goals' },
        { key: 'metrics', label: 'Metrics' },
        { key: 'performance', label: 'Performance' },
        { key: 'feedback', label: 'Feedback' },
        { key: 'suggestions', label: 'Suggestions' },
        { key: 'ideas', label: 'Ideas' },
        { key: 'proposals', label: 'Proposals' },
        { key: 'votes', label: 'Votes' },
        { key: 'polls', label: 'Polls' },
        { key: 'decisions_log', label: 'Decisions Log' },
        { key: 'action_log', label: 'Action Log' },
        { key: 'assignments', label: 'Task Assignments' },
        { key: 'due_dates', label: 'Due Dates' },
        { key: 'reminders', label: 'Reminders' },
        { key: 'calendar', label: 'Calendar' },
        { key: 'recap', label: 'Recap' },
        { key: 'overview', label: 'Overview' },
        { key: 'insights', label: 'Insights' },
        { key: 'trends', label: 'Trends' },
        { key: 'patterns', label: 'Patterns' },
        { key: 'anomalies', label: 'Anomalies' },
        { key: 'questions', label: 'Questions' },
        { key: 'answers', label: 'Answers' },
        { key: 'notes', label: 'Notes' },
        { key: 'comments', label: 'Comments' },
        { key: 'conclusion', label: 'Conclusion' },
        { key: 'recommendations', label: 'Recommendations' },
        { key: 'priorities', label: 'Priorities' },
        { key: 'dependencies', label: 'Dependencies' },
        { key: 'custom_1', label: 'Custom 1' },
        { key: 'custom_2', label: 'Custom 2' }
    ];

    // Meeting elements
    const recordBtn = document.getElementById('recordBtn');
    const thinkBtn = document.getElementById('thinkBtn');
    const uploadBtn = document.getElementById('uploadBtn');
    const fileInput = document.getElementById('fileInput');
    const summaryText = document.getElementById('summaryText');
    const summaryContent = document.getElementById('summaryContent');
    const summaryTitle = document.getElementById('summaryTitle');
    const cacheIcon = document.getElementById('cacheIcon');
    const summaryOptions = document.getElementById('summaryOptions');
    const transcriptList = document.getElementById('transcriptList');
    const transcriptTitle = document.querySelector('.transcript-section .section-title');
    const sectionHeaders = document.querySelectorAll('.section-header');
    const endSession = document.getElementById('endSession');

    // Floating options
    const optionsFab = document.getElementById('optionsFab');
    const floatingOptions = document.getElementById('floatingOptions');
    const optionsClose = document.getElementById('optionsClose');
    const floatingOptionsList = document.getElementById('floatingOptionsList');

    // Settings
    const aiOptionsList = document.getElementById('aiOptionsList');

    // Settings toggles
    const toggles = document.querySelectorAll('.toggle');

    // Activity items
    const activityItems = document.querySelectorAll('.activity-item');

    const AI_OPTIONS_KEY = 'aiSummaryOptions';
    const AI_CACHE_KEY = 'aiSummaryCache';
    const DEFAULT_AI_OPTIONS = ['summary', 'qa'];

    function getAiSummaryOptions() {
        try {
            const saved = localStorage.getItem(AI_OPTIONS_KEY);
            if (saved) {
                return JSON.parse(saved);
            }
        } catch (e) {}
        return DEFAULT_AI_OPTIONS;
    }

    function setAiSummaryOptions(options) {
        try {
            localStorage.setItem(AI_OPTIONS_KEY, JSON.stringify(options));
        } catch (e) {}
    }

    function getSummaryCache() {
        try {
            const saved = localStorage.getItem(AI_CACHE_KEY);
            if (saved) {
                return JSON.parse(saved);
            }
        } catch (e) {}
        return {};
    }

    function setSummaryCache(key, data) {
        try {
            const cache = getSummaryCache();
            cache[key] = {
                title: data.title,
                text: data.text,
                generated_at: data.generated_at,
                cached_at: new Date().toISOString()
            };
            localStorage.setItem(AI_CACHE_KEY, JSON.stringify(cache));
        } catch (e) {}
    }

    function getCachedSummary(key) {
        const cache = getSummaryCache();
        return cache[key] || null;
    }

    function fetchSummaryFromService(key, callback) {
        fetch('/api/summary/' + encodeURIComponent(key))
            .then(function(response) {
                if (!response.ok) {
                    throw new Error('Service error');
                }
                return response.json();
            })
            .then(function(data) {
                setSummaryCache(key, data);
                callback(null, data);
            })
            .catch(function(err) {
                callback(err, null);
            });
    }

    function setCacheIcon(visible) {
        if (cacheIcon) {
            cacheIcon.style.display = visible ? '' : 'none';
        }
    }

    function loadSummaryContent(key, forceRefresh) {
        if (summaryTitle && summaryText) {
            showLoading(summaryText);
        }

        if (!forceRefresh) {
            const cached = getCachedSummary(key);
            if (cached) {
                displaySummary(cached);
                setCacheIcon(true);
                return;
            }
        }

        setCacheIcon(false);

        fetchSummaryFromService(key, function(err, data) {
            if (err) {
                if (summaryText) {
                    summaryText.textContent = 'Failed to load. Please try again.';
                    summaryText.style.color = 'var(--danger)';
                }
                setCacheIcon(false);
                showToast('Service error');
                return;
            }
            displaySummary(data);
            setCacheIcon(false);
            showToast(data.title + ' loaded from service');
        });
    }

    function displaySummary(data) {
        if (summaryTitle && summaryText) {
            summaryTitle.textContent = data.title;
            summaryText.innerHTML = data.text;
            summaryText.style.color = 'var(--text-primary)';
        }
    }

    function getOptionByKey(key) {
        return ALL_OPTIONS.find(function(opt) { return opt.key === key; });
    }

    function renderChips() {
        if (!summaryOptions) return;

        const enabled = getAiSummaryOptions();
        summaryOptions.innerHTML = '';

        enabled.forEach(function(key, index) {
            const opt = getOptionByKey(key);
            if (!opt) return;

            const chip = document.createElement('button');
            chip.className = 'option-chip' + (index === 0 ? ' active' : '');
            chip.setAttribute('data-option', key);
            chip.textContent = opt.label;

            chip.addEventListener('click', function() {
                document.querySelectorAll('.option-chip').forEach(function(c) {
                    c.classList.remove('active');
                });
                this.classList.add('active');

                loadSummaryContent(opt.key, false);
            });

            summaryOptions.appendChild(chip);
        });
    }

    function renderFloatingOptions() {
        if (!floatingOptionsList) return;

        const enabled = getAiSummaryOptions();
        floatingOptionsList.innerHTML = '';

        ALL_OPTIONS.forEach(function(opt) {
            const isActive = enabled.includes(opt.key);

            const label = document.createElement('label');
            label.className = 'floating-option';
            label.setAttribute('data-option', opt.key);

            const span = document.createElement('span');
            span.textContent = opt.label;

            const toggle = document.createElement('div');
            toggle.className = 'toggle' + (isActive ? ' active' : '');

            label.appendChild(span);
            label.appendChild(toggle);
            floatingOptionsList.appendChild(label);

            toggle.addEventListener('click', function(e) {
                e.stopPropagation();
                handleFloatingToggle(opt.key, this);
            });

            span.addEventListener('click', function(e) {
                e.stopPropagation();
                handleFloatingToggle(opt.key, toggle);
            });
        });
    }

    function renderSettingsOptions() {
        if (!aiOptionsList) return;

        const enabled = getAiSummaryOptions();
        aiOptionsList.innerHTML = '';

        ALL_OPTIONS.forEach(function(opt) {
            const isActive = enabled.includes(opt.key);

            const row = document.createElement('div');
            row.className = 'setting-row';

            const label = document.createElement('span');
            label.className = 'setting-label';
            label.textContent = opt.label;

            const toggle = document.createElement('div');
            toggle.className = 'toggle' + (isActive ? ' active' : '');

            row.appendChild(label);
            row.appendChild(toggle);
            aiOptionsList.appendChild(row);

            toggle.addEventListener('click', function() {
                const currentOptions = getAiSummaryOptions();
                const currentlyActive = currentOptions.includes(opt.key);

                if (currentlyActive) {
                    if (currentOptions.length > 1) {
                        currentOptions.splice(currentOptions.indexOf(opt.key), 1);
                    } else {
                        showToast('At least one AI summary option is required');
                        return;
                    }
                } else {
                    currentOptions.push(opt.key);
                }

                setAiSummaryOptions(currentOptions);
                this.classList.toggle('active', currentOptions.includes(opt.key));
                showToast('AI summary options updated');
            });
        });
    }

    function handleFloatingToggle(key, toggle) {
        const currentOptions = getAiSummaryOptions();
        const isActive = currentOptions.includes(key);

        if (isActive) {
            if (currentOptions.length > 1) {
                currentOptions.splice(currentOptions.indexOf(key), 1);
            } else {
                showToast('At least one AI summary option is required');
                return;
            }
        } else {
            currentOptions.push(key);
        }

        setAiSummaryOptions(currentOptions);

        // Update all toggles to reflect current state
        updateFloatingToggles();

        // Re-render chips
        const wasFirst = currentOptions[0] === key;
        renderChips();

        // Update summary text to first visible
        const firstChip = document.querySelector('.option-chip');
        if (firstChip && summaryTitle && summaryText) {
            const activeOption = getOptionByKey(firstChip.getAttribute('data-option'));
            if (activeOption) {
                summaryTitle.textContent = 'AI ' + activeOption.label;
                summaryText.textContent = 'Tap Think to generate the ' + activeOption.label + '.';
            }
        }
    }

    function updateFloatingToggles() {
        const enabled = getAiSummaryOptions();
        document.querySelectorAll('.floating-option').forEach(function(row) {
            const key = row.getAttribute('data-option');
            const toggle = row.querySelector('.toggle');
            if (toggle) {
                toggle.classList.toggle('active', enabled.includes(key));
            }
        });
    }

    function openFloatingOptions() {
        if (floatingOptions) {
            updateFloatingToggles();
            floatingOptions.classList.add('open');
        }
    }

    function closeFloatingOptions() {
        if (floatingOptions) {
            floatingOptions.classList.remove('open');
        }
    }

    if (optionsFab) {
        optionsFab.addEventListener('click', function(e) {
            e.stopPropagation();
            openFloatingOptions();
        });
    }

    if (optionsClose) {
        optionsClose.addEventListener('click', function(e) {
            e.stopPropagation();
            closeFloatingOptions();
        });
    }

    if (floatingOptions) {
        floatingOptions.addEventListener('click', function(e) {
            e.stopPropagation();
        });
    }

    document.addEventListener('click', function() {
        closeFloatingOptions();
    });

    // Recording toggle
    if (recordBtn) {
        recordBtn.addEventListener('click', function() {
            isRecording = !isRecording;

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

    // Think button - refresh from service
    if (thinkBtn) {
        thinkBtn.addEventListener('click', function() {
            if (summaryContent) {
                summaryContent.classList.remove('collapsed');
            }

            const activeChip = document.querySelector('.option-chip.active');
            const key = activeChip ? activeChip.getAttribute('data-option') : 'summary';

            loadSummaryContent(key, true);
        });
    }

    // Upload button
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
        if (toggle.closest('.floating-option')) {
            return;
        }
        if (toggle.closest('#aiOptionsList')) {
            return;
        }
        toggle.addEventListener('click', function() {
            this.classList.toggle('active');
        });
    });

    // Activity items
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

    // Helpers
    function showLoading(element) {
        if (!element) return;
        element.innerHTML = `
            <div class="loading-dots">
                <span></span>
                <span></span>
                <span></span>
            </div>
            <div style="color: var(--text-muted); font-size: 12px; margin-top: 6px;">
                Generating...
            </div>
        `;
    }

    function showToast(message) {
        const existingToast = document.querySelector('.toast');
        if (existingToast) {
            existingToast.remove();
        }

        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.textContent = message;
        document.body.appendChild(toast);

        requestAnimationFrame(function() {
            toast.classList.add('show');
        });

        setTimeout(function() {
            toast.classList.remove('show');
            setTimeout(function() {
                toast.remove();
            }, 300);
        }, 2500);
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Initialize
    renderFloatingOptions();
    renderSettingsOptions();
    renderChips();

    const firstChip = document.querySelector('.option-chip');
    if (firstChip && summaryTitle && summaryText) {
        const opt = getOptionByKey(firstChip.getAttribute('data-option'));
        if (opt) {
            summaryTitle.textContent = 'AI ' + opt.label;
            summaryText.textContent = 'Tap Think to generate the ' + opt.label + '.';
        }
    }
});
