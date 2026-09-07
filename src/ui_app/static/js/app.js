/*
 * Meeting Assistant Mobile UI - Interactive Logic
 */

window.onerror = function(message, source, lineno, colno, error) {
    console.error('JS Error:', message, 'line:', lineno, 'col:', colno, error);
};

document.addEventListener('DOMContentLoaded', function() {
    console.log('Meeting Assistant UI loaded');

    // State
    let isRecording = false;
    let transcriptCount = 0;
    let sampleIndex = 0;
    let mediaRecorder = null;
    let audioChunks = [];
    let audioStream = null;
    let speechRecognition = null;

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
    const summaryHistory = document.getElementById('summaryHistory');
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
    const autoSummaryInterval = document.getElementById('autoSummaryInterval');

    // Settings toggles
    const toggles = document.querySelectorAll('.toggle');

    // Activity items
    const activityItems = document.querySelectorAll('.activity-item');

    const AI_OPTIONS_KEY = 'aiSummaryOptions';
    const AI_CACHE_KEY = 'aiSummaryCache';
    const AUTO_INTERVAL_KEY = 'autoSummaryInterval';
    const DEFAULT_AI_OPTIONS = ['summary', 'qa'];
    let autoSummaryTimer = null;

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

    function getAutoSummaryInterval() {
        try {
            const saved = localStorage.getItem(AUTO_INTERVAL_KEY);
            if (saved) {
                return parseInt(saved, 10);
            }
        } catch (e) {}
        return 0;
    }

    function setAutoSummaryInterval(seconds) {
        try {
            localStorage.setItem(AUTO_INTERVAL_KEY, String(seconds));
        } catch (e) {}
    }

    function startAutoSummary() {
        stopAutoSummary();
        const seconds = getAutoSummaryInterval();
        if (seconds > 0 && isRecording) {
            autoSummaryTimer = setInterval(function() {
                const activeChip = document.querySelector('.option-chip.active');
                const key = activeChip ? activeChip.getAttribute('data-option') : 'summary';
                if (activeChip && summaryContent) {
                    summaryContent.classList.remove('collapsed');
                }
                loadSummaryContent(key, true);
            }, seconds * 1000);
        }
    }

    function stopAutoSummary() {
        if (autoSummaryTimer) {
            clearInterval(autoSummaryTimer);
            autoSummaryTimer = null;
        }
    }

    function setSummaryCache(key, data) {
        try {
            const cache = getSummaryCache();
            if (!cache[key]) {
                cache[key] = [];
            }

            cache[key].unshift({
                title: data.title,
                text: data.text,
                generated_at: data.generated_at,
                cached_at: new Date().toISOString()
            });

            if (cache[key].length > 5) {
                cache[key] = cache[key].slice(0, 5);
            }

            localStorage.setItem(AI_CACHE_KEY, JSON.stringify(cache));
        } catch (e) {}
    }

    function getCachedSummary(key) {
        const cache = getSummaryCache();
        if (!cache[key] || !cache[key].length) return null;
        return cache[key][0];
    }

    function getSummaryHistory(key) {
        const cache = getSummaryCache();
        return cache[key] || [];
    }

    function getTranscriptText() {
        if (!transcriptList) return '';
        const items = transcriptList.querySelectorAll('.transcript-text');
        return Array.from(items).map(function(el) { return el.textContent; }).join(' ');
    }

    function fetchSummaryFromService(key, callback) {
        console.log('fetching /api/summary with option:', key);
        const transcript = getTranscriptText();

        fetch('/api/summary', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ option: key, transcript: transcript })
        })
            .then(function(response) {
                console.log('fetch response:', response.status);
                if (!response.ok) {
                    throw new Error('Service error');
                }
                return response.json();
            })
            .then(function(data) {
                console.log('fetch data:', data);
                setSummaryCache(key, data);
                callback(null, data);
            })
            .catch(function(err) {
                console.log('fetch error:', err);
                callback(err, null);
            });
    }

    function setCacheIcon(visible) {
        if (cacheIcon) {
            cacheIcon.style.display = visible ? '' : 'none';
        }
    }

    function isCacheFresh(key) {
        const cached = getCachedSummary(key);
        if (!cached || !cached.cached_at) return false;
        const ttl = getAutoSummaryInterval() * 1000;
        if (ttl <= 0) return false;
        const cachedAt = new Date(cached.cached_at).getTime();
        return (Date.now() - cachedAt) < ttl;
    }

    function loadSummaryContent(key, forceRefresh) {
        console.log('loadSummaryContent called:', key, 'force:', forceRefresh);
        if (summaryTitle && summaryText) {
            showLoading(summaryText);
        }

        if (!forceRefresh && isCacheFresh(key)) {
            const cached = getCachedSummary(key);
            console.log('using cache');
            displaySummary(cached);
            setCacheIcon(true);
            showToast('Loaded from cache');
            return;
        }

        setCacheIcon(false);

        fetchSummaryFromService(key, function(err, data) {
            console.log('fetch callback:', err, data);
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

    function renderHistory(key) {
        if (!summaryHistory) return;

        const history = getSummaryHistory(key);
        if (history.length <= 1) {
            summaryHistory.innerHTML = '';
            return;
        }

        summaryHistory.innerHTML = '<div class="summary-history-title">Previous</div>';

        history.slice(1).forEach(function(item, index) {
            const entry = document.createElement('div');
            entry.className = 'summary-history-item';
            entry.innerHTML = item.text;
            entry.style.display = index === 0 ? '' : 'none';

            if (index === 0) {
                summaryHistory.appendChild(entry);
            }
        });

        if (history.length > 2) {
            const count = document.createElement('div');
            count.className = 'summary-history-count';
            count.textContent = '+' + (history.length - 2) + ' more';
            summaryHistory.appendChild(count);
        }
    }

    function displaySummary(data) {
        if (summaryTitle && summaryText) {
            summaryTitle.textContent = data.title;
            summaryText.innerHTML = data.text;
            summaryText.style.color = 'var(--text-primary)';
        }

        const activeChip = document.querySelector('.option-chip.active');
        const key = activeChip ? activeChip.getAttribute('data-option') : null;
        if (key) {
            renderHistory(key);
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

        const intro = document.createElement('span');
        intro.className = 'option-paragraph-intro';
        intro.textContent = 'Tap the options you want to show: ';
        floatingOptionsList.appendChild(intro);

        ALL_OPTIONS.forEach(function(opt, index) {
            const word = document.createElement('span');
            word.className = 'option-word' + (enabled.includes(opt.key) ? ' selected' : '');
            word.setAttribute('data-option', opt.key);
            word.textContent = opt.label;
            if (index < ALL_OPTIONS.length - 1) {
                word.textContent += ',';
            }

            word.addEventListener('click', function(e) {
                e.stopPropagation();
                handleFloatingToggle(opt.key);
            });

            floatingOptionsList.appendChild(word);
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

    function handleFloatingToggle(key) {
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

        // Update all word styles
        updateFloatingToggles();

        // Re-render chips
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
        document.querySelectorAll('.option-word').forEach(function(word) {
            const key = word.getAttribute('data-option');
            word.classList.toggle('selected', enabled.includes(key));
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

    function startSpeechRecognition() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            console.log('Web Speech API not supported');
            return;
        }

        speechRecognition = new SpeechRecognition();
        speechRecognition.continuous = true;
        speechRecognition.interimResults = false;
        speechRecognition.lang = 'en-US';

        speechRecognition.onresult = function(event) {
            for (let i = event.resultIndex; i < event.results.length; i++) {
                const result = event.results[i];
                if (result.isFinal) {
                    const text = result[0].transcript;
                    addToTranscript('Speaker', text, new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}));
                }
            }
        };

        speechRecognition.onerror = function(event) {
            console.error('Speech recognition error:', event.error);
        };

        speechRecognition.onend = function() {
            if (isRecording && speechRecognition) {
                speechRecognition.start();
            }
        };

        try {
            speechRecognition.start();
        } catch (e) {
            console.error('Could not start speech recognition:', e);
        }
    }

    function stopSpeechRecognition() {
        if (speechRecognition) {
            speechRecognition.stop();
            speechRecognition = null;
        }
    }

    function stopAudioRecording() {
        stopSpeechRecognition();
        if (mediaRecorder && mediaRecorder.state !== 'inactive') {
            mediaRecorder.stop();
        }
        if (audioStream) {
            audioStream.getTracks().forEach(function(track) { track.stop(); });
            audioStream = null;
        }
        isRecording = false;
        if (recordBtn) recordBtn.classList.remove('recording');
        updateRecordingStatus(false);
        stopAutoSummary();
    }

    function startAudioRecording() {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            showToast('Audio recording not supported in this browser');
            return;
        }

        navigator.mediaDevices.getUserMedia({ audio: true })
            .then(function(stream) {
                audioStream = stream;

                try {
                    mediaRecorder = new MediaRecorder(stream);
                } catch (e) {
                    showToast('MediaRecorder not supported');
                    return;
                }

                audioChunks = [];

                mediaRecorder.ondataavailable = function(event) {
                    if (event.data.size > 0) {
                        audioChunks.push(event.data);
                    }
                };

                mediaRecorder.onstop = function() {
                    const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                    const audioUrl = URL.createObjectURL(audioBlob);

                    addToTranscript('System', 'Audio recording saved (' + (audioBlob.size / 1024).toFixed(1) + ' KB)', 'Just now');

                    // Optional download link
                    const link = document.createElement('a');
                    link.href = audioUrl;
                    link.download = 'meeting-recording-' + Date.now() + '.webm';
                    link.style.display = 'none';
                    document.body.appendChild(link);
                    // Do not auto-click; user can download if needed
                };

                mediaRecorder.onerror = function(e) {
                    console.error('MediaRecorder error:', e);
                    showToast('Recording error');
                    stopAudioRecording();
                };

                mediaRecorder.start();
                startSpeechRecognition();
                isRecording = true;
                if (recordBtn) recordBtn.classList.add('recording');
                updateRecordingStatus(true);
                startAutoSummary();
                showToast('Recording started');
            })
            .catch(function(err) {
                console.error('Microphone permission denied:', err);
                showToast('Microphone permission denied');
            });
    }

    // Recording toggle
    if (recordBtn) {
        console.log('recordBtn found and listener attached');
        recordBtn.addEventListener('click', function() {
            console.log('recordBtn clicked');

            if (isRecording) {
                stopAudioRecording();
                this.innerHTML = '<svg class="icon" viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="10"></circle><circle cx="12" cy="12" r="4" fill="currentColor"></circle></svg>';
                showToast('Recording stopped');
            } else {
                this.innerHTML = '<svg class="icon" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="2"></rect></svg>';
                startAudioRecording();
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

    // Think button
    if (thinkBtn) {
        console.log('thinkBtn found and listener attached');
        thinkBtn.addEventListener('click', function() {
            console.log('thinkBtn clicked');
            if (summaryContent) {
                summaryContent.classList.remove('collapsed');
            }

            const activeChip = document.querySelector('.option-chip.active');
            const key = activeChip ? activeChip.getAttribute('data-option') : 'summary';

            loadSummaryContent(key, false);
        });
    }

    // Upload button
    if (uploadBtn) {
        console.log('uploadBtn found and listener attached');
        uploadBtn.addEventListener('click', function() {
            console.log('uploadBtn clicked');
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
        console.log('endSession found and listener attached');
        endSession.addEventListener('click', function() {
            console.log('endSession clicked');
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

    // Auto-summarize interval select
    if (autoSummaryInterval) {
        autoSummaryInterval.value = String(getAutoSummaryInterval());
        autoSummaryInterval.addEventListener('change', function() {
            const seconds = parseInt(this.value, 10);
            setAutoSummaryInterval(seconds);
            if (isRecording) {
                startAutoSummary();
            }
        });
    }

    // Initialize
    updateRecordingStatus(false);
    if (recordBtn) {
        recordBtn.innerHTML = '<svg class="icon" viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="10"></circle><circle cx="12" cy="12" r="4" fill="currentColor"></circle></svg>';
    }

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
