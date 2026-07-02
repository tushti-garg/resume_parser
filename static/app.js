// ---------- Navigation ----------
document.querySelectorAll('.nav-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById(btn.dataset.page).classList.add('active');
    if (btn.dataset.page === 'dashboard') loadDashboard();
  });
});

async function checkAuth() {
  const res = await fetch('/api/me');
  const data = await res.json();
  document.getElementById('auth-status').textContent = data.logged_in
    ? `Logged in as ${data.username}` : 'Not logged in';
}
checkAuth();

function scoreRing(score) {
  return `<div class="score-ring" style="--pct:${score}"><span>${score}</span></div>`;
}

// ---------- Candidate ----------
document.getElementById('analyze-btn').addEventListener('click', async () => {
  const fileInput = document.getElementById('resume-file');
  const role = document.getElementById('custom-role').value.trim() || document.getElementById('target-role').value;
  if (!fileInput.files.length) return alert('Please choose a resume file.');

  const out = document.getElementById('analyze-result');
  out.innerHTML = '<div class="skeleton"></div>';

  const formData = new FormData();
  formData.append('resume', fileInput.files[0]);
  if (role) formData.append('target_role', role);

  const res = await fetch('/api/candidate/analyze', { method: 'POST', body: formData });
  const data = await res.json();
  if (data.error) { out.innerHTML = `<p class="error">${data.error}</p>`; return; }

  let html = `<div class="card"><div style="display:flex; gap:1.2rem; align-items:center;">
    ${scoreRing(data.ats_score)}
    <div><div class="result-name">${data.name}</div>
    <div class="hint">${data.target_role ? 'Targeting: ' + data.target_role : 'General ATS score'}</div></div>
  </div>`;

  if (data.matched_skills.length || data.missing_skills.length) {
    html += `<h3>Skill match</h3>`;
    data.matched_skills.forEach(s => html += `<span class="badge match">${s}</span>`);
    data.missing_skills.forEach(s => html += `<span class="badge missing">${s}</span>`);
  }

  html += `<h3>Feedback</h3><p class="result-explanation">${data.improvement_feedback}</p></div>`;
  out.innerHTML = html;
});

// ---------- Recruiter: skill rows ----------
function addSkillRow(skill = '', weight = 3) {
  const row = document.createElement('div');
  row.className = 'skill-row';
  row.innerHTML = `
    <input type="text" class="skill-name" placeholder="e.g. python" value="${skill}">
    <input type="range" class="skill-weight" min="1" max="5" value="${weight}">
    <span class="weight-label">${weight}</span>
    <button class="ghost remove-skill">✕</button>`;
  row.querySelector('.skill-weight').addEventListener('input', e => {
    row.querySelector('.weight-label').textContent = e.target.value;
  });
  row.querySelector('.remove-skill').addEventListener('click', () => row.remove());
  document.getElementById('skill-rows').appendChild(row);
}
addSkillRow(); addSkillRow(); addSkillRow();
document.getElementById('add-skill-row').addEventListener('click', () => addSkillRow());

document.getElementById('tab-create-job').addEventListener('click', () => {
  document.getElementById('create-job-panel').style.display = 'block';
  document.getElementById('my-jobs-panel').style.display = 'none';
  document.getElementById('upload-panel').style.display = 'none';
});
document.getElementById('tab-my-jobs').addEventListener('click', () => {
  document.getElementById('create-job-panel').style.display = 'none';
  document.getElementById('my-jobs-panel').style.display = 'block';
  document.getElementById('upload-panel').style.display = 'none';
  loadJobs();
});

document.getElementById('create-job-btn').addEventListener('click', async () => {
  const title = document.getElementById('job-title').value.trim();
  const minExp = parseInt(document.getElementById('job-min-exp').value, 10);
  const expWeight = parseInt(document.getElementById('job-exp-weight').value, 10);
  const skills = [...document.querySelectorAll('.skill-row')].map(row => ({
    skill: row.querySelector('.skill-name').value.trim().toLowerCase(),
    weight: parseInt(row.querySelector('.skill-weight').value, 10),
  })).filter(s => s.skill);

  if (!title || !skills.length) return alert('Add a title and at least one skill.');

  const res = await fetch('/api/recruiter/jobs', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, skills, min_experience_years: minExp, experience_weight: expWeight })
  });
  const data = await res.json();
  if (data.error) return alert(data.error);
  alert('Job posting created. Switch to "My job postings" to upload resumes.');
});

async function loadJobs() {
  const res = await fetch('/api/recruiter/jobs');
  const jobs = await res.json();
  const list = document.getElementById('jobs-list');
  if (!jobs.length) { list.innerHTML = '<p class="hint">No job postings yet.</p>'; return; }
  list.innerHTML = jobs.map(j => `
    <div class="result-row">
      <div class="result-main">
        <div class="result-name">${j.title}</div>
        <div class="hint">Min experience: ${j.min_experience_years} yrs</div>
      </div>
      <button class="ghost" onclick="openUpload(${j.id}, '${j.title.replace(/'/g, "\\'")}')">Upload resumes</button>
    </div>`).join('');
}

function openUpload(jobId, title) {
  document.getElementById('upload-panel').style.display = 'block';
  document.getElementById('upload-job-title').textContent = `Upload candidates for: ${title}`;
  document.getElementById('bulk-btn').dataset.jobId = jobId;
}

document.getElementById('bulk-btn').addEventListener('click', async function () {
  const jobId = this.dataset.jobId;
  const files = document.getElementById('bulk-files').files;
  if (!files.length) return alert('Choose resume files.');

  const out = document.getElementById('bulk-result');
  out.innerHTML = '<div class="skeleton"></div><div class="skeleton" style="margin-top:8px;"></div>';

  const formData = new FormData();
  for (const f of files) formData.append('resumes', f);

  const res = await fetch(`/api/recruiter/jobs/${jobId}/upload`, { method: 'POST', body: formData });
  const data = await res.json();
  if (data.error) { out.innerHTML = `<p class="error">${data.error}</p>`; return; }

  let html = `<p class="hint">${data.qualified.length} of ${data.total} candidates meet the requirements.</p>`;
  data.all_results.forEach(r => {
    html += `<div class="result-row">
      ${scoreRing(r.fit_score)}
      <div class="result-main">
        <div class="result-name">${r.name} <span class="badge ${r.qualifies ? 'qualified' : 'notqualified'}">${r.qualifies ? 'Qualified' : 'Not qualified'}</span></div>
        ${r.matched_skills.map(s => `<span class="badge match">${s}</span>`).join('')}
        ${r.missing_skills.map(s => `<span class="badge missing">${s}</span>`).join('')}
        ${r.explanation ? `<p class="result-explanation">${r.explanation}</p>` : ''}
      </div>
    </div>`;
  });
  out.innerHTML = html;
});

// ---------- Auth ----------
document.getElementById('login-btn').addEventListener('click', async () => {
  const username = document.getElementById('login-username').value;
  const password = document.getElementById('login-password').value;
  const res = await fetch('/api/login', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password })
  });
  const data = await res.json();
  document.getElementById('auth-message').textContent = data.message || data.error;
  checkAuth();
});

document.getElementById('register-btn').addEventListener('click', async () => {
  const username = document.getElementById('register-username').value;
  const password = document.getElementById('register-password').value;
  const res = await fetch('/api/register', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password })
  });
  const data = await res.json();
  document.getElementById('auth-message').textContent = data.message || data.error;
});

// ---------- Dashboard ----------
async function loadDashboard() {
  const container = document.getElementById('dashboard-content');
  container.innerHTML = '<div class="skeleton"></div>';
  const res = await fetch('/api/dashboard');
  if (res.status === 401) {
    container.innerHTML = '<p class="hint">Log in to see your history and analytics.</p>';
    return;
  }
  const data = await res.json();

  let html = `<div class="metric-grid">
    <div class="metric-card"><p class="metric-label">Total parsed</p><p class="metric-value">${data.total_parsed}</p></div>
    <div class="metric-card"><p class="metric-label">Average ATS score</p><p class="metric-value">${data.avg_score}</p></div>
    <div class="metric-card"><p class="metric-label">Top skill</p><p class="metric-value">${data.top_skills[0]?.skill || '—'}</p></div>
  </div>
  <div class="card"><div style="position:relative; height:280px;">
    <canvas id="skills-chart" role="img" aria-label="Bar chart of most frequent skills across your parsed resumes"></canvas>
  </div></div>`;
  container.innerHTML = html;

  if (window.skillsChart) window.skillsChart.destroy();
  window.skillsChart = new Chart(document.getElementById('skills-chart'), {
    type: 'bar',
    data: {
      labels: data.top_skills.map(s => s.skill),
      datasets: [{ label: 'Frequency', data: data.top_skills.map(s => s.count), backgroundColor: '#7c5cff', borderRadius: 4 }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: '#9aa5bd' }, grid: { display: false } },
        y: { ticks: { color: '#9aa5bd' }, grid: { color: '#2a3348' } }
      }
    }
  });
                          }
