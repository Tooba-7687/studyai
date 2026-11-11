const practiceTarget = document.getElementById('mdcat-practice');
const subjectDescriptions = {
    Biology: 'Start with a focused Biology MCQ set covering concepts, diagrams, and terminology.',
    Chemistry: 'Start with a focused Chemistry MCQ set covering reactions, equations, and numericals.',
    Physics: 'Start with a focused Physics MCQ set covering formulas, logic, and problem solving.',
    English: 'Start with a focused English MCQ set covering vocabulary, grammar, and comprehension.'
};

document.querySelectorAll('[data-subject]').forEach(button => button.addEventListener('click', () => {
    const subject = button.dataset.subject;
    practiceTarget.innerHTML = `<div class="result-card"><h3>${subject} practice</h3><p>${subjectDescriptions[subject]}</p><a class="primary-button" href="/mdcat-tools/?subject=${encodeURIComponent(subject)}">Open MDCAT Study Tools</a></div>`;
}));

const targetDate = document.getElementById('target-date');
const daysTarget = document.getElementById('mdcat-days');
const parseDateOnly = value => {
    const [year, month, day] = value.split('-').map(Number);
    return Date.UTC(year, month - 1, day);
};
const updateCountdown = () => {
    if (!targetDate.value) return;
    const today = new Date();
    const todayUtc = Date.UTC(today.getFullYear(), today.getMonth(), today.getDate());
    const difference = Math.round((parseDateOnly(targetDate.value) - todayUtc) / 86400000);
    daysTarget.textContent = difference >= 0 ? `${difference} days left` : 'Date passed';
};
targetDate.addEventListener('change', updateCountdown);
updateCountdown();
