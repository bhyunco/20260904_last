// ============================================================
// VIBE RPA Front-end Application Controller
// ============================================================

document.addEventListener("DOMContentLoaded", () => {
    // --------------------------------------------------------
    // 1. DOM Elements
    // --------------------------------------------------------
    const btnStartRpa = document.getElementById("btnStartRpa");
    const btnSendEmailOnly = document.getElementById("btnSendEmailOnly");
    const btnRefreshData = document.getElementById("btnRefreshData");
    const btnClearLogs = document.getElementById("btnClearLogs");

    const appPasswordInput = document.getElementById("appPasswordInput");
    const rememberPasswordCheck = document.getElementById("rememberPasswordCheck");
    const togglePasswordVisibility = document.getElementById("togglePasswordVisibility");
    const eyeIcon = document.getElementById("eyeIcon");

    const senderEmail = document.getElementById("senderEmail");
    const receiverEmail = document.getElementById("receiverEmail");
    const headlessCheck = document.getElementById("headlessCheck");

    const companyTagsContainer = document.getElementById("companyTagsContainer");
    const newCompanyInput = document.getElementById("newCompanyInput");
    const btnAddCompany = document.getElementById("btnAddCompany");

    const progressBarFill = document.getElementById("progressBarFill");
    const bigPercentText = document.getElementById("bigPercentText");
    const progressPercentDisplay = document.getElementById("progressPercentDisplay");
    const currentStepMessage = document.getElementById("currentStepMessage");
    const progressPulse = document.getElementById("progressPulse");
    const terminalLogs = document.getElementById("terminalLogs");

    const systemStatusPill = document.getElementById("systemStatusPill");
    const systemStatusText = document.getElementById("systemStatusText");

    const kpiTotalArticles = document.getElementById("kpiTotalArticles");
    const kpiPositive = document.getElementById("kpiPositive");
    const kpiNegative = document.getElementById("kpiNegative");
    const kpiPosRatio = document.getElementById("kpiPosRatio");

    const summaryTableBody = document.getElementById("summaryTableBody");
    const articlesTableBody = document.getElementById("articlesTableBody");
    const articleFilterInput = document.getElementById("articleFilterInput");
    const companyDonutsContainer = document.getElementById("companyDonutsContainer");

    // --------------------------------------------------------
    // 2. Chart Instances Storage
    // --------------------------------------------------------
    let overallChartInstance = null;
    let companyBarChartInstance = null;
    const companyDonutInstances = {};
    let cachedArticles = [];

    // --------------------------------------------------------
    // 3. 앱 비밀번호 로컬스토리지 기억 기능 (요구사항 1)
    // --------------------------------------------------------
    const STORAGE_KEY = "vibe_rpa_app_password";
    const savedPassword = localStorage.getItem(STORAGE_KEY);

    if (savedPassword) {
        appPasswordInput.value = savedPassword;
        rememberPasswordCheck.checked = true;
    }

    rememberPasswordCheck.addEventListener("change", () => {
        if (rememberPasswordCheck.checked) {
            localStorage.setItem(STORAGE_KEY, appPasswordInput.value);
            showToast("앱 비밀번호가 브라우저에 저장되었습니다.", "success");
        } else {
            localStorage.removeItem(STORAGE_KEY);
            showToast("저장된 앱 비밀번호가 삭제되었습니다.", "info");
        }
    });

    appPasswordInput.addEventListener("input", () => {
        if (rememberPasswordCheck.checked) {
            localStorage.setItem(STORAGE_KEY, appPasswordInput.value);
        }
    });

    // 비밀번호 가시성 토글
    togglePasswordVisibility.addEventListener("click", () => {
        if (appPasswordInput.type === "password") {
            appPasswordInput.type = "text";
            eyeIcon.classList.replace("fa-eye", "fa-eye-slash");
            togglePasswordVisibility.innerHTML = '<i class="fa-solid fa-eye-slash"></i> 숨김';
        } else {
            appPasswordInput.type = "password";
            eyeIcon.classList.replace("fa-eye-slash", "fa-eye");
            togglePasswordVisibility.innerHTML = '<i class="fa-solid fa-eye"></i> 보기';
        }
    });

    // --------------------------------------------------------
    // 4. 기업 태그 관리
    // --------------------------------------------------------
    function getCompaniesList() {
        const tags = companyTagsContainer.querySelectorAll(".tag");
        const list = [];
        tags.forEach(t => {
            const txt = t.childNodes[0].textContent.trim();
            if (txt) list.push(txt);
        });
        return list;
    }

    function addCompanyTag(name) {
        const trimmed = name.trim();
        if (!trimmed) return;
        const currentList = getCompaniesList();
        if (currentList.includes(trimmed)) {
            showToast("이미 등록된 기업명입니다.", "warn");
            return;
        }
        const tag = document.createElement("span");
        tag.className = "tag";
        tag.innerHTML = `${trimmed} <i class="fa-solid fa-xmark remove-tag"></i>`;
        companyTagsContainer.appendChild(tag);
        newCompanyInput.value = "";
    }

    btnAddCompany.addEventListener("click", () => addCompanyTag(newCompanyInput.value));
    newCompanyInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") {
            e.preventDefault();
            addCompanyTag(newCompanyInput.value);
        }
    });

    companyTagsContainer.addEventListener("click", (e) => {
        if (e.target.classList.contains("remove-tag")) {
            const tag = e.target.closest(".tag");
            if (companyTagsContainer.querySelectorAll(".tag").length <= 1) {
                showToast("최소 1개 이상의 기업이 필요합니다.", "warn");
                return;
            }
            tag.remove();
        }
    });

    // --------------------------------------------------------
    // 5. SSE 실시간 스트림 연결 (요구사항 2: 실시간 % 진행상황)
    // --------------------------------------------------------
    let eventSource = null;

    function initEventSource() {
        if (eventSource) eventSource.close();
        eventSource = new EventSource("/api/stream");

        eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                updateProgressUI(data);
            } catch (err) {
                // Keepalive heartbeat
            }
        };

        eventSource.onerror = () => {
            // Reconnect automatically
        };
    }

    function updateProgressUI(data) {
        if (!data) return;

        const percent = Math.min(100, Math.max(0, data.percent || 0));
        progressBarFill.style.width = `${percent}%`;
        bigPercentText.innerText = percent;
        progressPercentDisplay.innerText = `${percent}%`;

        if (data.message) {
            currentStepMessage.innerText = data.message;
            addLogLine(`[${data.timestamp || getCurTime()}] ${data.message}`, getLogClass(data.status));
        }

        // 상태 인디케이터 뱃지 및 스텝
        if (data.status === "running") {
            setSystemStatus("실행 중", "running");
            progressPulse.classList.add("active");
            btnStartRpa.disabled = true;
            btnStartRpa.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> 자동화 작업 진행 중...';
        } else if (data.status === "completed") {
            setSystemStatus("완료됨", "idle");
            progressPulse.classList.remove("active");
            btnStartRpa.disabled = false;
            btnStartRpa.innerHTML = '<i class="fa-solid fa-play"></i> RPA 전체 자동화 실행';
            showToast("🎉 RPA 전체 자동화가 성공적으로 완료되었습니다!", "success");
            loadDashboardData();
        } else if (data.status === "error") {
            setSystemStatus("오류 발생", "error");
            progressPulse.classList.remove("active");
            btnStartRpa.disabled = false;
            btnStartRpa.innerHTML = '<i class="fa-solid fa-play"></i> RPA 전체 자동화 실행';
            showToast(`작업 중 오류: ${data.message}`, "error");
        }

        updateStepTracker(percent);
    }

    function updateStepTracker(pct) {
        const steps = [
            { id: "step1", line: "line1", threshold: 5, compThreshold: 48 },
            { id: "step2", line: "line2", threshold: 48, compThreshold: 76 },
            { id: "step3", line: "line3", threshold: 76, compThreshold: 86 },
            { id: "step4", line: null, threshold: 86, compThreshold: 98 }
        ];

        steps.forEach((s) => {
            const stepEl = document.getElementById(s.id);
            const lineEl = s.line ? document.getElementById(s.line) : null;

            if (pct >= s.compThreshold) {
                stepEl.className = "step-item completed";
                if (lineEl) lineEl.className = "step-line completed";
            } else if (pct >= s.threshold) {
                stepEl.className = "step-item active";
                if (lineEl) lineEl.className = "step-line";
            } else {
                stepEl.className = "step-item";
                if (lineEl) lineEl.className = "step-line";
            }
        });
    }

    function setSystemStatus(text, type) {
        systemStatusText.innerText = text;
        const dot = systemStatusPill.querySelector(".status-dot");
        dot.className = "status-dot";
        if (type === "running") dot.classList.add("running");
        else if (type === "error") dot.classList.add("error");
    }

    function addLogLine(msg, typeClass = "info") {
        const line = document.createElement("div");
        line.className = `log-line ${typeClass}`;
        line.textContent = msg;
        terminalLogs.appendChild(line);
        terminalLogs.scrollTop = terminalLogs.scrollHeight;
    }

    function getLogClass(status) {
        if (status === "error") return "error";
        if (status === "completed") return "success";
        return "info";
    }

    function getCurTime() {
        const now = new Date();
        return now.toTimeString().split(" ")[0];
    }

    btnClearLogs.addEventListener("click", () => {
        terminalLogs.innerHTML = "";
    });

    // --------------------------------------------------------
    // 6. RPA 전체 파이프라인 실행 트리거
    // --------------------------------------------------------
    btnStartRpa.addEventListener("click", async () => {
        const companies = getCompaniesList();
        const sender = senderEmail.value.trim();
        const receiver = receiverEmail.value.trim();
        const appPassword = appPasswordInput.value.trim();
        const headless = headlessCheck.checked;

        if (!companies.length) {
            showToast("분석할 기업명을 하나 이상 입력하세요.", "warn");
            return;
        }

        if (rememberPasswordCheck.checked) {
            localStorage.setItem(STORAGE_KEY, appPassword);
        }

        try {
            btnStartRpa.disabled = true;
            btnStartRpa.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> 작업 요청 중...';

            const resp = await fetch("/api/run", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    companies,
                    sender,
                    receiver,
                    app_password: appPassword,
                    headless
                })
            });

            const res = await resp.json();
            if (resp.ok) {
                showToast("RPA 자동화 파이프라인이 시작되었습니다.", "info");
                terminalLogs.innerHTML = "";
                addLogLine(`[${getCurTime()}] RPA 파이프라인 기동 요청 완료`, "info");
            } else {
                showToast(res.error || "실행 요청 실패", "error");
                btnStartRpa.disabled = false;
                btnStartRpa.innerHTML = '<i class="fa-solid fa-play"></i> RPA 전체 자동화 실행';
            }
        } catch (err) {
            showToast(`요청 실패: ${err.message}`, "error");
            btnStartRpa.disabled = false;
            btnStartRpa.innerHTML = '<i class="fa-solid fa-play"></i> RPA 전체 자동화 실행';
        }
    });

    // --------------------------------------------------------
    // 7. 이메일만 재발송 트리거 (요구사항 3: 비즈니스 메일)
    // --------------------------------------------------------
    btnSendEmailOnly.addEventListener("click", async () => {
        const sender = senderEmail.value.trim();
        const receiver = receiverEmail.value.trim();
        const appPassword = appPasswordInput.value.trim();

        if (!appPassword) {
            showToast("Gmail 앱 비밀번호를 입력해주세요.", "warn");
            return;
        }

        btnSendEmailOnly.disabled = true;
        btnSendEmailOnly.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> 메일 발송 중...';

        try {
            const resp = await fetch("/api/send-email", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    sender,
                    receiver,
                    app_password: appPassword
                })
            });

            const res = await resp.json();
            if (resp.ok) {
                showToast(res.message, "success");
                addLogLine(`[${getCurTime()}] 비즈니스 이메일 발송 완료 -> 수신자: ${receiver}`, "success");
            } else {
                showToast(res.error || "메일 전송 실패", "error");
                addLogLine(`[${getCurTime()}] 메일 발송 오류: ${res.error}`, "error");
            }
        } catch (err) {
            showToast(`발송 요청 중 네트워크 오류: ${err.message}`, "error");
        } finally {
            btnSendEmailOnly.disabled = false;
            btnSendEmailOnly.innerHTML = '<i class="fa-solid fa-envelope"></i> 결과 이메일만 재발송';
        }
    });

    // --------------------------------------------------------
    // 8. 대시보드 데이터 로드 & 차트 렌더링 (요구사항 5: 원형그래프 대시보드)
    // --------------------------------------------------------
    async function loadDashboardData() {
        try {
            const resp = await fetch("/api/status");
            const data = await resp.json();

            if (!data.summary || !data.summary.has_data) {
                summaryTableBody.innerHTML = '<tr><td colspan="5" class="text-center py-4 text-muted">저장된 집계 데이터가 없습니다. 먼저 RPA를 실행하세요.</td></tr>';
                companyDonutsContainer.innerHTML = '<div class="loading-placeholder">RPA 실행 후 원형 그래프가 생성됩니다.</div>';
                return;
            }

            const s = data.summary;

            // KPI 업데이트
            kpiTotalArticles.innerText = s.overall.total.toLocaleString();
            kpiPositive.innerText = s.overall.positive.toLocaleString();
            kpiNegative.innerText = s.overall.negative.toLocaleString();
            kpiPosRatio.innerText = `${s.overall.pos_ratio}%`;

            // 1) 전체 반응 도넛 차트
            renderOverallDonutChart(s.overall.positive, s.overall.negative);

            // 2) 기업별 비교 바 차트
            renderCompanyBarChart(s.table_data);

            // 3) 기업별 개별 원형/도넛 차트 그리드
            renderCompanyDonutCharts(s.by_company);

            // 4) 집계 데이터 테이블
            renderSummaryTable(s.table_data);

            // 5) 기사 미리보기 테이블
            cachedArticles = s.articles || [];
            renderArticlesTable(cachedArticles);

        } catch (err) {
            console.error("대시보드 데이터 로드 오류:", err);
        }
    }

    btnRefreshData.addEventListener("click", () => {
        loadDashboardData();
        showToast("대시보드 데이터를 갱신했습니다.", "info");
    });

    // Chart 1: 전체 시장 반응 도넛 차트
    function renderOverallDonutChart(pos, neg) {
        const ctx = document.getElementById("overallDonutChart").getContext("2d");
        if (overallChartInstance) overallChartInstance.destroy();

        overallChartInstance = new Chart(ctx, {
            type: "doughnut",
            data: {
                labels: ["긍정 반응", "부정 반응"],
                datasets: [{
                    data: [pos, neg],
                    backgroundColor: ["#10b981", "#f43f5e"],
                    borderColor: ["#0b0f19", "#0b0f19"],
                    borderWidth: 4,
                    hoverOffset: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: "bottom",
                        labels: { color: "#e2e8f0", font: { size: 12, family: "Pretendard" }, padding: 16 }
                    },
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                const total = pos + neg;
                                const val = context.raw;
                                const pct = total > 0 ? ((val / total) * 100).toFixed(1) : 0;
                                return ` ${context.label}: ${val}건 (${pct}%)`;
                            }
                        }
                    }
                },
                cutout: "68%"
            }
        });
    }

    // Chart 2: 기업별 비교 바 차트
    function renderCompanyBarChart(tableData) {
        const ctx = document.getElementById("companyBarChart").getContext("2d");
        if (companyBarChartInstance) companyBarChartInstance.destroy();

        const labels = tableData.map(d => d.company);
        const posData = tableData.map(d => d.positive);
        const negData = tableData.map(d => d.negative);

        companyBarChartInstance = new Chart(ctx, {
            type: "bar",
            data: {
                labels,
                datasets: [
                    {
                        label: "긍정(+)",
                        data: posData,
                        backgroundColor: "#10b981",
                        borderRadius: 6
                    },
                    {
                        label: "부정(-)",
                        data: negData,
                        backgroundColor: "#f43f5e",
                        borderRadius: 6
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: "bottom",
                        labels: { color: "#e2e8f0", font: { size: 12, family: "Pretendard" } }
                    }
                },
                scales: {
                    x: {
                        ticks: { color: "#94a3b8", font: { family: "Pretendard" } },
                        grid: { display: false }
                    },
                    y: {
                        ticks: { color: "#94a3b8", stepSize: 5 },
                        grid: { color: "#1e293b" }
                    }
                }
            }
        });
    }

    // Chart 3: 각 기업별 개별 도넛/원형 그래프 그리드 렌더링
    function renderCompanyDonutCharts(byCompany) {
        companyDonutsContainer.innerHTML = "";
        const companies = Object.keys(byCompany);

        if (!companies.length) {
            companyDonutsContainer.innerHTML = '<div class="loading-placeholder">표시할 기업별 데이터가 없습니다.</div>';
            return;
        }

        companies.forEach((comp, idx) => {
            const data = byCompany[comp];
            const canvasId = `companyDonut_${idx}`;

            const box = document.createElement("div");
            box.className = "company-chart-box";
            box.innerHTML = `
                <div class="company-chart-title">${comp}</div>
                <div class="company-chart-meta">전체 ${data.total}건 · 긍정률 <strong style="color:${data.pos_ratio >= 50 ? '#34d399' : '#fb7185'}">${data.pos_ratio}%</strong></div>
                <div class="company-donut-canvas-wrap">
                    <canvas id="${canvasId}"></canvas>
                </div>
            `;
            companyDonutsContainer.appendChild(box);

            const ctx = document.getElementById(canvasId).getContext("2d");
            if (companyDonutInstances[comp]) companyDonutInstances[comp].destroy();

            companyDonutInstances[comp] = new Chart(ctx, {
                type: "doughnut",
                data: {
                    labels: ["긍정", "부정"],
                    datasets: [{
                        data: [data.positive, data.negative],
                        backgroundColor: ["#10b981", "#f43f5e"],
                        borderColor: ["#0d1424", "#0d1424"],
                        borderWidth: 3
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: "bottom",
                            labels: { color: "#cbd5e1", font: { size: 11, family: "Pretendard" }, boxWidth: 10 }
                        },
                        tooltip: {
                            callbacks: {
                                label: (c) => ` ${c.label}: ${c.raw}건 (${data.total > 0 ? ((c.raw / data.total)*100).toFixed(1) : 0}%)`
                            }
                        }
                    },
                    cutout: "60%"
                }
            });
        });
    }

    // 통계 요약 테이블 렌더링
    function renderSummaryTable(tableData) {
        summaryTableBody.innerHTML = "";
        tableData.forEach(row => {
            const tr = document.createElement("tr");
            const ratioColor = row.ratio >= 60 ? "#34d399" : (row.ratio >= 40 ? "#fbbf24" : "#fb7185");
            tr.innerHTML = `
                <td><strong>${row.company}</strong></td>
                <td class="text-center"><span class="sentiment-badge sentiment-pos">+${row.positive}</span></td>
                <td class="text-center"><span class="sentiment-badge sentiment-neg">-${row.negative}</span></td>
                <td class="text-center"><strong>${row.total}</strong>건</td>
                <td class="text-right" style="color:${ratioColor}; font-weight:700;">${row.ratio}%</td>
            `;
            summaryTableBody.appendChild(tr);
        });
    }

    // 기사 목록 렌더링
    function renderArticlesTable(articles) {
        articlesTableBody.innerHTML = "";
        if (!articles.length) {
            articlesTableBody.innerHTML = '<tr><td colspan="4" class="text-center py-3 text-muted">표시할 기사 데이터가 없습니다.</td></tr>';
            return;
        }

        articles.forEach(art => {
            const tr = document.createElement("tr");
            let badgeClass = "sentiment-neu";
            if (art.sentiment === "긍정") badgeClass = "sentiment-pos";
            else if (art.sentiment === "부정") badgeClass = "sentiment-neg";

            tr.innerHTML = `
                <td>${art.company}</td>
                <td class="text-center"><span class="sentiment-badge ${badgeClass}">${art.sentiment}</span></td>
                <td>${art.title}</td>
                <td class="text-center">
                    <a href="${art.url}" target="_blank" rel="noopener noreferrer" class="article-link" title="네이버 카페 바로가기">
                        <i class="fa-solid fa-arrow-up-right-from-square"></i>
                    </a>
                </td>
            `;
            articlesTableBody.appendChild(tr);
        });
    }

    // 기사 검색 필터링
    articleFilterInput.addEventListener("input", (e) => {
        const query = e.target.value.toLowerCase();
        const filtered = cachedArticles.filter(a => 
            a.title.toLowerCase().includes(query) || 
            a.company.toLowerCase().includes(query) ||
            a.sentiment.toLowerCase().includes(query)
        );
        renderArticlesTable(filtered);
    });

    // --------------------------------------------------------
    // 9. Toast Helper
    // --------------------------------------------------------
    function showToast(message, type = "info") {
        const container = document.getElementById("toastContainer");
        const toast = document.createElement("div");
        toast.className = `toast ${type}`;
        
        let icon = "fa-info-circle";
        if (type === "success") icon = "fa-check-circle";
        else if (type === "error") icon = "fa-exclamation-triangle";
        else if (type === "warn") icon = "fa-triangle-exclamation";

        toast.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${message}</span>`;
        container.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = "0";
            toast.style.transform = "translateX(100%)";
            toast.style.transition = "all 0.4s ease";
            setTimeout(() => toast.remove(), 400);
        }, 3500);
    }

    // --------------------------------------------------------
    // 10. 초기화 실행
    // --------------------------------------------------------
    initEventSource();
    loadDashboardData();
});
