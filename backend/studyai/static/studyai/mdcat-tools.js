const api = async (endpoint, options = {}) => { const method=(options.method || 'GET').toUpperCase(); const headers={'Content-Type':'application/json',...(options.headers || {})}; if(!['GET','HEAD','OPTIONS','TRACE'].includes(method))headers['X-CSRFToken']=document.querySelector('[name="csrfmiddlewaretoken"]')?.value || ''; const response = await fetch(`/api/${endpoint}/`, {...options,headers}); const type = response.headers.get('content-type') || ''; const data = type.includes('application/json') ? await response.json() : null; if (!response.ok || !data) throw new Error(data?.error || 'Request failed.'); return data; };
const escapeHtml = value => String(value || '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[char]));
const tabs = document.querySelectorAll('.tool-tab');
tabs.forEach(tab => tab.addEventListener('click', () => { tabs.forEach(item => item.classList.remove('active')); document.querySelectorAll('.tool-view').forEach(view => view.classList.remove('active')); tab.classList.add('active'); document.querySelector(`[data-view="${tab.dataset.tab}"]`).classList.add('active'); }));
const requestedTab = new URLSearchParams(window.location.search).get('tab');
if (requestedTab) document.querySelector(`.tool-tab[data-tab="${requestedTab}"]`)?.click();

const paperList = document.getElementById('past-paper-list');
const paperYear = document.getElementById('paper-year');
const paperSubject = document.getElementById('paper-subject');
const renderPastPapers = () => {
	const year = paperYear.value;
	const subject = paperSubject.value;
	const query = `Pakistan MDCAT ${year === 'all' ? '' : year} ${subject === 'all' ? '' : subject} past paper`;
	const encodedQuery = encodeURIComponent(query.trim());
	paperList.innerHTML = `<article class="paper-card"><span class="paper-year">${year === 'all' ? 'ALL YEARS' : year}</span><strong>${subject === 'all' ? 'Complete MDCAT paper' : `${subject} practice paper`}</strong><p>Search publicly available papers and confirm the source before downloading.</p><a href="https://www.google.com/search?q=${encodedQuery}" target="_blank" rel="noopener">Find this paper →</a></article><article class="paper-card"><span class="paper-year">YOUTUBE</span><strong>Video walkthroughs</strong><p>Find solved explanations for this year and subject.</p><a href="https://www.youtube.com/results?search_query=${encodedQuery}+solved" target="_blank" rel="noopener">Find walkthroughs →</a></article>`;
};
paperYear.addEventListener('change', renderPastPapers);
paperSubject.addEventListener('change', renderPastPapers);
renderPastPapers();

let test = {items:[], index:0, score:0, title:'', topic:''};
const checkpointKey = 'mdcat-checkpoint';
const saveCheckpoint = () => localStorage.setItem(checkpointKey, JSON.stringify({items:test.items,index:test.index,score:test.score,title:test.title,topic:test.topic,savedAt:Date.now()}));
const clearCheckpoint = () => { localStorage.removeItem(checkpointKey); renderCheckpoint(); };
const renderCheckpoint = () => { const banner=document.getElementById('checkpoint-banner'); if(!banner)return; const saved=JSON.parse(localStorage.getItem(checkpointKey) || 'null'); if(!saved?.items?.length){banner.hidden=true;return;} banner.hidden=false; banner.innerHTML=`<strong>Checkpoint available</strong><span>${escapeHtml(saved.title || 'Practice test')} · question ${Math.min(saved.index + 1,saved.items.length)} of ${saved.items.length}</span><button class="primary-button" data-restore-checkpoint>Restore Checkpoint</button><button class="checkpoint-dismiss" data-dismiss-checkpoint aria-label="Dismiss checkpoint">×</button>`; banner.querySelector('[data-restore-checkpoint]').addEventListener('click',()=>{test={...saved};renderTest(practiceResult,saved.title || 'Practice test');}); banner.querySelector('[data-dismiss-checkpoint]').addEventListener('click',clearCheckpoint); };
const practiceResult = document.getElementById('practice-result');
const recordWrongAnswer = (topic, item) => { const mistakes=JSON.parse(localStorage.getItem('mdcat-mistakes') || '[]'); mistakes.unshift({topic,question:item.question,note:`Correct answer: ${item.correct}. ${item.explanation || ''}`,createdAt:Date.now()}); localStorage.setItem('mdcat-mistakes',JSON.stringify(mistakes.slice(0,50))); };
const recordAnswer = (topic, correct) => { const stats=JSON.parse(localStorage.getItem('mdcat-topic-stats') || '{}'); const stat=stats[topic] || {attempts:0,correct:0,wrong:0}; stat.attempts += 1; stat[correct ? 'correct' : 'wrong'] += 1; stats[topic]=stat; localStorage.setItem('mdcat-topic-stats',JSON.stringify(stats)); };
const renderTest = (target, title) => { const item = test.items[test.index]; if (!item) { target.innerHTML = `<div class="result-card"><h3>${title} complete</h3><p>Score: <strong>${test.score}/${test.items.length}</strong></p><button class="primary-button" data-reset-test>Start again</button></div>`; target.querySelector('[data-reset-test]').addEventListener('click', () => {target.innerHTML='';}); return; } target.innerHTML = `<div class="quiz-card"><div class="quiz-progress"><span>${title} · ${test.index + 1}/${test.items.length}</span><span>${test.score} correct</span></div><div class="quiz-track"><i style="width:${(test.index / test.items.length) * 100}%"></i></div><h3>${escapeHtml(item.question)}</h3><div class="quiz-options">${(item.options || []).map((option,index) => `<button class="quiz-option" data-choice="${index}">${escapeHtml(option)}</button>`).join('')}</div><div class="quiz-feedback"></div></div>`; target.querySelectorAll('.quiz-option').forEach(button => button.addEventListener('click', () => { const selected = item.options[Number(button.dataset.choice)]; const correct = selected === item.correct; if (correct) test.score += 1; target.querySelectorAll('.quiz-option').forEach(option => { option.disabled=true; if(option.textContent === item.correct) option.classList.add('correct'); if(option === button && !correct) option.classList.add('wrong'); }); const feedback=target.querySelector('.quiz-feedback'); feedback.className=`quiz-feedback ${correct?'feedback-correct':'feedback-wrong'}`; feedback.innerHTML=`<strong>${correct?'Correct!':'Review this one.'}</strong><p>${correct?'Nice work.':`Correct answer: ${escapeHtml(item.correct)}`}</p><p>${escapeHtml(item.explanation || '')}</p><button class="primary-button" data-next>${test.index === test.items.length-1?'See score':'Next question'}</button>`; feedback.querySelector('[data-next]').addEventListener('click',()=>{test.index += 1;renderTest(target,title);}); })); };

const startTest = async (topic, count, target, title) => { target.innerHTML='<div class="saved-empty">Preparing your questions...</div>'; try { const data=await api('quiz',{method:'POST',body:JSON.stringify({topic,count,type:'mcq'})}); test={items:data.questions || [],index:0,score:0}; renderTest(target,title); return true; } catch(error) { target.innerHTML=`<div class="result-card error">${escapeHtml(error.message)}</div>`; return false; } };
document.querySelectorAll('[data-practice-subject]').forEach(button => button.addEventListener('click', () => { const topic=`MDCAT ${button.dataset.practiceSubject}`; const title=`${button.dataset.practiceSubject} practice`; startTest(topic,10,practiceResult,title).then(()=>{test.topic=topic;test.title=title;saveCheckpoint();}); }));
document.addEventListener('click', event => { const button=event.target.closest('.quiz-option'); if(!button || !test.items[test.index])return; const item=test.items[test.index]; const correct=item.options[Number(button.dataset.choice)] === item.correct; recordAnswer(test.topic,correct); if(!correct)recordWrongAnswer(test.topic,item); saveCheckpoint(); });
setInterval(() => { if(test.items.length && test.index < test.items.length) saveCheckpoint(); }, 1000);
renderCheckpoint();

const topicCoachForm = document.getElementById('topic-coach-form');
const topicCoachResult = document.getElementById('topic-coach-result');
const renderTopicGuide = guide => {
	const questions = guide.mcqs || [];
	topicCoachResult.innerHTML = `<article class="topic-guide"><div class="topic-guide-heading"><span class="eyebrow">${escapeHtml(guide.topic || 'Topic')}</span><h3>Concept explanation</h3></div><div class="topic-explanation">${escapeHtml(guide.explanation || '').replace(/\n/g, '<br>')}</div><h3>Key points</h3><ul class="topic-key-points">${(guide.key_points || []).map(point => `<li>${escapeHtml(point)}</li>`).join('')}</ul><h3>Practice MCQs</h3><div class="topic-mcqs">${questions.map((item, index) => `<article class="topic-mcq"><strong>${index + 1}. ${escapeHtml(item.question)}</strong><div class="topic-options">${(item.options || []).map(option => `<span>${escapeHtml(option)}</span>`).join('')}</div><details><summary>Show answer</summary><p><b>${escapeHtml(item.correct)}</b></p><p>${escapeHtml(item.explanation || '')}</p></details></article>`).join('')}</div></article>`;
};
topicCoachForm.addEventListener('submit', async event => {
	event.preventDefault();
	const topic = document.getElementById('topic-query').value.trim();
	const difficulty = document.getElementById('topic-difficulty').value;
	if (!topic) return;
	topicCoachResult.innerHTML = '<div class="saved-empty">Preparing your explanation and MCQs...</div>';
	try {
		const guide = await api('topic-study-guide', {method:'POST', body:JSON.stringify({topic, difficulty})});
		renderTopicGuide(guide);
	} catch (error) {
		topicCoachResult.innerHTML = `<div class="result-card error">${escapeHtml(error.message)}</div>`;
	}
});

const tutorChatForm = document.getElementById('tutor-chat-form');
const tutorChatMessages = document.getElementById('tutor-chat-messages');
const tutorHistory = JSON.parse(localStorage.getItem('mdcat-tutor-history') || '[]');
const cleanTutorText = value => String(value || '')
	.replace(/\\text\{([^{}]*)\}/g, '$1')
	.replace(/\\(?:alpha|beta|gamma|delta|theta|mu|pi|rightarrow|to|times|cdot|circ|left|right|rightarrow)/g, '')
	.replace(/\\[a-zA-Z]+/g, '')
	.replace(/\$\$?/g, '')
	.replace(/^\s*#{1,6}\s*/gm, '')
	.replace(/^\s*[-*_]{3,}\s*$/gm, '')
	.replace(/[`*]/g, '')
	.replace(/\\/g, '')
	.replace(/\n{3,}/g, '\n\n')
	.trim();
const renderTutorChat = () => { tutorChatMessages.innerHTML=tutorHistory.map(item=>`<div class="tutor-message ${item.role === 'user' ? 'user' : 'assistant'}"><span>${item.role === 'user' ? 'You' : 'StudyAI Tutor'}</span><p>${escapeHtml(cleanTutorText(item.content)).replace(/\n/g,'<br>')}</p></div>`).join('') || '<div class="saved-empty">Ask about a concept, formula, question, or revision strategy.</div>'; tutorChatMessages.scrollTop=tutorChatMessages.scrollHeight; };
document.getElementById('clear-tutor-history').addEventListener('click', () => { tutorHistory.splice(0, tutorHistory.length); localStorage.removeItem('mdcat-tutor-history'); renderTutorChat(); });
tutorChatForm.addEventListener('submit', async event => { event.preventDefault(); const message=document.getElementById('tutor-chat-message').value.trim(); const topic=document.getElementById('tutor-chat-topic').value.trim(); if(!message)return; tutorHistory.push({role:'user',content:message}); renderTutorChat(); document.getElementById('tutor-chat-message').value=''; const pending={role:'assistant',content:'Thinking through this...'}; tutorHistory.push(pending); renderTutorChat(); try { const data=await api('mdcat-chat',{method:'POST',body:JSON.stringify({message,topic,history:tutorHistory.slice(0,-1)})}); pending.content=data.reply || 'I could not prepare a response.'; } catch(error) { pending.content=`Error: ${error.message}`; } localStorage.setItem('mdcat-tutor-history',JSON.stringify(tutorHistory.slice(-20))); renderTutorChat(); });
renderTutorChat();

let mockTimer;
document.getElementById('start-mock').addEventListener('click', async () => { clearInterval(mockTimer); const count=Number(document.getElementById('mock-count').value); const minutes=Number(document.getElementById('mock-minutes').value); const result=document.getElementById('mock-result'); const loaded=await startTest('MDCAT mixed subjects',count,result,'Timed mock'); if(!loaded)return; result.insertAdjacentHTML('afterbegin',`<div class="mock-clock">Time remaining: <strong id="mock-time">${minutes}:00</strong></div>`); let seconds=minutes*60; mockTimer=setInterval(()=>{seconds -= 1; const clock=document.getElementById('mock-time'); if(!clock) return clearInterval(mockTimer); clock.textContent=`${Math.floor(seconds/60)}:${String(seconds%60).padStart(2,'0')}`; if(seconds<=0){clearInterval(mockTimer); clock.textContent='Time up';}},1000);});

const syllabus = {Biology:['Cell biology','Biological molecules','Genetics','Human physiology','Ecology'],Chemistry:['Basic concepts','Atomic structure','Chemical bonding','Organic chemistry','Solutions'],Physics:['Measurements','Force and motion','Work and energy','Electricity','Waves'],English:['Vocabulary','Grammar','Sentence correction','Reading comprehension','Punctuation']};
const syllabusState=JSON.parse(localStorage.getItem('mdcat-syllabus') || '{}'); const syllabusList=document.getElementById('syllabus-list');
const renderSyllabus=()=>{let total=0,done=0; syllabusList.innerHTML=Object.entries(syllabus).map(([subject,topics])=>`<div class="syllabus-group"><h3>${subject}</h3>${topics.map(topic=>{const key=`${subject}:${topic}`;total+=1;if(syllabusState[key])done+=1;return `<label><input type="checkbox" data-syllabus="${key}" ${syllabusState[key]?'checked':''}>${topic}</label>`;}).join('')}</div>`).join(''); document.getElementById('readiness-score').textContent=`${total?Math.round(done/total*100):0}%`; syllabusList.querySelectorAll('[data-syllabus]').forEach(box=>box.addEventListener('change',()=>{syllabusState[box.dataset.syllabus]=box.checked;localStorage.setItem('mdcat-syllabus',JSON.stringify(syllabusState));renderSyllabus();}));}; renderSyllabus();

const mistakesKey='mdcat-mistakes'; let mistakes=JSON.parse(localStorage.getItem(mistakesKey) || '[]'); const mistakeList=document.getElementById('mistake-list'); const renderMistakes=()=>{mistakeList.innerHTML=mistakes.map((item,index)=>`<article class="mistake-card"><strong>${escapeHtml(item.topic)}</strong><p>${escapeHtml(item.note)}</p><button data-remove-mistake="${index}">Mark reviewed / remove</button></article>`).join('') || '<div class="saved-empty">Your mistake notebook is empty.</div>'; mistakeList.querySelectorAll('[data-remove-mistake]').forEach(button=>button.addEventListener('click',()=>{mistakes.splice(Number(button.dataset.removeMistake),1);localStorage.setItem(mistakesKey,JSON.stringify(mistakes));renderMistakes();}));}; renderMistakes();
document.getElementById('save-mistake').addEventListener('click',()=>{const topic=document.getElementById('mistake-topic').value.trim();const note=document.getElementById('mistake-note').value.trim();if(!topic)return;mistakes.unshift({topic,note});localStorage.setItem(mistakesKey,JSON.stringify(mistakes));document.getElementById('mistake-topic').value='';document.getElementById('mistake-note').value='';renderMistakes();});
