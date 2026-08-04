/**
 * api.js — HTTP client for the FastAPI backend.
 */
const API_BASE = 'http://localhost:8001/api';

class ApiClient {
    constructor() {
        this.token = localStorage.getItem('token') || null;
    }

    setToken(token) {
        this.token = token;
        localStorage.setItem('token', token);
    }

    clearToken() {
        this.token = null;
        localStorage.removeItem('token');
    }

    async request(method, path, body = null, isFormData = false) {
        const headers = {};
        if (this.token) headers['Authorization'] = `Bearer ${this.token}`;
        if (!isFormData && body) headers['Content-Type'] = 'application/json';

        const opts = { method, headers };
        if (body) {
            opts.body = isFormData ? body : JSON.stringify(body);
        }

        const res = await fetch(`${API_BASE}${path}`, opts);
        if (res.status === 204) return null;

        // Handle token expiry — auto-logout
        if (res.status === 401 && this.token) {
            this.clearToken();
            window.location.reload();
            throw new Error('Session expired. Please sign in again.');
        }

        const data = await res.json();
        if (!res.ok) {
            throw new Error(data.detail || `Request failed (${res.status})`);
        }
        return data;
    }

    // ── Auth ──
    register(payload) { return this.request('POST', '/auth/register', payload); }
    login(payload) { return this.request('POST', '/auth/login', payload); }
    getMe() { return this.request('GET', '/auth/me'); }

    // ── Projects ──
    createProject(payload) { return this.request('POST', '/projects', payload); }
    listProjects() { return this.request('GET', '/projects'); }
    getProject(id) { return this.request('GET', `/projects/${id}`); }
    deleteProject(id) { return this.request('DELETE', `/projects/${id}`); }

    // ── Files ──
    async uploadFile(projectId, file) {
        const fd = new FormData();
        fd.append('project_id', projectId);
        fd.append('file', file);
        return this.request('POST', '/upload', fd, true);
    }
    listFiles(projectId) { return this.request('GET', `/projects/${projectId}/files`); }

    // ── Consulting ──
    startConsultation(projectId, goalStatement) {
        return this.request('POST', '/consult', {
            project_id: projectId,
            goal_statement: goalStatement,
        });
    }
    getReport(reportId) { return this.request('GET', `/reports/${reportId}`); }
    listReports(projectId) { return this.request('GET', `/projects/${projectId}/reports`); }
}

const api = new ApiClient();
