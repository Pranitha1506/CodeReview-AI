
"use strict";

const API = "/api";

const codeInput = document.getElementById("codeInput");
const language = document.getElementById("language");

const analyzeBtn = document.getElementById("analyzeBtn");
const fixBtn = document.getElementById("fixBtn");
const clearBtn = document.getElementById("clearBtn");

const statusMessage = document.getElementById("statusMessage");

const resultsSection = document.getElementById("resultsSection");
const fixSection = document.getElementById("fixSection");

const historyContainer = document.getElementById("historyContainer");
const historyEmptyState = document.getElementById("historyEmptyState");

let latestFixedCode = "";
let latestFixLanguage = "Python";

let activeHistoryTab = "reviews";
let currentHistoryRecords = [];


function getElement(id) {
    return document.getElementById(id);
}


function setText(id, value) {
    const element = getElement(id);

    if (element) {
        element.textContent = value ?? "";
    }
}


function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, char => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
    })[char]);
}


function showStatus(message, isError = false) {
    if (!statusMessage) return;

    statusMessage.textContent = message;

    statusMessage.style.color = isError
        ? "#dc2626"
        : "";
}


function formatDate(value) {
    if (!value) return "Date unavailable";

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return String(value);
    }

    return date.toLocaleString();
}


async function apiRequest(url, options = {}) {
    const response = await fetch(url, options);

    let data;

    try {
        data = await response.json();
    } catch {
        throw new Error("The server returned an invalid response.");
    }

    if (!response.ok) {
        throw new Error(
            data.detail ||
            data.message ||
            `Request failed with status ${response.status}.`
        );
    }

    return data;
}


function showEmptyHistory(show) {
    if (historyEmptyState) {
        historyEmptyState.classList.toggle("hidden", !show);
    }

    if (historyContainer) {
        historyContainer.style.display = show ? "none" : "";
    }
}


function showReviewSection() {
    if (resultsSection) {
        resultsSection.classList.remove("hidden");
    }

    if (fixSection) {
        fixSection.classList.add("hidden");
    }

    const improvedCodeElement = getElement("improvedCode");

    if (improvedCodeElement) {
        const card = improvedCodeElement.closest(".result-card");

        if (card) {
            card.style.display = "none";
        }
    }
}


function showFixSection() {
    if (resultsSection) {
        resultsSection.classList.add("hidden");
    }

    if (fixSection) {
        fixSection.classList.remove("hidden");
    }
}


function updateCodeCount() {
    if (!codeInput) return;

    setText(
        "codeCount",
        `${codeInput.value.length} characters`
    );
}


if (codeInput) {
    codeInput.addEventListener("input", updateCodeCount);
    updateCodeCount();
}


if (clearBtn) {
    clearBtn.addEventListener("click", () => {
        if (codeInput) {
            codeInput.value = "";
        }

        updateCodeCount();
        showStatus("");

        if (resultsSection) {
            resultsSection.classList.add("hidden");
        }

        if (fixSection) {
            fixSection.classList.add("hidden");
        }
    });
}


function renderItems(items, type = "issue") {
    if (!Array.isArray(items) || items.length === 0) {
        return '<p class="empty-message">No items detected.</p>';
    }

    return items.map(item => {
        const title =
            typeof item === "string"
                ? item
                : item.title || "Finding";

        const description =
            typeof item === "string"
                ? ""
                : item.description || "";

        const severity = [
            "High",
            "Medium",
            "Low"
        ].includes(item.severity)
            ? item.severity
            : "";

        return `
            <div class="issue">
                <strong>${escapeHTML(title)}</strong>

                ${
                    description
                        ? `<p>${escapeHTML(description)}</p>`
                        : ""
                }

                ${
                    type === "issue" && severity
                        ? `<span class="severity ${severity}">
                            ${escapeHTML(severity)}
                           </span>`
                        : ""
                }
            </div>
        `;
    }).join("");
}


function displayResults(data) {
    if (!data || typeof data !== "object") {
        throw new Error("Invalid review result.");
    }

    const hasScore =
        data.overall_score !== null &&
        data.overall_score !== undefined &&
        Number.isFinite(Number(data.overall_score));
    const score = hasScore ? Number(data.overall_score) : null;

    setText("scoreValue", hasScore ? `${score}/100` : "N/A");
    setText("circleValue", hasScore ? score : "N/A");

    setText(
        "scoreLabel",
        hasScore
            ? score >= 80
                ? "Good code quality"
                : score >= 60
                    ? "Needs improvement"
                    : "Requires attention"
            : "No score from offline analysis"
    );

    const scoreCircle = getElement("scoreCircle");
    const circleValue = getElement("circleValue");

    const scoreColor = hasScore
        ? score >= 80
            ? "#16a34a"
            : score >= 60
                ? "#d97706"
                : "#dc2626"
        : "var(--muted)";

    if (scoreCircle) {
        scoreCircle.style.borderColor = scoreColor;
    }

    if (circleValue) {
        circleValue.style.color = scoreColor;
    }

    setText("reviewSummary", data.summary || "");

    const sourceBadge = getElement("reviewSourceBadge");

    if (sourceBadge) {
        const source = data.source || "Gemini AI";
        const badgeType = source === "Offline Static Analyzer"
            ? "offline"
            : "gemini";

        sourceBadge.textContent = source;
        sourceBadge.className = `source-badge ${badgeType}`;
    }

    const bugs = getElement("bugsResult");
    const security = getElement("securityResult");
    const optimization = getElement("optimizationResult");

    if (bugs) {
        bugs.innerHTML = renderItems(data.bugs);
    }

    if (security) {
        security.innerHTML = renderItems(data.security_issues);
    }

    if (optimization) {
        optimization.innerHTML = renderItems(
            data.optimizations,
            "suggestion"
        );
    }

    setText(
        "qualityResult",
        data.code_quality || "No quality description available."
    );

    const improvedCodeElement = getElement("improvedCode");

    if (improvedCodeElement) {
        const improvedCard =
            improvedCodeElement.closest(".result-card");

        if (improvedCard) {
            improvedCard.style.display = "none";
        }
    }

    showReviewSection();

    resultsSection?.scrollIntoView({
        behavior: "smooth",
        block: "start"
    });
}


if (analyzeBtn) {
    analyzeBtn.addEventListener("click", async () => {
        const code = codeInput?.value.trim() || "";

        if (!code) {
            showStatus("Please enter source code first.", true);
            return;
        }

        if (fixSection) {
            fixSection.classList.add("hidden");
        }

        analyzeBtn.disabled = true;

        if (fixBtn) {
            fixBtn.disabled = true;
        }

        analyzeBtn.textContent = "Analyzing...";

        showStatus("Gemini is analyzing your code. Please wait...");

        try {
            const data = await apiRequest(`${API}/review`, {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    code,
                    language: language?.value || "Python"
                })
            });

            displayResults(data);

            showStatus(
                data.source === "Offline Static Analyzer"
                    ? "Limited offline review completed and saved. See the report for its scope."
                    : "Code analysis completed and saved successfully."
            );

            await Promise.all([
                loadHistory(),
                loadDashboard()
            ]);

        } catch (error) {
            console.error("Review error:", error);
            showStatus(error.message, true);

        } finally {
            analyzeBtn.disabled = false;

            if (fixBtn) {
                fixBtn.disabled = false;
            }

            analyzeBtn.textContent = "✨ Analyze Code";
        }
    });
}


function renderTextList(items) {
    if (!Array.isArray(items) || items.length === 0) {
        return '<p class="empty-message">None reported.</p>';
    }

    return `
        <ul style="padding-left:20px;line-height:1.8;">
            ${items.map(item =>
                `<li>${escapeHTML(item)}</li>`
            ).join("")}
        </ul>
    `;
}


function displayChanges(changes) {
    if (!Array.isArray(changes) || changes.length === 0) {
        return `
            <p class="empty-message">
                No changes were necessary.
            </p>
        `;
    }

    return changes.map(change => `
        <div class="change-item">

            <strong>
                ${escapeHTML(change.title || "Code change")}
            </strong>

            <p>
                ${escapeHTML(change.explanation || "")}
            </p>

            <span class="change-type">
                ${escapeHTML(change.change_type || "Improvement")}
            </span>

        </div>
    `).join("");
}


function generateFallbackDiff(originalCode, fixedCode) {
    const original = originalCode.split("\n");
    const corrected = fixedCode.split("\n");

    const result = [];

    const maxLength = Math.max(
        original.length,
        corrected.length
    );

    for (let index = 0; index < maxLength; index++) {
        const oldLine = original[index];
        const newLine = corrected[index];

        if (
            oldLine !== undefined &&
            newLine !== undefined &&
            oldLine === newLine
        ) {
            result.push({
                type: "unchanged",
                line_number: index + 1,
                content: oldLine
            });
        } else {
            if (oldLine !== undefined) {
                result.push({
                    type: "removed",
                    line_number: index + 1,
                    content: oldLine
                });
            }

            if (newLine !== undefined) {
                result.push({
                    type: "added",
                    line_number: index + 1,
                    content: newLine
                });
            }
        }
    }

    return result;
}


function displayCodeDiff(diff) {
    const viewer = getElement("diffViewer");
    const summary = getElement("diffSummary");

    if (!viewer || !summary) return;

    if (!Array.isArray(diff) || diff.length === 0) {
        viewer.innerHTML =
            '<p class="empty-message">No differences found.</p>';

        summary.textContent = "No changes.";

        return;
    }

    const added = diff.filter(
        line => line.type === "added"
    ).length;

    const removed = diff.filter(
        line => line.type === "removed"
    ).length;

    summary.innerHTML = `
        <span class="added-count">+${added} additions</span>
        <span class="removed-count">−${removed} deletions</span>
    `;

    viewer.innerHTML = diff.map(line => {
        const type = [
            "added",
            "removed",
            "unchanged"
        ].includes(line.type)
            ? line.type
            : "unchanged";

        const prefix =
            type === "added"
                ? "+"
                : type === "removed"
                    ? "−"
                    : " ";

        return `
            <div class="diff-line ${type}">

                <span class="diff-prefix">
                    ${prefix}
                </span>

                <span class="diff-number">
                    ${escapeHTML(line.line_number)}
                </span>

                <code>${escapeHTML(line.content)}</code>

            </div>
        `;
    }).join("");
}


function updateCodeComparison(data) {
    const originalElement = getElement("originalCode");
    const fixedElement = getElement("fixedCode");

    const noChanges =
        data.decision === "NO_FIX_NEEDED" ||
        data.original_code === data.fixed_code;

    const originalCard =
        originalElement?.closest(".result-card");

    const fixedCard =
        fixedElement?.closest(".result-card");

    if (originalCard) {
        originalCard.style.display = noChanges ? "none" : "";
    }

    if (fixedCard) {
        fixedCard.style.display = noChanges ? "none" : "";
    }

    return noChanges;
}


function displayFixResults(data, shouldScroll = true) {
    if (!data || typeof data !== "object") {
        throw new Error("Invalid code-fix response.");
    }

    latestFixedCode = data.fixed_code || "";
    latestFixLanguage = data.language || "Python";

    const sourceBadge = getElement("fixSourceBadge");

    if (sourceBadge) {
        const source = data.source || "Gemini AI";
        const model = data.model_used;

        sourceBadge.textContent =
            source === "Gemini AI"
                ? `✨ Gemini AI${model ? " · " + model : ""}`
                : "⚙ Offline Static Analyzer";

        sourceBadge.style.display = "inline-block";
    }

    setText("fixSummary", data.summary || "");

    const decisionLabels = {
        NO_FIX_NEEDED: "No Fix Needed",
        IMPROVEMENT: "Improvement Suggested",
        BUG_FIX_REQUIRED: "Bug Fix Required"
    };

    const decisionClasses = {
        NO_FIX_NEEDED: "no-fix",
        IMPROVEMENT: "improvement",
        BUG_FIX_REQUIRED: "bug-fix"
    };

    const decision = data.decision || (
        data.original_code === data.fixed_code
            ? "NO_FIX_NEEDED"
            : "IMPROVEMENT"
    );

    const badge = getElement("fixDecisionBadge");

    if (badge) {
        badge.textContent =
            decisionLabels[decision] || decision;

        badge.className =
            `decision-badge ${decisionClasses[decision] || ""}`;
    }

    setText(
        "decisionReason",
        data.decision_reason ||
        "The code-fix analysis has completed."
    );

    const syntaxElement = getElement("syntaxValidation");

    if (syntaxElement) {
        if (data.syntax_valid === true) {
            syntaxElement.textContent =
                "✓ " + (
                    data.syntax_message ||
                    "Syntax validation passed."
                );

            syntaxElement.className =
                "syntax-validation syntax-valid";

        } else if (data.syntax_valid === false) {
            syntaxElement.textContent =
                "✕ " + (
                    data.syntax_message ||
                    "Syntax error detected."
                );

            syntaxElement.className =
                "syntax-validation syntax-invalid";

        } else {
            syntaxElement.textContent =
                data.syntax_message ||
                "Syntax validation is unavailable.";

            syntaxElement.className =
                "syntax-validation";
        }
    }

    setText("originalCode", data.original_code || "");
    setText("fixedCode", data.fixed_code || "");

    const noChanges = updateCodeComparison(data);

    const changesResult = getElement("changesResult");

    if (changesResult) {
        changesResult.innerHTML =
            displayChanges(data.changes);
    }

    const remainingIssues = getElement("remainingIssues");

    if (remainingIssues) {
        remainingIssues.innerHTML =
            renderTextList(data.remaining_issues);
    }

    const testingNotes = getElement("testingNotes");

    if (testingNotes) {
        testingNotes.innerHTML =
            renderTextList(data.testing_notes);
    }

    const diff = Array.isArray(data.diff)
        ? data.diff
        : generateFallbackDiff(
            data.original_code || "",
            data.fixed_code || ""
        );

    displayCodeDiff(diff);

    const diffCard = getElement("smartDiffCard");

    if (diffCard) {
        diffCard.style.display = noChanges ? "none" : "";
    }

    showFixSection();

    if (shouldScroll) {
        fixSection?.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });
    }
}


if (fixBtn) {
    fixBtn.addEventListener("click", async () => {
        const code = codeInput?.value.trim() || "";

        if (!code) {
            showStatus("Please enter source code before fixing.", true);
            return;
        }

        if (resultsSection) {
            resultsSection.classList.add("hidden");
        }

        fixBtn.disabled = true;

        if (analyzeBtn) {
            analyzeBtn.disabled = true;
        }

        fixBtn.textContent = "Fixing Code...";

        showStatus(
            "Trying available Gemini models. Offline analysis will be used if all models fail..."
        );

        try {
            const data = await apiRequest(`${API}/fix`, {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    code,
                    language: language?.value || "Python"
                })
            });

            displayFixResults(data);

            showStatus(
                data.source === "Offline Static Analyzer"
                    ? "Offline analysis completed. Review and test the suggested result."
                    : "Gemini AI code-fix analysis completed. Review and test the result."
            );

            await Promise.all([
                loadHistory(),
                loadDashboard()
            ]);

        } catch (error) {
            console.error("Code fix error:", error);
            showStatus(error.message, true);

        } finally {
            fixBtn.disabled = false;

            if (analyzeBtn) {
                analyzeBtn.disabled = false;
            }

            fixBtn.textContent = "🛠 Fix My Code";
        }
    });
}


const copyFixedBtn = getElement("copyFixedBtn");

if (copyFixedBtn) {
    copyFixedBtn.addEventListener("click", async () => {
        if (!latestFixedCode) {
            showStatus("No corrected code is available.", true);
            return;
        }

        try {
            await navigator.clipboard.writeText(latestFixedCode);

            copyFixedBtn.textContent = "Copied!";

            setTimeout(() => {
                copyFixedBtn.textContent = "Copy Fixed Code";
            }, 1500);

        } catch (error) {
            showStatus("Unable to copy code. Copy it manually.", true);
        }
    });
}


const downloadFixedBtn = getElement("downloadFixedBtn");

if (downloadFixedBtn) {
    downloadFixedBtn.addEventListener("click", () => {
        if (!latestFixedCode) {
            showStatus("No corrected code is available.", true);
            return;
        }

        const extensions = {
            Python: "py",
            Java: "java",
            JavaScript: "js",
            C: "c",
            "C++": "cpp"
        };

        const extension =
            extensions[latestFixLanguage] || "txt";

        const blob = new Blob(
            [latestFixedCode],
            { type: "text/plain;charset=utf-8" }
        );

        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");

        link.href = url;
        link.download = `corrected_code.${extension}`;

        document.body.appendChild(link);
        link.click();
        link.remove();

        URL.revokeObjectURL(url);
    });
}


async function loadDashboard() {
    try {
        const data = await apiRequest(`${API}/dashboard`);

        setText("totalReviews", data.total_reviews ?? 0);
        setText("totalFixes", data.total_fixes ?? 0);
        setText(
            "averageScore",
            Number(data.average_score || 0).toFixed(1)
        );
        setText("totalBugs", data.total_bugs ?? 0);

    } catch (error) {
        console.error("Dashboard loading error:", error);
    }
}


const refreshDashboardBtn = getElement("refreshDashboardBtn");

if (refreshDashboardBtn) {
    refreshDashboardBtn.addEventListener(
        "click",
        loadDashboard
    );
}


function setActiveHistoryTab(tab) {
    activeHistoryTab = tab;

    const reviewTab = getElement("reviewHistoryTab");
    const fixTab = getElement("fixHistoryTab");

    if (reviewTab) {
        reviewTab.classList.toggle(
            "active",
            tab === "reviews"
        );
    }

    if (fixTab) {
        fixTab.classList.toggle(
            "active",
            tab === "fixes"
        );
    }

    const sortSelect = getElement("historySort");

    if (sortSelect) {
        const scoreOptions = Array.from(
            sortSelect.options
        ).filter(option =>
            option.value.startsWith("score-")
        );

        scoreOptions.forEach(option => {
            option.disabled = tab === "fixes";
        });

        if (
            tab === "fixes" &&
            sortSelect.value.startsWith("score-")
        ) {
            sortSelect.value = "newest";
        }
    }

    loadHistory();
}


getElement("reviewHistoryTab")?.addEventListener(
    "click",
    () => setActiveHistoryTab("reviews")
);


getElement("fixHistoryTab")?.addEventListener(
    "click",
    () => setActiveHistoryTab("fixes")
);


function getHistoryFilters() {
    return {
        search: getElement("historySearch")?.value.trim() || "",

        language:
            getElement("historyLanguageFilter")?.value || "all",

        sort:
            getElement("historySort")?.value || "newest"
    };
}


function buildHistoryUrl(endpoint) {
    const filters = getHistoryFilters();

    const params = new URLSearchParams();

    if (filters.search) {
        params.set("search", filters.search);
    }

    if (filters.language !== "all") {
        params.set("language", filters.language);
    }

    params.set("sort", filters.sort);

    return `${API}/${endpoint}?${params.toString()}`;
}


const historySearch = getElement("historySearch");
const historyLanguageFilter =
    getElement("historyLanguageFilter");
const historySort = getElement("historySort");


if (historySearch) {
    historySearch.addEventListener("input", loadHistory);
}

if (historyLanguageFilter) {
    historyLanguageFilter.addEventListener(
        "change",
        loadHistory
    );
}

if (historySort) {
    historySort.addEventListener(
        "change",
        loadHistory
    );
}


function renderReviewHistory(reviews) {
    if (!Array.isArray(reviews) || reviews.length === 0) {
        return;
    }

    const rows = reviews.map(review => `
        <tr>

            <td>#${escapeHTML(review.id)}</td>

            <td>${escapeHTML(review.language)}</td>

            <td>
                <strong>
                    ${escapeHTML(review.overall_score ?? "--")}
                </strong>
            </td>

            <td>${escapeHTML(formatDate(review.created_at))}</td>

            <td>
                <div class="history-actions">

                    <button
                        type="button"
                        class="secondary-btn"
                        data-action="view-review"
                        data-id="${Number(review.id)}">
                        View
                    </button>

                    <button
                        type="button"
                        class="delete-btn"
                        data-action="delete-review"
                        data-id="${Number(review.id)}">
                        Delete
                    </button>

                </div>
            </td>

        </tr>
    `).join("");

    return `
        <div class="history-table-wrapper">

            <table class="history-table">

                <thead>
                    <tr>
                        <th>Review ID</th>
                        <th>Language</th>
                        <th>Score</th>
                        <th>Date</th>
                        <th>Actions</th>
                    </tr>
                </thead>

                <tbody>${rows}</tbody>

            </table>

        </div>
    `;
}


function renderFixHistory(fixes) {
    if (!Array.isArray(fixes) || fixes.length === 0) {
        return;
    }

    const rows = fixes.map(fix => `
        <tr>

            <td>#${escapeHTML(fix.id)}</td>

            <td>${escapeHTML(fix.language)}</td>

            <td>
                <span class="decision-badge">
                    ${escapeHTML(
                        fix.decision?.replaceAll("_", " ") || "Unknown"
                    )}
                </span>
            </td>

            <td>${escapeHTML(fix.source || "Unknown")}</td>

            <td>${escapeHTML(formatDate(fix.created_at))}</td>

            <td>
                <div class="history-actions">

                    <button
                        type="button"
                        class="secondary-btn"
                        data-action="view-fix"
                        data-id="${Number(fix.id)}">
                        View
                    </button>

                    <button
                        type="button"
                        class="delete-btn"
                        data-action="delete-fix"
                        data-id="${Number(fix.id)}">
                        Delete
                    </button>

                </div>
            </td>

        </tr>
    `).join("");

    return `
        <div class="history-table-wrapper">

            <table class="history-table">

                <thead>
                    <tr>
                        <th>Fix ID</th>
                        <th>Language</th>
                        <th>Decision</th>
                        <th>Source</th>
                        <th>Date</th>
                        <th>Actions</th>
                    </tr>
                </thead>

                <tbody>${rows}</tbody>

            </table>

        </div>
    `;
}


async function loadReviewHistory() {
    const url = buildHistoryUrl("reviews");

    const reviews = await apiRequest(url);

    currentHistoryRecords = reviews;

    setText(
        "historySummary",
        `${reviews.length} review record(s) found`
    );

    if (!reviews.length) {
        showEmptyHistory(true);
        return;
    }

    showEmptyHistory(false);

    historyContainer.innerHTML =
        renderReviewHistory(reviews);
}


async function loadFixHistory() {
    const url = buildHistoryUrl("fixes");

    const fixes = await apiRequest(url);

    currentHistoryRecords = fixes;

    setText(
        "historySummary",
        `${fixes.length} fix record(s) found`
    );

    if (!fixes.length) {
        showEmptyHistory(true);
        return;
    }

    showEmptyHistory(false);

    historyContainer.innerHTML =
        renderFixHistory(fixes);
}


async function loadHistory() {
    if (!historyContainer) return;

    historyContainer.innerHTML =
        '<p class="muted">Loading history...</p>';

    showEmptyHistory(false);

    try {
        if (activeHistoryTab === "reviews") {
            await loadReviewHistory();
        } else {
            await loadFixHistory();
        }

    } catch (error) {
        console.error("History loading error:", error);

        historyContainer.innerHTML = `
            <p class="error-message">
                ${escapeHTML(error.message)}
            </p>
        `;

        showEmptyHistory(false);

        setText("historySummary", "Unable to load history.");
    }
}


async function viewReview(id) {
    try {
        const data = await apiRequest(
            `${API}/reviews/${id}`
        );

        if (codeInput) {
            codeInput.value = data.source_code || "";
        }

        if (language) {
            language.value = data.language || "Python";
        }

        updateCodeCount();

        displayResults(data.review_result);

        showStatus(
            `Viewing saved Code Review #${id}. No new AI request was made.`
        );

    } catch (error) {
        showStatus(error.message, true);
    }
}


async function viewFix(id) {
    try {
        const data = await apiRequest(
            `${API}/fixes/${id}`
        );

        if (codeInput) {
            codeInput.value = data.original_code || "";
        }

        if (language) {
            language.value = data.language || "Python";
        }

        updateCodeCount();

        displayFixResults(data.fix_result);

        showStatus(
            `Viewing saved Code Fix #${id}. No new AI request was made.`
        );

    } catch (error) {
        showStatus(error.message, true);
    }
}


async function deleteReview(id) {
    const confirmed = confirm(
        `Delete Code Review #${id}? This action cannot be undone.`
    );

    if (!confirmed) return;

    try {
        await apiRequest(`${API}/reviews/${id}`, {
            method: "DELETE"
        });

        showStatus(`Code Review #${id} deleted successfully.`);

        await Promise.all([
            loadHistory(),
            loadDashboard()
        ]);

    } catch (error) {
        showStatus(error.message, true);
    }
}


async function deleteFix(id) {
    const confirmed = confirm(
        `Delete Code Fix #${id}? This action cannot be undone.`
    );

    if (!confirmed) return;

    try {
        await apiRequest(`${API}/fixes/${id}`, {
            method: "DELETE"
        });

        showStatus(`Code Fix #${id} deleted successfully.`);

        await Promise.all([
            loadHistory(),
            loadDashboard()
        ]);

    } catch (error) {
        showStatus(error.message, true);
    }
}


if (historyContainer) {
    historyContainer.addEventListener("click", event => {
        const button = event.target.closest(
            "button[data-action]"
        );

        if (!button) return;

        const id = Number(button.dataset.id);
        const action = button.dataset.action;

        if (!Number.isInteger(id) || id <= 0) {
            return;
        }

        switch (action) {
            case "view-review":
                viewReview(id);
                break;

            case "view-fix":
                viewFix(id);
                break;

            case "delete-review":
                deleteReview(id);
                break;

            case "delete-fix":
                deleteFix(id);
                break;
        }
    });
}


const refreshHistoryBtn = getElement("refreshHistoryBtn");

if (refreshHistoryBtn) {
    refreshHistoryBtn.addEventListener("click", async () => {
        refreshHistoryBtn.disabled = true;
        refreshHistoryBtn.textContent = "Refreshing...";

        await Promise.all([
            loadHistory(),
            loadDashboard()
        ]);

        refreshHistoryBtn.disabled = false;
        refreshHistoryBtn.textContent = "↻ Refresh";
    });
}


async function initializeApplication() {
    updateCodeCount();

    await Promise.all([
        loadDashboard(),
        loadHistory()
    ]);
}

initializeApplication();

