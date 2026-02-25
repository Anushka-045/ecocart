const userInput = document.getElementById('userInput');
const analyzeBtn = document.getElementById('analyzeBtn');
const charCount = document.getElementById('charCount');
const loadingState = document.getElementById('loadingState');
const errorState = document.getElementById('errorState');
const resultsEl = document.getElementById('results');
//final anushka 
userInput.addEventListener('input', () => {
  charCount.textContent = `${userInput.value.length} chars`;
});

analyzeBtn.addEventListener('click', analyze);

async function analyze() {
  const text = userInput.value.trim();
  if (!text) { userInput.focus(); return; }

  // reset
  analyzeBtn.disabled = true;
  loadingState.classList.add('active');
  errorState.classList.remove('active');
  resultsEl.classList.remove('visible');
  resultsEl.innerHTML = '';

  try {
    const response = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: 'claude-sonnet-4-20250514',
        max_tokens: 1000,
        system: `You are an expert sustainability analyst. Analyze the given product description and return ONLY a valid JSON object with no markdown or extra text. The JSON must have these exact keys:
{
  "score": number 0-100,
  "grade": "A"|"B"|"C"|"D"|"F",
  "verdict": "Good"|"Needs Work"|"Poor",
  "summary": "One sentence summary",
  "positive_tags": ["tag1","tag2",...],
  "negative_tags": ["tag1","tag2",...],
  "impacts": ["impact sentence 1", ...],
  "improvements": ["improvement 1", ...],
  "alternatives": ["alternative 1", ...]
}
Score: 0=extremely harmful, 50=average, 100=perfectly sustainable. Be accurate and strict. Grade A=85+, B=70+, C=55+, D=40+, F=below 40.`,
        messages: [{ role: 'user', content: `Analyze this product: ${text}` }]
      })
    });

    const data = await response.json();
    const raw = data.content.map(b => b.text || '').join('');
    const clean = raw.replace(/```json|```/g, '').trim();
    const result = JSON.parse(clean);
    renderResults(result);

  } catch (err) {
    console.error(err);
    errorState.textContent = `⚠️ ${err.message || 'Analysis failed. Please try again.'}`;
    errorState.classList.add('active');
  } finally {
    analyzeBtn.disabled = false;
    loadingState.classList.remove('active');
  }
}

function renderResults(r) {
  const score = Math.min(100, Math.max(0, r.score || 0));
  const scoreColor = score >= 70 ? '' : score >= 45 ? 'yellow' : 'red';
  const verdict = r.verdict || 'Needs Work';
  const verdictClass = verdict === 'Good' ? 'good' : verdict === 'Poor' ? 'bad' : 'okay';
  const verdictEmoji = verdict === 'Good' ? '🌿' : verdict === 'Poor' ? '⚠️' : '🔄';

  const positiveTags = (r.positive_tags || []).map(t =>
    `<span class="tag tag-positive">${t}</span>`).join('');

  const negativeTags = (r.negative_tags || []).map(t =>
    `<span class="tag tag-negative">${t}</span>`).join('');

  const impacts = (r.impacts || []).map(i =>
    `<div class="item-row"><span class="item-dot dot-green"></span>${i}</div>`).join('');

  const improvements = (r.improvements || []).map(i =>
    `<div class="item-row"><span class="item-dot dot-yellow"></span>${i}</div>`).join('');

  const alternatives = (r.alternatives || []).map(a =>
    `<div class="item-row"><span class="item-dot dot-cyan"></span>${a}</div>`).join('');

  resultsEl.innerHTML = `...`; 

  // Animate score counter
  const scoreNumEl = document.getElementById('scoreNum');
  const barEl = document.getElementById('scoreBar');
  const barLabelEl = document.getElementById('barLabel');
  let current = 0;
  const step = score / 60;
  const timer = setInterval(() => {
    current = Math.min(current + step, score);
    scoreNumEl.textContent = Math.round(current);
    barEl.style.width = current + '%';
    barLabelEl.textContent = Math.round(current) + '%';
    if (current >= score) clearInterval(timer);
  }, 16);

  resultsEl.classList.add('visible');
  resultsEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
}