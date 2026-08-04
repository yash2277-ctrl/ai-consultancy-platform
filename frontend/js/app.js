/**
 * app.js — Main application controller.
 * Manages views, projects, files, consultations, and report rendering.
 */

class App {
    constructor() {
        this.currentView = 'dashboard';
        this.projects = [];
        this.currentProject = null;
        this.currentReportContext = null; // 'projects' or 'reports'
        this.pollingIntervals = {};
    }

    // ══════════════════════════════════════════════════════════════════
    //  INITIALISATION
    // ══════════════════════════════════════════════════════════════════

    async init() {
        auth.init();

        // Loading screen
        setTimeout(async () => {
            const loggedIn = await auth.checkSession();
            document.getElementById('loading-screen').classList.add('fade-out');
            setTimeout(() => {
                document.getElementById('loading-screen').classList.add('hidden');
                if (loggedIn) {
                    this.onAuthenticated(auth.user);
                } else {
                    document.getElementById('auth-screen').classList.remove('hidden');
                }
            }, 500);
        }, 1200);

        this.bindEvents();
    }

    bindEvents() {
        // Sidebar nav
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', e => {
                e.preventDefault();
                this.switchView(item.dataset.view);
            });
        });

        // Sidebar toggle (mobile)
        document.getElementById('sidebar-toggle').addEventListener('click', () => {
            document.querySelector('.sidebar').classList.toggle('open');
        });

        // Theme toggle
        document.getElementById('theme-toggle').addEventListener('click', () => this.toggleTheme());

        // Logout
        document.getElementById('logout-btn').addEventListener('click', () => this.logout());

        // New project
        document.getElementById('btn-new-project').addEventListener('click', () => this.openModal('modal-new-project'));
        document.getElementById('form-new-project').addEventListener('submit', e => this.createProject(e));

        // Upload
        document.getElementById('btn-upload-file').addEventListener('click', () => this.openModal('modal-upload'));
        this.initUploadZone();

        // Consult from project detail
        document.getElementById('btn-start-consult').addEventListener('click', () => this.openModal('modal-consult'));
        document.getElementById('form-quick-consult').addEventListener('submit', e => this.quickConsult(e));

        // Delete project
        document.getElementById('btn-delete-project').addEventListener('click', () => this.deleteProject());

        // Consult from consult view
        document.getElementById('btn-run-consult').addEventListener('click', () => this.runConsultation());

        // Modal close
        document.querySelectorAll('.modal-overlay, .modal-close').forEach(el => {
            el.addEventListener('click', () => this.closeAllModals());
        });
    }

    // ══════════════════════════════════════════════════════════════════
    //  AUTH & SESSION
    // ══════════════════════════════════════════════════════════════════

    onAuthenticated(user) {
        document.getElementById('auth-screen').classList.add('hidden');
        document.getElementById('app-screen').classList.remove('hidden');
        document.getElementById('user-name').textContent = user.full_name;
        document.getElementById('user-email').textContent = user.email;
        this.switchView('dashboard');
        this.loadDashboard();
    }

    logout() {
        auth.logout();
        // Clear polling
        Object.values(this.pollingIntervals).forEach(clearInterval);
        this.pollingIntervals = {};
        document.getElementById('app-screen').classList.add('hidden');
        document.getElementById('auth-screen').classList.remove('hidden');
    }

    // ══════════════════════════════════════════════════════════════════
    //  THEME
    // ══════════════════════════════════════════════════════════════════

    toggleTheme() {
        const html = document.documentElement;
        const current = html.getAttribute('data-theme');
        const next = current === 'dark' ? 'light' : 'dark';
        html.setAttribute('data-theme', next);
        const icon = document.querySelector('#theme-toggle i');
        icon.className = next === 'dark' ? 'fas fa-moon' : 'fas fa-sun';
    }

    // ══════════════════════════════════════════════════════════════════
    //  VIEW SWITCHING
    // ══════════════════════════════════════════════════════════════════

    switchView(view) {
        this.currentView = view;
        document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
        document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));

        const viewEl = document.getElementById(`view-${view}`);
        if (viewEl) viewEl.classList.add('active');

        const navEl = document.querySelector(`.nav-item[data-view="${view}"]`);
        if (navEl) navEl.classList.add('active');

        const titles = {
            dashboard: ['Dashboard', 'Overview of your AI consultancy workspace'],
            projects: ['Projects', 'Manage your consulting projects'],
            'project-detail': ['Project Details', 'Files, reports, and AI consultations'],
            consult: ['AI Consultation', 'Launch a new AI-powered consulting analysis'],
            reports: ['Reports', 'All generated consulting reports'],
            'report-detail': ['Report', 'Detailed AI consulting analysis'],
        };
        const [title, subtitle] = titles[view] || ['', ''];
        document.getElementById('view-title').textContent = title;
        document.getElementById('view-subtitle').textContent = subtitle;

        // Load data for view
        if (view === 'dashboard') this.loadDashboard();
        if (view === 'projects') this.loadProjects();
        if (view === 'consult') this.loadConsultView();
        if (view === 'reports') this.loadAllReports();

        // Close mobile sidebar
        document.querySelector('.sidebar').classList.remove('open');
    }

    // ══════════════════════════════════════════════════════════════════
    //  DASHBOARD
    // ══════════════════════════════════════════════════════════════════

    async loadDashboard() {
        try {
            this.projects = await api.listProjects();
            const totalFiles = this.projects.reduce((s, p) => s + (p.file_count || 0), 0);
            const totalReports = this.projects.reduce((s, p) => s + (p.report_count || 0), 0);

            document.getElementById('stat-projects').textContent = this.projects.length;
            document.getElementById('stat-files').textContent = totalFiles;
            document.getElementById('stat-reports').textContent = totalReports;
            // Count completed reports accurately
            let completedReports = 0;
            for (const p of this.projects) {
                if (p.report_count > 0) {
                    try {
                        const reps = await api.listReports(p.id);
                        completedReports += reps.filter(r => r.status === 'completed').length;
                    } catch { /* ignore */ }
                }
            }
            document.getElementById('stat-completed').textContent = completedReports;

            // Recent projects
            const recentEl = document.getElementById('recent-projects');
            if (this.projects.length === 0) {
                recentEl.innerHTML = '<div class="empty-state"><i class="fas fa-folder-plus"></i><p>No projects yet.</p></div>';
            } else {
                recentEl.innerHTML = this.projects.slice(0, 5).map(p => `
                    <div class="report-list-item" onclick="app.openProject('${p.id}')">
                        <div class="report-list-info">
                            <h5>${this.esc(p.name)}</h5>
                            <p>${p.file_count} files · ${p.report_count} reports · ${p.industry || 'General'}</p>
                        </div>
                        <i class="fas fa-chevron-right" style="color: var(--text-muted)"></i>
                    </div>
                `).join('');
            }

            // Recent reports placeholder
            const reportsEl = document.getElementById('recent-reports');
            if (this.projects.length > 0 && totalReports > 0) {
                // Show first project's reports
                const firstProjectWithReports = this.projects.find(p => p.report_count > 0);
                if (firstProjectWithReports) {
                    const reports = await api.listReports(firstProjectWithReports.id);
                    reportsEl.innerHTML = reports.slice(0, 5).map(r => `
                        <div class="report-list-item" onclick="app.openReport('${r.id}', 'dashboard')">
                            <div class="report-list-info">
                                <h5>${this.esc(r.goal_statement.substring(0, 80))}${r.goal_statement.length > 80 ? '…' : ''}</h5>
                                <p>${new Date(r.created_at).toLocaleDateString()} · <span class="status-badge ${r.status}">${r.status.replace('_', ' ')}</span></p>
                            </div>
                            <i class="fas fa-chevron-right" style="color: var(--text-muted)"></i>
                        </div>
                    `).join('');
                }
            } else {
                reportsEl.innerHTML = '<div class="empty-state"><i class="fas fa-chart-pie"></i><p>No reports generated yet.</p></div>';
            }
        } catch (err) {
            this.toast('error', 'Failed to load dashboard: ' + err.message);
        }
    }

    // ══════════════════════════════════════════════════════════════════
    //  PROJECTS
    // ══════════════════════════════════════════════════════════════════

    async loadProjects() {
        try {
            this.projects = await api.listProjects();
            const container = document.getElementById('projects-list');
            if (this.projects.length === 0) {
                container.innerHTML = `<div class="empty-state-lg"><i class="fas fa-folder-open"></i><h3>No projects yet</h3><p>Create your first project to get started.</p></div>`;
                return;
            }
            container.innerHTML = this.projects.map(p => `
                <div class="project-card" onclick="app.openProject('${p.id}')">
                    <h4>${this.esc(p.name)}</h4>
                    <p class="project-desc">${this.esc(p.description || 'No description')}</p>
                    <div class="project-meta">
                        ${p.industry ? `<span class="badge">${p.industry}</span>` : ''}
                        <span><i class="fas fa-file-alt"></i> ${p.file_count} files</span>
                        <span><i class="fas fa-chart-bar"></i> ${p.report_count} reports</span>
                    </div>
                </div>
            `).join('');
        } catch (err) {
            this.toast('error', err.message);
        }
    }

    async createProject(e) {
        e.preventDefault();
        const payload = {
            name: document.getElementById('np-name').value,
            industry: document.getElementById('np-industry').value || null,
            description: document.getElementById('np-desc').value || null,
        };
        try {
            await api.createProject(payload);
            this.closeAllModals();
            document.getElementById('form-new-project').reset();
            this.toast('success', 'Project created!');
            this.loadProjects();
        } catch (err) {
            this.toast('error', err.message);
        }
    }

    async openProject(id) {
        try {
            this.currentProject = await api.getProject(id);
            document.getElementById('detail-project-name').textContent = this.currentProject.name;
            document.getElementById('detail-project-desc').textContent = this.currentProject.description || 'No description';
            document.getElementById('detail-project-industry').textContent = this.currentProject.industry || 'General';
            this.switchView('project-detail');
            this.loadProjectFiles();
            this.loadProjectReports();
        } catch (err) {
            this.toast('error', err.message);
        }
    }

    async deleteProject() {
        if (!this.currentProject) return;
        if (!confirm(`Delete project "${this.currentProject.name}"?\n\nThis will permanently delete all files and reports. This cannot be undone.`)) return;

        const btn = document.getElementById('btn-delete-project');
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

        try {
            await api.deleteProject(this.currentProject.id);
            this.toast('success', 'Project deleted');
            this.currentProject = null;
            this.switchView('projects');
        } catch (err) {
            this.toast('error', err.message);
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-trash-alt"></i>';
        }
    }

    // ══════════════════════════════════════════════════════════════════
    //  FILES
    // ══════════════════════════════════════════════════════════════════

    async loadProjectFiles() {
        if (!this.currentProject) return;
        try {
            const files = await api.listFiles(this.currentProject.id);
            const container = document.getElementById('project-files');
            if (files.length === 0) {
                container.innerHTML = '<div class="empty-state"><i class="fas fa-cloud-upload-alt"></i><p>No files uploaded yet.</p></div>';
                return;
            }
            container.innerHTML = files.map(f => `
                <div class="file-item">
                    <div class="file-info">
                        <div class="file-icon ${f.file_type}">
                            <i class="fas fa-file-${f.file_type === 'pdf' ? 'pdf' : f.file_type === 'csv' ? 'csv' : f.file_type === 'xlsx' ? 'excel' : 'word'}"></i>
                        </div>
                        <div>
                            <div class="file-name">${this.esc(f.original_name)}</div>
                            <div class="file-meta">${this.formatSize(f.file_size)} · ${f.chunk_count} chunks · ${new Date(f.uploaded_at).toLocaleDateString()}</div>
                        </div>
                    </div>
                    <span class="status-badge ${f.status}">${f.status}</span>
                </div>
            `).join('');
        } catch (err) {
            this.toast('error', err.message);
        }
    }

    initUploadZone() {
        const zone = document.getElementById('upload-zone');
        const input = document.getElementById('file-input');

        zone.addEventListener('click', () => input.click());
        zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('dragover'); });
        zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
        zone.addEventListener('drop', e => {
            e.preventDefault();
            zone.classList.remove('dragover');
            if (e.dataTransfer.files.length) this.uploadFile(e.dataTransfer.files[0]);
        });
        input.addEventListener('change', () => { if (input.files.length) this.uploadFile(input.files[0]); });
    }

    async uploadFile(file) {
        if (!this.currentProject) return;
        const progressEl = document.getElementById('upload-progress');
        const fillEl = document.getElementById('progress-fill');
        const statusEl = document.getElementById('upload-status');
        const fileInput = document.getElementById('file-input');

        progressEl.classList.remove('hidden');
        fillEl.style.width = '30%';
        statusEl.textContent = `Uploading ${file.name}…`;

        try {
            fillEl.style.width = '60%';
            await api.uploadFile(this.currentProject.id, file);
            fillEl.style.width = '100%';
            statusEl.textContent = 'Upload complete! Processing embeddings…';
            this.toast('success', `${file.name} uploaded successfully!`);
            // Reset file input so the same file can be re-uploaded
            fileInput.value = '';
            setTimeout(() => {
                this.closeAllModals();
                progressEl.classList.add('hidden');
                fillEl.style.width = '0%';
                this.loadProjectFiles();
            }, 1500);
        } catch (err) {
            statusEl.textContent = `Error: ${err.message}`;
            fillEl.style.width = '0%';
            fileInput.value = '';
            this.toast('error', err.message);
        }
    }

    // ══════════════════════════════════════════════════════════════════
    //  CONSULTATION
    // ══════════════════════════════════════════════════════════════════

    async loadConsultView() {
        try {
            this.projects = await api.listProjects();
            const select = document.getElementById('consult-project');
            select.innerHTML = '<option value="">-- Select a project --</option>' +
                this.projects.map(p => `<option value="${p.id}">${this.esc(p.name)}</option>`).join('');
        } catch (err) {
            this.toast('error', err.message);
        }
    }

    async runConsultation() {
        const projectId = document.getElementById('consult-project').value;
        const goal = document.getElementById('consult-goal').value;
        if (!projectId) return this.toast('error', 'Please select a project');
        if (!goal || goal.length < 10) return this.toast('error', 'Goal statement must be at least 10 characters');

        const btn = document.getElementById('btn-run-consult');
        const origText = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Launching…';

        try {
            const report = await api.startConsultation(projectId, goal);
            this.toast('success', 'Consultation launched! AI agents are working…');
            document.getElementById('consult-goal').value = '';
            this.openReport(report.id, 'consult');
        } catch (err) {
            this.toast('error', err.message);
        } finally {
            btn.disabled = false;
            btn.innerHTML = origText;
        }
    }

    async quickConsult(e) {
        e.preventDefault();
        if (!this.currentProject) return;
        const goal = document.getElementById('qc-goal').value;
        if (!goal || goal.length < 10) return this.toast('error', 'Goal must be at least 10 characters');

        const btn = e.submitter || e.target.querySelector('button[type=submit]');
        if (btn) { btn.disabled = true; btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Launching…'; }

        try {
            const report = await api.startConsultation(this.currentProject.id, goal);
            this.closeAllModals();
            document.getElementById('qc-goal').value = '';
            this.toast('success', 'AI consultation started!');
            this.openReport(report.id, 'projects');
        } catch (err) {
            this.toast('error', err.message);
        } finally {
            if (btn) { btn.disabled = false; btn.textContent = 'Start Consultation'; }
        }
    }

    // ══════════════════════════════════════════════════════════════════
    //  REPORTS
    // ══════════════════════════════════════════════════════════════════

    async loadProjectReports() {
        if (!this.currentProject) return;
        try {
            const reports = await api.listReports(this.currentProject.id);
            const container = document.getElementById('project-reports');
            if (reports.length === 0) {
                container.innerHTML = '<div class="empty-state"><i class="fas fa-chart-line"></i><p>No reports yet.</p></div>';
                return;
            }
            container.innerHTML = reports.map(r => `
                <div class="report-list-item" onclick="app.openReport('${r.id}', 'projects')">
                    <div class="report-list-info">
                        <h5>${this.esc(r.goal_statement.substring(0, 100))}</h5>
                        <p>${new Date(r.created_at).toLocaleDateString()}</p>
                    </div>
                    <span class="status-badge ${r.status}">${r.status.replace('_', ' ')}</span>
                </div>
            `).join('');
        } catch (err) {
            this.toast('error', err.message);
        }
    }

    async loadAllReports() {
        try {
            this.projects = await api.listProjects();
            const container = document.getElementById('all-reports-list');
            let allReports = [];

            for (const p of this.projects) {
                if (p.report_count > 0) {
                    const reports = await api.listReports(p.id);
                    allReports.push(...reports.map(r => ({ ...r, project_name: p.name })));
                }
            }

            if (allReports.length === 0) {
                container.innerHTML = `<div class="empty-state-lg"><i class="fas fa-chart-line"></i><h3>No reports yet</h3><p>Start an AI consultation to generate your first report.</p></div>`;
                return;
            }

            allReports.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

            container.innerHTML = `<div class="card"><div class="card-header"><h3><i class="fas fa-chart-bar"></i> All Reports</h3></div>` +
                allReports.map(r => `
                    <div class="report-list-item" onclick="app.openReport('${r.id}', 'reports')">
                        <div class="report-list-info">
                            <h5>${this.esc(r.goal_statement.substring(0, 100))}</h5>
                            <p>${r.project_name} · ${new Date(r.created_at).toLocaleDateString()}</p>
                        </div>
                        <span class="status-badge ${r.status}">${r.status.replace('_', ' ')}</span>
                    </div>
                `).join('') + '</div>';
        } catch (err) {
            this.toast('error', err.message);
        }
    }

    async openReport(reportId, fromContext) {
        this.currentReportContext = fromContext;
        this.switchView('report-detail');

        const container = document.getElementById('report-detail-content');
        container.innerHTML = this.renderProcessing();

        try {
            const report = await api.getReport(reportId);
            if (report.status === 'completed') {
                container.innerHTML = this.renderReport(report);
                this.stopPolling(reportId);
            } else if (report.status === 'failed') {
                container.innerHTML = this.renderFailed(report);
                this.stopPolling(reportId);
            } else {
                // Poll for updates
                container.innerHTML = this.renderProcessing();
                this.startPolling(reportId);
            }
        } catch (err) {
            container.innerHTML = `<div class="empty-state-lg"><i class="fas fa-exclamation-triangle"></i><h3>Error</h3><p>${this.esc(err.message)}</p></div>`;
        }
    }

    startPolling(reportId) {
        this.stopPolling(reportId);
        this.pollingIntervals[reportId] = setInterval(async () => {
            try {
                const report = await api.getReport(reportId);
                const container = document.getElementById('report-detail-content');
                if (report.status === 'completed') {
                    container.innerHTML = this.renderReport(report);
                    this.stopPolling(reportId);
                } else if (report.status === 'failed') {
                    container.innerHTML = this.renderFailed(report);
                    this.stopPolling(reportId);
                }
            } catch (err) {
                console.error('Polling error:', err);
            }
        }, 3000);
    }

    stopPolling(reportId) {
        if (this.pollingIntervals[reportId]) {
            clearInterval(this.pollingIntervals[reportId]);
            delete this.pollingIntervals[reportId];
        }
    }

    goBackFromReport() {
        if (this.currentReportContext === 'projects' && this.currentProject) {
            this.openProject(this.currentProject.id);
        } else if (this.currentReportContext === 'reports') {
            this.switchView('reports');
        } else {
            this.switchView('dashboard');
        }
    }

    // ══════════════════════════════════════════════════════════════════
    //  REPORT RENDERING
    // ══════════════════════════════════════════════════════════════════

    renderProcessing() {
        return `
            <div class="processing-anim">
                <div class="agents-working">
                    <div class="agent-bubble bg-blue"><i class="fas fa-calculator"></i></div>
                    <div class="agent-bubble bg-green"><i class="fas fa-chess-knight"></i></div>
                    <div class="agent-bubble bg-purple"><i class="fas fa-crown"></i></div>
                </div>
                <h3>AI Consultants Are Analysing…</h3>
                <p>Our three-agent team is reviewing your data and producing insights. This typically takes 30–90 seconds.</p>
            </div>
        `;
    }

    renderFailed(report) {
        const error = report.consolidated_report?.error || 'Unknown error';
        return `
            <div class="report-header">
                <h2><i class="fas fa-exclamation-circle" style="color:var(--red)"></i> Consultation Failed</h2>
                <p style="color:var(--text-muted)">${this.esc(report.goal_statement)}</p>
                <p style="color:var(--red);margin-top:0.8rem">${this.esc(error)}</p>
            </div>
        `;
    }

    renderReport(report) {
        const fa = report.financial_analysis || {};
        const ms = report.market_strategy || {};
        const ex = report.executive_summary || {};

        return `
            <div class="report-header">
                <h2><i class="fas fa-check-circle" style="color:var(--green)"></i> AI Consulting Report</h2>
                <p style="color:var(--text-muted);margin-top:0.3rem">${this.esc(report.goal_statement)}</p>
                <div class="report-meta">
                    <span><i class="fas fa-clock"></i> ${report.processing_time_seconds}s</span>
                    <span><i class="fas fa-calendar"></i> ${new Date(report.completed_at).toLocaleString()}</span>
                    <span class="status-badge completed">Completed</span>
                    <button class="btn btn-sm" onclick="app.printReport()" title="Print / Export PDF">
                        <i class="fas fa-print"></i> Print
                    </button>
                </div>
            </div>

            <div class="report-sections">
                <!-- Executive Summary -->
                <div class="report-section">
                    <div class="report-section-header">
                        <div class="section-icon bg-purple"><i class="fas fa-crown"></i></div>
                        <h3>Executive Summary</h3>
                    </div>
                    <div class="report-section-body">
                        ${ex.situation_assessment ? `<p>${this.esc(ex.situation_assessment)}</p>` : ''}

                        ${ex.key_findings?.length ? `
                            <h4>Key Findings</h4>
                            <ul>${ex.key_findings.map(f => `<li>${this.esc(f)}</li>`).join('')}</ul>
                        ` : ''}

                        ${ex.strategic_recommendations?.length ? `
                            <h4>Strategic Recommendations</h4>
                            <ul>${ex.strategic_recommendations.map(r => `<li>${this.esc(r)}</li>`).join('')}</ul>
                        ` : ''}

                        ${ex.priority_actions?.length ? `
                            <h4>Priority Actions</h4>
                            ${ex.priority_actions.map(a => `
                                <div class="action-item">
                                    <h5>${this.esc(a.action || a.title || 'Action')}</h5>
                                    <p>${this.esc(a.description || a.detail || a.timeline || '')}</p>
                                </div>
                            `).join('')}
                        ` : ''}

                        ${ex.confidence_score !== undefined ? `
                            <div class="confidence-meter">
                                <span style="font-size:0.85rem;color:var(--text-secondary)">Confidence</span>
                                <div class="confidence-bar-bg">
                                    <div class="confidence-bar-fill" style="width:${Math.round(ex.confidence_score * 100)}%"></div>
                                </div>
                                <span class="confidence-label">${Math.round(ex.confidence_score * 100)}%</span>
                            </div>
                        ` : ''}

                        ${ex.raw_analysis ? `<p>${this.esc(ex.raw_analysis)}</p>` : ''}
                    </div>
                </div>

                <!-- Financial Analysis -->
                <div class="report-section">
                    <div class="report-section-header">
                        <div class="section-icon bg-blue"><i class="fas fa-calculator"></i></div>
                        <h3>Financial Analysis</h3>
                    </div>
                    <div class="report-section-body">
                        ${fa.revenue_analysis ? `<p>${this.esc(fa.revenue_analysis)}</p>` : ''}

                        ${fa.key_metrics ? `
                            <h4>Key Metrics</h4>
                            <div class="metric-grid">
                                ${Object.entries(fa.key_metrics).map(([k, v]) => `
                                    <div class="metric-item">
                                        <span class="metric-val">${typeof v === 'number' ? v.toLocaleString() : this.esc(String(v))}</span>
                                        <span class="metric-label">${this.esc(k.replace(/_/g, ' '))}</span>
                                    </div>
                                `).join('')}
                            </div>
                        ` : ''}

                        ${fa.cost_optimization?.length ? `
                            <h4>Cost Optimisation</h4>
                            <ul>${fa.cost_optimization.map(c => `<li>${this.esc(c)}</li>`).join('')}</ul>
                        ` : ''}

                        ${fa.risk_factors?.length ? `
                            <h4>Risk Factors</h4>
                            <ul>${fa.risk_factors.map(r => `<li>${this.esc(r)}</li>`).join('')}</ul>
                        ` : ''}

                        ${fa.recommendations?.length ? `
                            <h4>Recommendations</h4>
                            <ul>${fa.recommendations.map(r => `<li>${this.esc(r)}</li>`).join('')}</ul>
                        ` : ''}

                        ${fa.financial_health_score !== undefined && fa.financial_health_score !== null ? `
                            <div class="confidence-meter">
                                <span style="font-size:0.85rem;color:var(--text-secondary)">Financial Health</span>
                                <div class="confidence-bar-bg">
                                    <div class="confidence-bar-fill" style="width:${Math.round(fa.financial_health_score * 100)}%"></div>
                                </div>
                                <span class="confidence-label">${Math.round(fa.financial_health_score * 100)}%</span>
                            </div>
                        ` : ''}

                        ${fa.raw_analysis ? `<p>${this.esc(fa.raw_analysis)}</p>` : ''}
                    </div>
                </div>

                <!-- Market Strategy -->
                <div class="report-section">
                    <div class="report-section-header">
                        <div class="section-icon bg-green"><i class="fas fa-chess-knight"></i></div>
                        <h3>Market Strategy</h3>
                    </div>
                    <div class="report-section-body">
                        ${ms.market_overview ? `<p>${this.esc(ms.market_overview)}</p>` : ''}

                        ${ms.competitive_landscape?.length ? `
                            <h4>Competitive Landscape</h4>
                            <ul>${ms.competitive_landscape.map(c => `<li>${this.esc(c)}</li>`).join('')}</ul>
                        ` : ''}

                        ${ms.growth_opportunities?.length ? `
                            <h4>Growth Opportunities</h4>
                            <ul>${ms.growth_opportunities.map(g => `<li>${this.esc(g)}</li>`).join('')}</ul>
                        ` : ''}

                        ${ms.threats?.length ? `
                            <h4>Threats</h4>
                            <ul>${ms.threats.map(t => `<li>${this.esc(t)}</li>`).join('')}</ul>
                        ` : ''}

                        ${ms.target_segments?.length ? `
                            <h4>Target Segments</h4>
                            <ul>${ms.target_segments.map(s => `<li>${this.esc(s)}</li>`).join('')}</ul>
                        ` : ''}

                        ${ms.recommendations?.length ? `
                            <h4>Recommendations</h4>
                            <ul>${ms.recommendations.map(r => `<li>${this.esc(r)}</li>`).join('')}</ul>
                        ` : ''}

                        ${ms.raw_analysis ? `<p>${this.esc(ms.raw_analysis)}</p>` : ''}
                    </div>
                </div>
            </div>
        `;
    }

    // ══════════════════════════════════════════════════════════════════
    //  MODALS & TOASTS
    // ══════════════════════════════════════════════════════════════════

    openModal(id) {
        document.getElementById(id).classList.remove('hidden');
    }

    closeAllModals() {
        document.querySelectorAll('.modal').forEach(m => m.classList.add('hidden'));
    }

    toast(type, message) {
        const container = document.getElementById('toast-container');
        const icons = { success: 'fa-check-circle', error: 'fa-exclamation-circle', info: 'fa-info-circle' };
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <i class="fas ${icons[type]} toast-icon"></i>
            <span class="toast-text">${this.esc(message)}</span>
            <button class="toast-close" onclick="this.parentElement.remove()">&times;</button>
        `;
        container.appendChild(toast);
        setTimeout(() => toast.remove(), 5000);
    }

    // ══════════════════════════════════════════════════════════════════
    //  UTILITIES
    // ══════════════════════════════════════════════════════════════════

    printReport() {
        const content = document.getElementById('report-detail-content');
        if (!content) return;
        const win = window.open('', '_blank');
        win.document.write(`
            <html><head><title>AI Consulting Report — NexusAI</title>
            <style>
                body { font-family: 'Inter', system-ui, sans-serif; max-width: 800px; margin: 2rem auto; color: #1a1a2e; line-height: 1.7; padding: 0 2rem; }
                h2, h3, h4, h5 { color: #16213e; } h2 { border-bottom: 2px solid #0f3460; padding-bottom: 0.5rem; }
                ul { padding-left: 1.5rem; } li { margin-bottom: 0.4rem; }
                .report-meta, .status-badge, button { display: none; }
                .report-section { margin: 1.5rem 0; padding: 1rem; border: 1px solid #e0e0e0; border-radius: 8px; }
                .report-section-header { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem; }
                .section-icon { width: 28px; height: 28px; border-radius: 6px; display: flex; align-items: center; justify-content: center; color: #fff; font-size: 0.8rem; }
                .bg-purple { background: #6c5ce7; } .bg-blue { background: #0984e3; } .bg-green { background: #00b894; }
                .metric-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.8rem; }
                .metric-item { text-align: center; padding: 0.5rem; background: #f8f9fa; border-radius: 6px; }
                .metric-val { display: block; font-size: 1.1rem; font-weight: 700; } .metric-label { font-size: 0.75rem; color: #666; }
                .action-item { padding: 0.5rem; margin: 0.3rem 0; background: #f8f9fa; border-radius: 4px; }
                @media print { body { margin: 0; } }
            </style></head><body>
            <h2>NexusAI — AI Consulting Report</h2>
            ${content.innerHTML}
            <hr><p style="color:#999;font-size:0.75rem;margin-top:2rem;">Generated by NexusAI AI Consultancy Platform</p>
            </body></html>
        `);
        win.document.close();
        win.print();
    }

    esc(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    formatSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / 1048576).toFixed(1) + ' MB';
    }
}

// ── Bootstrap ────────────────────────────────────────────────────────────────
const app = new App();
document.addEventListener('DOMContentLoaded', () => app.init());
