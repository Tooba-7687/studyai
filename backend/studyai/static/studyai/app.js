const api = async (endpoint, options = {}) => {
    const response = await fetch(`/api/${endpoint}/`, {headers: {'X-Requested-With': 'XMLHttpRequest', ...(options.headers || {})}, ...options});
    const contentType = response.headers.get('content-type') || '';
    const data = contentType.includes('application/json') ? await response.json() : null;
    if (!data) throw new Error(`Server returned an unexpected response (${response.status}). Refresh the page and try again.`);
    if (!response.ok) throw new Error(data.error || 'Request failed.');
    return data;
};

const renderStudyText = (content) => {
    const source = String(content || '');
    if (window.marked && window.DOMPurify) {
        const html = window.marked.parse(source, {breaks: true, gfm: true});
        return window.DOMPurify.sanitize(html);
    }
    return escapeHtml(source).replace(/\n/g, '<br>');
};

const renderMath = (target) => {
    if (window.renderMathInElement) {
        window.renderMathInElement(target, {
            delimiters: [
                {left: '$$', right: '$$', display: true},
                {left: '$', right: '$', display: false},
                {left: '\\[', right: '\\]', display: true},
                {left: '\\(', right: '\\)', display: false}
            ],
            throwOnError: false
        });
    }
};

const showResult = (id, content, title = '') => {
    const target = document.getElementById(id);
    target.innerHTML = `<div class="result-card markdown-result">${title ? `<h3>${escapeHtml(title)}</h3>` : ''}<div class="rendered-content">${renderStudyText(content)}</div></div>`;
    renderMath(target.querySelector('.rendered-content'));
};
const escapeHtml = (value) => String(value || '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[char]));
let currentPlan = null;

const renderSavedPlans = (plans) => {
    const target = document.getElementById('saved-plans');
    if (!plans.length) {
        target.innerHTML = '<div class="saved-empty">No saved plans yet. Generate your first roadmap above.</div>';
        return;
    }
    target.innerHTML = plans.map(plan => `<article class="saved-plan"><div><strong>${escapeHtml(plan.title)}</strong><small>${escapeHtml(plan.exam_date)} · ${plan.hours_per_day} hours/day</small><p>${escapeHtml(plan.topics)}</p></div><div class="saved-plan-actions"><button class="secondary-button" data-open-plan="${plan.id}">Open</button><button class="text-button" data-edit-plan="${plan.id}">Rename</button><button class="text-button danger" data-delete-plan="${plan.id}">Delete</button></div></article>`).join('');
    target.querySelectorAll('[data-open-plan]').forEach(button => button.addEventListener('click', () => {
        const plan = plans.find(item => item.id === Number(button.dataset.openPlan));
        currentPlan = plan;
        document.getElementById('plan-topics').value = plan.topics;
        document.getElementById('plan-date').value = plan.exam_date;
        document.getElementById('plan-hours').value = plan.hours_per_day;
        showResult('planner-result', plan.plan, plan.title);
        addPlanActions();
    }));
    target.querySelectorAll('[data-edit-plan]').forEach(button => button.addEventListener('click', async () => {
        const plan = plans.find(item => item.id === Number(button.dataset.editPlan));
        const title = window.prompt('Plan name', plan.title);
        if (!title || title === plan.title) return;
        await api(`study-plans/${plan.id}`, {method:'PATCH', headers:{'Content-Type':'application/json'}, body:JSON.stringify({title})});
        loadSavedPlans();
    }));
    target.querySelectorAll('[data-delete-plan]').forEach(button => button.addEventListener('click', async () => {
        if (!window.confirm('Delete this saved plan?')) return;
        await api(`study-plans/${button.dataset.deletePlan}`, {method:'DELETE'});
        loadSavedPlans();
    }));
};

const loadSavedPlans = async () => {
    const data = await api('study-plans');
    renderSavedPlans(data.plans || []);
};

const addPlanActions = () => {
    const target = document.getElementById('planner-result');
    if (!currentPlan || target.querySelector('[data-save-plan]')) return;
    target.insertAdjacentHTML('beforeend', `<div class="plan-actions"><input id="plan-title" value="${escapeHtml(currentPlan.title || 'My study plan')}" placeholder="Plan name"><button type="button" class="primary-button" data-save-plan>${currentPlan.id ? 'Update saved plan' : 'Save this plan'}</button><span class="plan-save-status" aria-live="polite"></span></div>`);
    target.querySelector('[data-save-plan]').addEventListener('click', async () => {
        const saveButton = target.querySelector('[data-save-plan]');
        const status = target.querySelector('.plan-save-status');
        saveButton.disabled = true;
        status.textContent = 'Saving...';
        try {
            const payload = {title: document.getElementById('plan-title').value, topics: document.getElementById('plan-topics').value, exam_date: document.getElementById('plan-date').value, hours_per_day: document.getElementById('plan-hours').value, plan: currentPlan.plan};
            const endpoint = currentPlan.id ? `study-plans/${currentPlan.id}` : 'study-plans';
            const data = await api(endpoint, {method: currentPlan.id ? 'PATCH' : 'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)});
            currentPlan = data.plan;
            status.textContent = 'Saved';
            saveButton.textContent = 'Update saved plan';
            loadSavedPlans();
        } catch (error) {
            status.textContent = error.message;
        } finally {
            saveButton.disabled = false;
        }
    });
};
let quizState = {questions: [], index: 0, score: 0, answered: false, type: 'mcq'};

const renderQuiz = () => {
    const target = document.getElementById('quiz-result');
    const question = quizState.questions[quizState.index];
    if (!question) {
        target.innerHTML = `<div class="result-card quiz-complete"><span class="eyebrow">QUIZ COMPLETE</span><h3>${quizState.score} / ${quizState.questions.length} correct</h3><p>${quizState.score === quizState.questions.length ? 'Excellent work. You mastered this set.' : 'Good attempt. Review the explanations and try again.'}</p><button class="secondary-button" data-quiz-restart>Try again</button></div>`;
        target.querySelector('[data-quiz-restart]').addEventListener('click', () => {
            quizState = {questions: [], index: 0, score: 0, answered: false, type: 'mcq'};
            target.innerHTML = '';
        });
        return;
    }

    const progress = Math.round((quizState.index / quizState.questions.length) * 100);
    if (quizState.type === 'written') {
        target.innerHTML = `<div class="quiz-card"><div class="quiz-progress"><span>Written question ${quizState.index + 1} of ${quizState.questions.length}</span><span>${quizState.score} reviewed</span></div><div class="quiz-track"><i style="width:${progress}%"></i></div><h3>${escapeHtml(question.question)}</h3><textarea class="test-answer" placeholder="Write your answer here..."></textarea><button class="primary-button" data-check-written>Check answer</button><div class="quiz-feedback" aria-live="polite"></div></div>`;
        target.querySelector('[data-check-written]').addEventListener('click', () => {
            const answer = target.querySelector('.test-answer').value.trim();
            if (!answer) return;
            const feedback = target.querySelector('.quiz-feedback');
            feedback.className = 'quiz-feedback feedback-correct';
            feedback.innerHTML = `<strong>Compare your answer</strong><p><b>Model answer:</b> ${escapeHtml(question.answer)}</p><p><b>Key points:</b> ${escapeHtml((question.key_points || []).join(', '))}</p><button class="primary-button" data-next-question>${quizState.index === quizState.questions.length - 1 ? 'See my progress' : 'Next question'}</button>`;
            feedback.querySelector('[data-next-question]').addEventListener('click', () => { quizState.score += 1; quizState.index += 1; renderQuiz(); });
        });
        return;
    }
    if (quizState.type === 'qa') {
        target.innerHTML = `<div class="quiz-card"><div class="quiz-progress"><span>Q&amp;A ${quizState.index + 1} of ${quizState.questions.length}</span><span>${quizState.score} remembered</span></div><div class="quiz-track"><i style="width:${progress}%"></i></div><h3>${escapeHtml(question.question)}</h3><button class="primary-button" data-reveal-answer>Reveal answer</button><div class="quiz-feedback" aria-live="polite"></div></div>`;
        target.querySelector('[data-reveal-answer]').addEventListener('click', () => {
            const feedback = target.querySelector('.quiz-feedback');
            feedback.className = 'quiz-feedback feedback-correct';
            feedback.innerHTML = `<strong>Answer</strong><p>${escapeHtml(question.answer)}</p><p><b>Memory tip:</b> ${escapeHtml(question.memory_tip || 'Explain it once in your own words.')}</p><button class="secondary-button" data-knew-it>I knew it</button> <button class="primary-button" data-next-question>Next</button>`;
            target.querySelector('[data-knew-it]').addEventListener('click', () => { quizState.score += 1; quizState.index += 1; renderQuiz(); });
            target.querySelector('[data-next-question]').addEventListener('click', () => { quizState.index += 1; renderQuiz(); });
        });
        return;
    }
    target.innerHTML = `<div class="quiz-card"><div class="quiz-progress"><span>Question ${quizState.index + 1} of ${quizState.questions.length}</span><span>${quizState.score} correct</span></div><div class="quiz-track"><i style="width:${progress}%"></i></div><h3>${escapeHtml(question.question)}</h3><div class="quiz-options">${question.options.map((option, optionIndex) => `<button class="quiz-option" data-option-index="${optionIndex}">${escapeHtml(option)}</button>`).join('')}</div><div class="quiz-feedback" aria-live="polite"></div></div>`;

    target.querySelectorAll('.quiz-option').forEach(button => button.addEventListener('click', () => {
        if (quizState.answered) return;
        quizState.answered = true;
        const selected = question.options[Number(button.dataset.optionIndex)];
        const isCorrect = selected === question.correct;
        if (isCorrect) quizState.score += 1;
        target.querySelectorAll('.quiz-option').forEach(optionButton => {
            const value = question.options[Number(optionButton.dataset.optionIndex)];
            optionButton.disabled = true;
            if (value === question.correct) optionButton.classList.add('correct');
            if (value === selected && !isCorrect) optionButton.classList.add('wrong');
        });
        const feedback = target.querySelector('.quiz-feedback');
        feedback.className = `quiz-feedback ${isCorrect ? 'feedback-correct' : 'feedback-wrong'}`;
        feedback.innerHTML = `<strong>${isCorrect ? 'Correct!' : 'Not quite.'}</strong><span>${isCorrect ? 'Great choice.' : `Correct answer: ${escapeHtml(question.correct)}`}</span><p>${escapeHtml(question.explanation || '')}</p><button class="primary-button" data-next-question>${quizState.index === quizState.questions.length - 1 ? 'See my score' : 'Next question'}</button>`;
        feedback.querySelector('[data-next-question]').addEventListener('click', () => {
            quizState.index += 1;
            quizState.answered = false;
            renderQuiz();
        });
    }));
};

const run = async (button, action) => {
    const original = button.textContent; button.disabled = true; button.textContent = 'Working...';
    try { await action(); } catch (error) { const panel = button.closest('.tool-panel').querySelector('.result'); panel.innerHTML = `<div class="result-card error">${escapeHtml(error.message)}</div>`; }
    button.disabled = false; button.textContent = original;
};

document.querySelectorAll('.mode-button, .quick-tool').forEach(button => button.addEventListener('click', () => {
    document.querySelectorAll('.mode-button').forEach(item => item.classList.remove('active'));
    document.querySelectorAll('.tool-panel').forEach(panel => panel.classList.remove('active'));
    button.classList.add('active'); document.querySelector(`[data-panel="${button.dataset.mode}"]`).classList.add('active');
}));

document.querySelectorAll('[data-action]').forEach(button => button.addEventListener('click', () => {
    const action = button.dataset.action;
    run(button, async () => {
        if (action === 'solve') { const data = await api('solve', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({problem:document.getElementById('solve-input').value})}); showResult('solve-result', data.solution, `${data.subject} solution`); }
        if (action === 'scan') { const file = document.getElementById('scan-input').files[0]; const body = new FormData(); body.append('image', file); const data = await api('ocr', {method:'POST', body}); showResult('scan-result', data.text || data.message, 'Extracted text'); }
        if (action === 'flashcards') { const data = await api('flashcards', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({notes:document.getElementById('flash-input').value, topic:document.getElementById('flash-topic').value || 'General'})}); showResult('flashcards-result', JSON.stringify(data.flashcards, null, 2), 'Flashcards'); }
        if (action === 'quiz') {
            const topic = document.getElementById('quiz-input').value;
            const countInput = document.getElementById('quiz-count').value.trim();
            const mentionedCount = topic.match(/\b(\d{1,2})\s*(?:mcqs?|questions?)\b/i);
            const count = countInput || (mentionedCount ? mentionedCount[1] : '5');
            const type = document.getElementById('quiz-type').value;
            const data = await api('quiz', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({topic, count, type})});
            quizState = {questions: data.questions || [], index: 0, score: 0, answered: false, type};
            renderQuiz();
        }
        if (action === 'planner') { const topics = document.getElementById('plan-topics').value; const examDate = document.getElementById('plan-date').value; const hours = document.getElementById('plan-hours').value; const data = await api('study-plan', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({topics, exam_date:examDate, hours_per_day:hours})}); currentPlan = {title:'My study plan', topics, exam_date:examDate, hours_per_day:hours, plan:data.plan}; showResult('planner-result', data.plan, 'Your study plan'); addPlanActions(); loadSavedPlans(); }
        if (action === 'refresh-plans') { await loadSavedPlans(); }
        if (action === 'summarize') { const data = await api('summarize', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({text:document.getElementById('summary-input').value, length:document.getElementById('summary-length').value})}); showResult('summarize-result', data.summary, 'Summary'); }
        if (action === 'formulas') { const data = await api('formulas', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({notes:document.getElementById('formula-input').value})}); showResult('formulas-result', data.formulas, 'Formula sheet'); }
        if (action === 'explain') { const data = await api('explain', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({topic:document.getElementById('explain-input').value, age_group:document.getElementById('explain-audience').value})}); showResult('explain-result', data.explanation, 'Simple explanation'); }
        if (action === 'history') { const data = await api('history'); document.getElementById('history-result').innerHTML = data.history.map(item => `<div class="history-item"><strong>${escapeHtml(item.subject)} · ${escapeHtml(item.created_at)}</strong><span>${escapeHtml(item.problem)}</span></div>`).join('') || '<p>No history yet.</p>'; }
    });
}));

api('history').then(data => {
    document.getElementById('backend-status').textContent = '● Backend connected';
    document.getElementById('solved-count').textContent = String(data.count || 0).padStart(2, '0');
}).catch(() => { document.getElementById('backend-status').textContent = '○ Backend unavailable'; });
