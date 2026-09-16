const state = {
    token: localStorage.getItem("mindsync_token"),
    studentId: localStorage.getItem("mindsync_student_id"),
    studentName: localStorage.getItem("mindsync_student_name"),
    history: []
};

const $ = (id) => document.getElementById(id);

function escapeHtml(value) {
    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function showScreen(screenId) {
    const auth = $("authScreen");
    const app = $("appScreen");

    if (screenId === "appScreen") {
        auth?.classList.remove("active");
        app?.classList.add("show");
    } else {
        app?.classList.remove("show");
        auth?.classList.add("active");
    }
}

function showToast(message, type = "info") {
    const old = document.querySelector(".toast");
    old?.remove();

    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    requestAnimationFrame(() => toast.classList.add("show"));

    setTimeout(() => {
        toast.classList.remove("show");
        setTimeout(() => toast.remove(), 250);
    }, 3000);
}

async function apiRequest(endpoint, options = {}) {
    const headers = {
        "Content-Type": "application/json",
        ...(options.headers || {})
    };

    if (state.token) {
        headers.Authorization = `Bearer ${state.token}`;
    }

    const response = await fetch(endpoint, {
        ...options,
        headers
    });

    let data = {};
    try {
        data = await response.json();
    } catch {
        data = {};
    }

    if (!response.ok) {
        let detail = data.detail || data.message || "Request failed.";
        if (Array.isArray(detail)) {
            detail = detail.map((item) => item.msg || "Invalid input").join("; ");
        }
        throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    }

    return data;
}

function saveAuth(data, fallbackStudentId) {
    state.token = data.access_token || data.token;
    state.studentId = data.student_id || fallbackStudentId;
    state.studentName = data.name || data.student_name || state.studentId;

    if (state.token) localStorage.setItem("mindsync_token", state.token);
    if (state.studentId) localStorage.setItem("mindsync_student_id", state.studentId);
    if (state.studentName) localStorage.setItem("mindsync_student_name", state.studentName);
}

function clearAuth() {
    state.token = null;
    state.studentId = null;
    state.studentName = null;
    state.history = [];

    localStorage.removeItem("mindsync_token");
    localStorage.removeItem("mindsync_student_id");
    localStorage.removeItem("mindsync_student_name");
}

function setAuthMessage(message, type = "error") {
    const box = $("authMessage");
    if (!box) return;

    box.textContent = message;
    box.className = `auth-message show ${type === "success" ? "success" : ""}`;
}

function clearAuthMessage() {
    const box = $("authMessage");
    if (!box) return;
    box.textContent = "";
    box.className = "auth-message";
}

function setButtonLoading(button, loading, normalText) {
    if (!button) return;
    button.disabled = loading;
    button.textContent = loading ? "Please wait…" : normalText;
}

async function handleLogin(event) {
    event.preventDefault();
    clearAuthMessage();

    const studentId = $("loginStudentId")?.value.trim();
    const password = $("loginPassword")?.value || "";
    const button = $("loginBtn");

    if (!studentId || !password) {
        setAuthMessage("Please enter your Student ID and password.");
        return false;
    }

    setButtonLoading(button, true, "Sign in to MindSync");

    try {
        const data = await apiRequest("/auth/login", {
            method: "POST",
            body: JSON.stringify({ student_id: studentId, password })
        });

        saveAuth(data, studentId);
        showScreen("appScreen");
        updateUserInterface();
        await refreshDashboard();
        showToast("Welcome to your MindSync Library.", "success");
    } catch (error) {
        setAuthMessage(error.message);
    } finally {
        setButtonLoading(button, false, "Sign in to MindSync");
    }

    return false;
}

async function handleRegister(event) {
    event.preventDefault();
    clearAuthMessage();

    const studentId = $("regStudentId")?.value.trim();
    const name = $("regName")?.value.trim();
    const department = $("regDepartment")?.value.trim();
    const password = $("regPassword")?.value || "";
    const button = $("registerBtn");

    if (!studentId || !name || !department || !password) {
        setAuthMessage("Please complete all registration fields.");
        return false;
    }

    if (password.length < 6) {
        setAuthMessage("Password must contain at least 6 characters.");
        return false;
    }

    setButtonLoading(button, true, "Create Library Account");

    try {
        await apiRequest("/auth/register", {
            method: "POST",
            body: JSON.stringify({
                student_id: studentId,
                name,
                department,
                password
            })
        });

        switchAuth("login");
        $("loginStudentId").value = studentId;
        setAuthMessage("Account created successfully. Sign in to access the library.", "success");
    } catch (error) {
        setAuthMessage(error.message);
    } finally {
        setButtonLoading(button, false, "Create Library Account");
    }

    return false;
}

function switchAuth(mode) {
    const loginForm = $("loginForm");
    const registerForm = $("registerForm");
    const loginTab = $("loginTab");
    const registerTab = $("registerTab");
    const title = $("authTitle");
    const subtitle = $("authSubtitle");
    const eyebrow = $("authEyebrow");
    const note = $("authNote");
    const form = document.querySelector(".auth-form");

    clearAuthMessage();

    const register = mode === "register";

    loginForm.style.display = register ? "none" : "block";
    registerForm.style.display = register ? "block" : "none";

    loginTab.classList.toggle("active", !register);
    registerTab.classList.toggle("active", register);
    form?.classList.toggle("register-mode", register);

    if (register) {
        eyebrow.textContent = "HITK · JOIN THE SMART LIBRARY";
        title.textContent = "Join MindSync Library";
        subtitle.textContent = "Create your student account to search, borrow, reserve, and manage library books.";
        note.textContent = "Your account is secured by the MindSync FastAPI authentication system.";
    } else {
        eyebrow.textContent = "HITK · STUDENT LIBRARY ACCESS";
        title.textContent = "Welcome to MindSync Library";
        subtitle.textContent = "Sign in to search, borrow, reserve, and manage your library books.";
        note.textContent = "Student authentication is handled securely by the MindSync FastAPI backend. No third-party login is required.";
    }
}

function logout() {
    clearAuth();
    showScreen("authScreen");
    $("loginForm")?.reset();
    $("registerForm")?.reset();
    switchAuth("login");
    showToast("You have been signed out.");
}

function updateUserInterface() {
    const name = state.studentName || state.studentId || "Student";
    const id = state.studentId || "—";

    if ($("sbName")) $("sbName").textContent = name;
    if ($("sbMeta")) $("sbMeta").textContent = id;
}

async function refreshDashboard() {
    if (!state.token || !state.studentId) return;

    try {
        const data = await apiRequest(`/students/${encodeURIComponent(state.studentId)}/dashboard`);
        renderDashboard(data);
    } catch (error) {
        console.error("Dashboard error:", error);
        if (/401|403|token|authentication|credentials/i.test(error.message)) {
            clearAuth();
            showScreen("authScreen");
            showToast("Your session has expired. Please sign in again.", "error");
        }
    }
}

function renderDashboard(data) {
    const borrowed = data.borrowed_books || data.borrowed || [];
    const reservations = data.reservations || [];
    const dueSoon = data.due_soon_count ?? data.due_soon ?? 0;
    const fine = data.outstanding_fine ?? data.total_fine ?? data.fine ?? 0;

    if ($("statBorrowed")) $("statBorrowed").textContent = borrowed.length;
    if ($("statDueSoon")) $("statDueSoon").textContent = dueSoon;
    if ($("statReservations")) $("statReservations").textContent = reservations.length;
    if ($("statFine")) $("statFine").textContent = `₹${Number(fine || 0).toFixed(2)}`;
}

function useSuggestion(message) {
    const input = $("messageInput");
    if (input) input.value = message;
    sendMessage();
}

function focusComposer() {
    const input = $("messageInput");
    input?.focus();
    input?.scrollIntoView({ behavior: "smooth", block: "center" });
}

function addMessage(role, message) {
    const container = $("messages");
    if (!container) return;

    const empty = $("emptyState");
    if (empty) empty.style.display = "none";

    const item = document.createElement("div");
    item.className = `chat-message ${role}`;

    if (role === "user") {
        item.innerHTML = `<div class="chat-bubble">${escapeHtml(message)}</div>`;
    } else {
        item.innerHTML = `
            <div class="assistant-mark">MS</div>
            <div class="chat-response">
                <div class="chat-label">MINDSYNC · LIBRARY ASSISTANT</div>
                <div class="chat-bubble">${formatMessage(message)}</div>
            </div>`;
    }

    container.appendChild(item);
    container.scrollTop = container.scrollHeight;
}

function formatMessage(message) {
    let text = escapeHtml(message || "");
    text = text.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    text = text.replace(/`([^`]+)`/g, "<code>$1</code>");
    text = text.replace(/\n/g, "<br>");
    return text;
}

function showTyping() {
    const container = $("messages");
    if (!container || $("typingIndicator")) return;

    const empty = $("emptyState");
    if (empty) empty.style.display = "none";

    const item = document.createElement("div");
    item.id = "typingIndicator";
    item.className = "chat-message assistant";
    item.innerHTML = `
        <div class="assistant-mark">MS</div>
        <div class="chat-response">
            <div class="chat-label">MINDSYNC · LIBRARY ASSISTANT</div>
            <div class="typing"><span></span><span></span><span></span></div>
        </div>`;
    container.appendChild(item);
}

function removeTyping() {
    $("typingIndicator")?.remove();
}

async function sendMessage() {
    const input = $("messageInput");
    const button = $("sendBtn");
    const message = input?.value.trim();

    if (!message) return;

    if (!state.token) {
        showToast("Please sign in first.", "error");
        return;
    }

    input.value = "";
    addMessage("user", message);
    showTyping();
    button.disabled = true;
    button.textContent = "…";

    try {
        const data = await apiRequest("/chat", {
            method: "POST",
            body: JSON.stringify({
                message,
                history: state.history
            })
        });

        removeTyping();

        const reply = data.response || data.reply || data.message || "I couldn't generate a response.";
        addMessage("assistant", reply);

        state.history.push({ role: "user", content: message });
        state.history.push({ role: "assistant", content: reply });

        renderToolActivity(data.tool_calls || data.tools || []);
        renderBookResults(data.tool_calls || data.tools || []);
        await refreshDashboard();
    } catch (error) {
        removeTyping();
        addMessage("assistant", `I couldn't complete that library request. ${error.message}`);
        showToast(error.message, "error");
    } finally {
        button.disabled = false;
        button.textContent = "Search";
    }
}

function renderToolActivity(toolCalls) {
    const container = $("toolActivity");
    if (!container) return;

    if (!Array.isArray(toolCalls) || !toolCalls.length) {
        container.innerHTML = "";
        return;
    }

    container.innerHTML = toolCalls.map((tool) => {
        const name = tool.name || tool.tool || "Library tool";
        return `<div class="tool-item"><span class="tool-status"></span><span>${escapeHtml(prettifyToolName(name))}</span></div>`;
    }).join("");
}

function prettifyToolName(name) {
    return String(name).replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function renderBookResults(toolCalls) {
    const container = $("chatResults");
    if (!container) return;

    const books = extractBooks(toolCalls);
    if (!books.length) {
        container.innerHTML = "";
        return;
    }

    container.innerHTML = `
        <div class="result-heading">LIBRARY RESULTS <span>${books.length} resources</span></div>
        <div class="result-grid">${books.map(bookCard).join("")}</div>`;
}

function extractBooks(toolCalls) {
    const books = [];

    function walk(value) {
        if (!value) return;
        if (Array.isArray(value)) {
            value.forEach(walk);
            return;
        }
        if (typeof value !== "object") return;

        if (value.title || value.book_title || value.book_id) {
            books.push(value);
            return;
        }

        Object.values(value).forEach(walk);
    }

    (Array.isArray(toolCalls) ? toolCalls : []).forEach((tool) => {
        const name = tool.name || tool.tool || "";
        if (["search_catalog", "find_best_available_book", "recommend_for_course", "check_availability"].includes(name)) {
            walk(tool.output ?? tool.result ?? tool.data);
        }
    });

    const seen = new Set();
    return books.filter((book) => {
        const key = book.book_id || book.id || book.title;
        if (!key || seen.has(key)) return false;
        seen.add(key);
        return true;
    }).slice(0, 8);
}

function bookCard(book) {
    const title = book.title || book.book_title || "Untitled";
    const author = book.author || book.authors || "Author unavailable";
    const subject = book.subject || book.category || "";
    const id = book.book_id || book.id || "";
    const available = book.available_copies ?? book.available ?? book.copies_available;

    const availability = available !== undefined
        ? Number(available) > 0 ? `${available} available` : "Currently unavailable"
        : "Availability unknown";

    return `
        <article class="result-card">
            <div class="result-cover">${escapeHtml(title.charAt(0).toUpperCase())}</div>
            <div class="result-info">
                <small>${escapeHtml(id)}</small>
                <h3>${escapeHtml(title)}</h3>
                <p>${escapeHtml(author)}</p>
                ${subject ? `<span>${escapeHtml(subject)}</span>` : ""}
                <div class="availability">● ${escapeHtml(availability)}</div>
            </div>
        </article>`;
}

function setup() {
    if (state.token && state.studentId) {
        showScreen("appScreen");
        updateUserInterface();
        refreshDashboard();
    } else {
        showScreen("authScreen");
        switchAuth("login");
    }

    $("messageInput")?.addEventListener("keydown", (event) => {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            sendMessage();
        }
    });
}

// Keep these functions globally available because index.html uses onclick handlers.
window.handleLogin = handleLogin;
window.handleRegister = handleRegister;
window.switchAuth = switchAuth;
window.logout = logout;
window.refreshDashboard = refreshDashboard;
window.useSuggestion = useSuggestion;
window.focusComposer = focusComposer;
window.sendMessage = sendMessage;

document.addEventListener("DOMContentLoaded", setup);
