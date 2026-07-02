document.querySelectorAll('#tabs button').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('#tabs button').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById(btn.dataset.tab).classList.add('active');
    if (btn.dataset.tab === 'dashboard') loadDashboard();
  });
});

async function checkAuth() {
  const res = await fetch('/api/me');
  const data = await res.json();
  document.getElementById('auth-status').textContent = data.logged_in
    ? `Logged in as ${data.username}` : 'Not logged in';
}
checkAuth();

document.getElementById('analyze-btn').addEventListener('click', async () => {
  const fileInput = document.getElementById('resume-file');
  const jd = document.getElementById('jd-text').value;
  if (!fileInput.files.length) return alert('Please choose a resume file.');

  const formData = new FormData();
  formData.append('resume', fileInput.files[0]);
  if (jd.trim()) formData.append('job_description', jd);

  const res = await fetch('/api/analyze', { method: 'POST', body: formData });
  const data = await res.json();
  const out = document.getElementById('analyze-result');
  if (data.error) { out.innerHTML = `<p class="error">${data.error}</p>`; return; }

  let html = `<h3>${data.name} — ATS Score: ${data.ats_score}/100</h3>`;
  html += `<h4>Suggestions</h4><ul>${data.suggestions.map(s => `<li>${s}</li>`).join('')}</ul>`;
  if (data.jd_match) {
    html += `<h4>Job Description Match: ${data.jd_match.match_percentage}%</h4>`;
    html += `<p><strong>Matched:</strong> ${data.jd_match.matched_skills.join(', ') || 'none'}</p>`;
    html += `<p><strong>Missing (skill gap):</strong> ${data.jd_match.missing_skills.join(', ') || 'none'}</p>`;
  }
  out.innerHTML = html;
});

document.getElementById('bulk-btn').addEventListener('click', async () => {
  const files = document.getElementById('bulk-files').files;
  const jd = document.getElementById('bulk-jd-text').value;
  if (!files.length) return alert('Please choose at least one resume.');

  const formData = new FormData();
  for (const f of files) formData.append('resumes', f);
  if (jd.trim()) formData.append('job_description', jd);

  const res = await fetch('/api/bulk', { method: 'POST', body: formData });
  const data = await res.json();
  const out = document.getElementById('bulk-result');

  let html = '<table><tr><th>Rank</th><th>Name</th><th>Score</th><th>Skills</th></tr>';
  data.results.forEach(r => {
    html += `<tr><td>${r.rank}</td><td>${r.name}</td><td>${r.overall_score}</td><td>${(r.skills||[]).join(', ')}</td></tr>`;
  });
  html += '</table>';
  out.innerHTML = html;
});

document.getElementById('login-btn').addEventListener('click', async () => {
  const username = document.getElementById('login-username').value;
  const password = document.getElementById('login-password').value;
  const res = await fetch('/api/login', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
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
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ username, password })
  });
  const data = await res.json();
  document.getElementById('auth-message').textContent = data.message || data.error;
});

async function loadDashboard() {
  const res = await fetch('/api/dashboard');
  const data = await res.json();
  if (data.error) {
    document.getElementById('dashboard-stats').innerHTML = `<p class="error">${data.error}</p>`;
    return;
  }
  document.getElementById('dashboard-stats').innerHTML =
    `<p>Total resumes parsed: ${data.total_parsed} | Average ATS score: ${data.avg_score}</p>`;

  const ctx = document.getElementById('skills-chart');
  if (window.skillsChart) window.skillsChart.destroy();
  window.skillsChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: data.top_skills.map(s => s.skill),
      datasets: [{ label: 'Frequency', data: data.top_skills.map(s => s.count) }]
    }
  });
}
