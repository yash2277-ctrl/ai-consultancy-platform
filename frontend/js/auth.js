/**
 * auth.js — Handles login, register, and session management.
 */

class AuthManager {
    constructor() {
        this.user = null;
    }

    init() {
        // Auth tabs
        document.querySelectorAll('.auth-tab').forEach(tab => {
            tab.addEventListener('click', () => this.switchTab(tab.dataset.tab));
        });

        // Forms
        document.getElementById('login-form').addEventListener('submit', e => this.handleLogin(e));
        document.getElementById('register-form').addEventListener('submit', e => this.handleRegister(e));
    }

    switchTab(tab) {
        document.querySelectorAll('.auth-tab').forEach(t => t.classList.toggle('active', t.dataset.tab === tab));
        document.getElementById('login-form').classList.toggle('hidden', tab !== 'login');
        document.getElementById('register-form').classList.toggle('hidden', tab !== 'register');
        document.getElementById('auth-error').classList.add('hidden');
    }

    showError(msg) {
        const el = document.getElementById('auth-error');
        el.textContent = msg;
        el.classList.remove('hidden');
    }

    async handleLogin(e) {
        e.preventDefault();
        const email = document.getElementById('login-email').value;
        const password = document.getElementById('login-password').value;
        const btn = e.target.querySelector('button[type=submit]');
        const origHTML = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Signing in…';
        try {
            const data = await api.login({ email, password });
            api.setToken(data.access_token);
            this.user = data.user;
            app.onAuthenticated(data.user);
        } catch (err) {
            this.showError(err.message);
        } finally {
            btn.disabled = false;
            btn.innerHTML = origHTML;
        }
    }

    async handleRegister(e) {
        e.preventDefault();
        const payload = {
            full_name: document.getElementById('reg-name').value,
            email: document.getElementById('reg-email').value,
            company: document.getElementById('reg-company').value || null,
            password: document.getElementById('reg-password').value,
        };
        const btn = e.target.querySelector('button[type=submit]');
        const origHTML = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creating account…';
        try {
            const data = await api.register(payload);
            api.setToken(data.access_token);
            this.user = data.user;
            app.onAuthenticated(data.user);
        } catch (err) {
            this.showError(err.message);
        } finally {
            btn.disabled = false;
            btn.innerHTML = origHTML;
        }
    }

    async checkSession() {
        if (!api.token) return false;
        try {
            const user = await api.getMe();
            this.user = user;
            return true;
        } catch {
            api.clearToken();
            return false;
        }
    }

    logout() {
        api.clearToken();
        this.user = null;
    }
}

const auth = new AuthManager();
