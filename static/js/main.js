document.addEventListener("DOMContentLoaded", () => {
  const dashboardApp = document.getElementById("dashboard-app");
  if (dashboardApp) {
    setupDashboard(dashboardApp);
  }

  const revealItems = document.querySelectorAll(".reveal");
  if (!revealItems.length) return;

  if (!("IntersectionObserver" in window)) {
    revealItems.forEach((item) => item.classList.add("is-visible"));
    return;
  }

  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("is-visible");
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.15 });

  revealItems.forEach((item) => observer.observe(item));
});

function setupDashboard(root) {
  const apiUrl = root.dataset.trendsApi || "/api/trends";
  const grid = document.getElementById("trend-grid");
  const emptyState = document.getElementById("dashboard-empty");
  const status = document.getElementById("dashboard-status");
  const alertsList = document.getElementById("alerts-list");
  const alertsEmpty = document.getElementById("alerts-empty");
  const fetchRedditBtn = document.getElementById("fetch-reddit-btn");
  const fetchGoogleBtn = document.getElementById("fetch-google-btn");
  const fetchLiveBtn = document.getElementById("fetch-live-btn");
  const analyzeTrendsBtn = document.getElementById("analyze-trends-btn");
  const ragAnalyzeBtn = document.getElementById("rag-analyze-btn");
  const forecastTrendsBtn = document.getElementById("forecast-trends-btn");
  const generateContentBtn = document.getElementById("generate-content-btn");
  const generateAlertsBtn = document.getElementById("generate-alerts-btn");
  const refreshBtn = document.getElementById("refresh-dashboard-btn");
  const dashboardLoader = document.getElementById("dashboard-loader");
  const statusText = document.querySelector("#dashboard-status .dashboard-status__text");
  const searchInput = document.getElementById("trend-search");
  const platformFilter = document.getElementById("platform-filter");
  const viralityFilter = document.getElementById("virality-filter");
  const sentimentFilter = document.getElementById("sentiment-filter");
  const sortFilter = document.getElementById("sort-filter");
  const statTotal = document.getElementById("stat-total");
  const statHighViral = document.getElementById("stat-high-viral");
  const statActiveAlerts = document.getElementById("stat-active-alerts");
  const statExplodingForecasts = document.getElementById("stat-exploding-forecasts");
  const forecastLikely = document.getElementById("forecast-likely");
  const forecastOpportunity = document.getElementById("forecast-opportunity");
  const forecastRisky = document.getElementById("forecast-risky");
  const forecastDownward = document.getElementById("forecast-downward");
  const intelRagTitle = document.getElementById("intel-rag-title");
  const intelRagText = document.getElementById("intel-rag-text");
  const intelForecastTitle = document.getElementById("intel-forecast-title");
  const intelForecastText = document.getElementById("intel-forecast-text");
  const intelSourceTitle = document.getElementById("intel-source-title");
  const intelSourceText = document.getElementById("intel-source-text");
  const intelLiveTitle = document.getElementById("intel-live-title");
  const intelLiveText = document.getElementById("intel-live-text");
  const toast = document.getElementById("toast");
  const modal = document.getElementById("content-modal");
  const modalBody = document.getElementById("content-modal-body");
  const modalTitle = document.getElementById("content-modal-title");
  const trendModal = document.getElementById("trend-modal");
  const trendModalBody = document.getElementById("trend-modal-body");
  const trendModalTitle = document.getElementById("trend-modal-title");
  const aiModal = document.getElementById("ai-modal");
  const aiModalBody = document.getElementById("ai-modal-body");
  const aiModalTitle = document.getElementById("ai-modal-title");
  const ragModal = document.getElementById("rag-modal");
  const ragModalBody = document.getElementById("rag-modal-body");
  const ragModalTitle = document.getElementById("rag-modal-title");
  const forecastModal = document.getElementById("forecast-modal");
  const forecastModalBody = document.getElementById("forecast-modal-body");
  const forecastModalTitle = document.getElementById("forecast-modal-title");
  const liveStatusDot = document.getElementById("live-status-dot");
  const liveStatusText = document.getElementById("live-status-text");
  const liveOnlineCount = document.getElementById("live-online-count");
  const liveUpdatedAt = document.getElementById("live-updated-at");
  const liveTicker = document.getElementById("live-ticker");
  const liveActivityFeed = document.getElementById("live-activity-feed");
  const soundToggle = document.getElementById("sound-toggle");
  const trendSkeletons = document.getElementById("trend-skeletons");
  const alertsApiUrl = "/api/alerts";

  const state = {
    allTrends: [],
    filteredTrends: [],
    alerts: [],
    filters: {
      search: "",
      platform: "all",
      virality: "all",
      sentiment: "all",
      sort: "latest",
    },
    loading: false,
    ws: {
      socket: null,
      reconnectTimer: null,
      refreshTimer: null,
      reconnectDelay: 1000,
      connected: false,
      soundEnabled: false,
      lastUpdated: null,
      onlineUsers: 0,
      currentRagTrendId: null,
      currentRagPayload: null,
      currentForecastTrendId: null,
      currentForecastPayload: null,
    },
  };

  function setStatus(message) {
    if (statusText) {
      statusText.textContent = message;
    } else if (status) {
      status.textContent = message;
    }
  }

  function setLoading(isLoading) {
    state.loading = isLoading;
    [fetchRedditBtn, fetchGoogleBtn, fetchLiveBtn, analyzeTrendsBtn, ragAnalyzeBtn, forecastTrendsBtn, generateContentBtn, generateAlertsBtn, refreshBtn].forEach((button) => {
      if (button) button.disabled = isLoading;
    });
    if (dashboardLoader) {
      dashboardLoader.style.display = isLoading ? "inline-flex" : "none";
      dashboardLoader.classList.toggle("is-loading", isLoading);
    }
    if (status) {
      status.classList.toggle("is-loading", isLoading);
    }
    if (trendSkeletons) {
      trendSkeletons.classList.toggle("is-visible", isLoading && state.allTrends.length === 0);
    }
  }

  function setLiveStatus(connected, message) {
    state.ws.connected = connected;
    if (liveStatusDot) {
      liveStatusDot.classList.toggle("is-live", connected);
    }
    if (liveStatusText) {
      liveStatusText.textContent = message || (connected ? "Connected" : "Disconnected");
    }
    renderIntelligencePanel();
  }

  function updateLiveMeta(timestamp) {
    state.ws.lastUpdated = timestamp || new Date().toISOString();
    if (liveUpdatedAt) {
      liveUpdatedAt.textContent = formatDate(state.ws.lastUpdated);
    }
    renderIntelligencePanel();
  }

  function updateOnlineUsers(count) {
    state.ws.onlineUsers = Number(count || 0);
    if (liveOnlineCount) {
      liveOnlineCount.textContent = String(state.ws.onlineUsers);
    }
  }

  function scheduleLiveRefresh(reason = "live update") {
    window.clearTimeout(state.ws.refreshTimer);
    state.ws.refreshTimer = window.setTimeout(async () => {
      try {
        await loadDashboard();
        await loadAlerts();
        addActivity(`Dashboard refreshed from ${reason}.`, "info");
      } catch (error) {
        console.warn("Live refresh failed", error);
      }
    }, 350);
  }

  function setTickerText(message) {
    if (liveTicker) {
      liveTicker.innerHTML = `<span>${escapeHtml(message || "Waiting for live updates...")}</span>`;
    }
  }

  function addActivity(message, level = "info", detail = "") {
    if (!liveActivityFeed) return;
    const item = document.createElement("div");
    item.className = `live-activity-item live-activity-item--${badgeKey(level || "info")}`;
    item.innerHTML = `
      <div>
        <strong>${escapeHtml(message)}</strong>
        ${detail ? `<div>${escapeHtml(detail)}</div>` : ""}
      </div>
      <span>${escapeHtml(formatDate(new Date().toISOString()))}</span>
    `;
    liveActivityFeed.prepend(item);
    while (liveActivityFeed.children.length > 6) {
      liveActivityFeed.removeChild(liveActivityFeed.lastElementChild);
    }
    if (message) {
      setTickerText(message);
    }
  }

  function playAlertTone() {
    if (!state.ws.soundEnabled || typeof window.AudioContext === "undefined") return;
    try {
      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      const oscillator = audioContext.createOscillator();
      const gain = audioContext.createGain();
      oscillator.type = "sine";
      oscillator.frequency.value = 880;
      gain.gain.value = 0.0001;
      oscillator.connect(gain);
      gain.connect(audioContext.destination);
      oscillator.start();
      gain.gain.exponentialRampToValueAtTime(0.08, audioContext.currentTime + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.0001, audioContext.currentTime + 0.18);
      oscillator.stop(audioContext.currentTime + 0.2);
    } catch (error) {
      console.warn("Sound notification failed", error);
    }
  }

  function markCardLive(trend) {
    const sourceUid = trend.source_uid ? String(trend.source_uid) : "";
    const escapedUid = window.CSS && typeof window.CSS.escape === "function" ? window.CSS.escape(sourceUid) : sourceUid.replaceAll('"', '\\"');
    const selector = sourceUid ? `[data-source-uid="${escapedUid}"]` : null;
    const card = selector ? grid?.querySelector(selector) : null;
    if (!card) return;
    card.classList.add("is-live-pulse");
    window.setTimeout(() => card.classList.remove("is-live-pulse"), 1300);
  }

  function normalizeTrendIdentity(trend) {
    return String(trend?.source_uid || trend?.id || `${trend?.platform || ""}:${trend?.title || trend?.name || ""}`);
  }

  function upsertTrend(trend, options = {}) {
    if (!trend) return;
    const identity = normalizeTrendIdentity(trend);
    const existingIndex = state.allTrends.findIndex((item) => normalizeTrendIdentity(item) === identity);
    const nextTrend = existingIndex >= 0 ? { ...state.allTrends[existingIndex], ...trend } : { ...trend };
    if (existingIndex >= 0) {
      state.allTrends[existingIndex] = nextTrend;
    } else {
      state.allTrends.unshift(nextTrend);
    }
    if (options.highlight) {
      markCardLive(nextTrend);
    }
    applyFilters();
  }

  function upsertAlert(alert) {
    if (!alert) return;
    const existingIndex = state.alerts.findIndex((item) => String(item.id) === String(alert.id));
    const nextAlert = existingIndex >= 0 ? { ...state.alerts[existingIndex], ...alert } : { ...alert };
    if (existingIndex >= 0) {
      state.alerts[existingIndex] = nextAlert;
    } else {
      state.alerts.unshift(nextAlert);
    }
    renderAlerts(state.alerts);
    renderStats(state.filteredTrends.length ? state.filteredTrends : state.allTrends);
  }

  function updateRagPanel(payload) {
    state.ws.currentRagPayload = payload;
    state.ws.currentRagTrendId = payload?.trend_id || null;
    if (ragModal && ragModal.classList.contains("is-open") && ragModalBody) {
      ragModalBody.innerHTML = renderRagAnalysis(payload);
    }
    renderIntelligencePanel();
  }

  function handleWebSocketMessage(event) {
    let message = null;
    try {
      message = JSON.parse(event.data);
    } catch (error) {
      console.warn("Invalid websocket payload", error);
      return;
    }

    const payload = message.payload || {};
    updateOnlineUsers(message.active_connections ?? payload.active_connections ?? state.ws.onlineUsers);
    updateLiveMeta(message.timestamp);

    switch (message.type) {
      case "connection_status":
        setLiveStatus(Boolean(payload.connected), payload.message || "Connected to live dashboard.");
        addActivity(payload.message || "Connection updated.", "info");
        break;
      case "trend_update":
        upsertTrend(payload.trend, { highlight: true });
        addActivity(`New ${payload.trend?.platform || "trend"} trend detected`, "info", payload.trend?.title || "");
        scheduleLiveRefresh("trend update");
        break;
      case "alert_update":
        upsertAlert(payload.alert);
        addActivity(`High virality alert triggered for ${payload.alert?.title || "a trend"}.`, "warning", payload.alert?.message || "");
        if (payload.alert?.virality_score >= 75) {
          showToast(`${payload.alert.title || "Trend"} alert went live.`);
          playAlertTone();
        }
        scheduleLiveRefresh("alert update");
        break;
      case "virality_update":
        upsertTrend(payload.trend, { highlight: true });
        addActivity(`Virality score updated for ${payload.trend?.title || "a trend"}.`, "info");
        scheduleLiveRefresh("virality update");
        break;
      case "forecast_update":
        upsertTrend(payload.trend, { highlight: true });
        state.ws.currentForecastPayload = {
          current_trend: payload.trend?.title || payload.current_trend || "Trend",
          forecast: payload.forecast || payload.trend || null,
          similar_trends: payload.similar_trends || [],
        };
        addActivity(`Forecast updated for ${payload.trend?.title || "a trend"}.`, "info");
        showToast(`Forecast refreshed for ${payload.trend?.title || "a trend"}.`);
        renderIntelligencePanel();
        scheduleLiveRefresh("forecast update");
        break;
      case "rag_update":
        updateRagPanel(payload);
        addActivity(`AI generated a new recommendation for ${payload.current_trend || "a trend"}.`, "success");
        showToast(`AI recommendation updated for ${payload.current_trend || "a trend"}.`);
        scheduleLiveRefresh("RAG analysis");
        break;
      case "activity":
        addActivity(payload.message || "Live activity received.", payload.level || "info");
        if (payload.kind === "trend_fetch" || payload.kind === "analysis" || payload.kind === "content_idea" || payload.kind === "forecast") {
          scheduleLiveRefresh(payload.kind.replaceAll("_", " "));
        }
        break;
      case "pong":
        updateLiveMeta(message.timestamp);
        break;
      default:
        addActivity(`Live event: ${message.type || "unknown"}`, "info");
        break;
    }
  }

  function scheduleReconnect() {
    if (state.ws.reconnectTimer) {
      window.clearTimeout(state.ws.reconnectTimer);
    }
    const delay = state.ws.reconnectDelay;
    state.ws.reconnectTimer = window.setTimeout(() => {
      connectWebSocket();
    }, delay);
    state.ws.reconnectDelay = Math.min(delay * 2, 30000);
    setLiveStatus(false, `Reconnecting in ${Math.round(delay / 1000)}s...`);
  }

  function connectWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws/dashboard`;

    try {
      if (state.ws.socket && (state.ws.socket.readyState === WebSocket.OPEN || state.ws.socket.readyState === WebSocket.CONNECTING)) {
        state.ws.socket.close();
      }
      const socket = new WebSocket(wsUrl);
      state.ws.socket = socket;
      setLiveStatus(false, "Connecting to live dashboard...");

      socket.addEventListener("open", () => {
        state.ws.reconnectDelay = 1000;
        setLiveStatus(true, "Live dashboard connected.");
        addActivity("Live dashboard connection established.", "success");
        socket.send(JSON.stringify({ type: "subscribe", source: "dashboard" }));
      });

      socket.addEventListener("message", handleWebSocketMessage);

      socket.addEventListener("close", () => {
        setLiveStatus(false, "Connection lost. Reconnecting...");
        scheduleReconnect();
      });

      socket.addEventListener("error", () => {
        setLiveStatus(false, "WebSocket error detected.");
      });
    } catch (error) {
      console.error("Failed to open websocket", error);
      setLiveStatus(false, "WebSocket unavailable.");
      scheduleReconnect();
    }
  }

  function formatDate(value) {
    if (!value) return "Just now";
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? "Just now" : date.toLocaleString();
  }

  function safeNumber(value) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function viralityLabelFromScore(score) {
    const value = safeNumber(score);
    if (value >= 75) return "High Viral";
    if (value >= 45) return "Medium Viral";
    return "Low Viral";
  }

  function currentSentimentLabel(trend) {
    return trend.sentiment_label || "Neutral";
  }

  function currentViralityLabel(trend) {
    return trend.virality_label || viralityLabelFromScore(trend.virality_score);
  }

  function currentPredictionLabel(trend) {
    return trend.prediction_label || "Pending";
  }

  function currentForecastConfidence(trend) {
    return safeNumber(trend.forecast_confidence);
  }

  function currentViralityProbability(trend) {
    const value = safeNumber(trend.virality_probability);
    return value <= 1 ? value * 100 : value;
  }

  function currentOpportunityScore(trend) {
    return safeNumber(trend.opportunity_score);
  }

  function currentRiskScore(trend) {
    return safeNumber(trend.risk_score);
  }

  function currentTrendScore(trend) {
    return trend.trend_score ?? trend.search_interest ?? 0;
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function badgeKey(value) {
    return String(value || "")
      .toLowerCase()
      .replaceAll(/[^a-z0-9]+/g, "-")
      .replaceAll(/^-+|-+$/g, "");
  }

  function formatMetricValue(value) {
    if (value === null || value === undefined || value === "") return "";
    return escapeHtml(value);
  }

  function calculateStats(items) {
    const total = items.length;
    const highViral = items.filter((trend) => safeNumber(trend.virality_score) >= 75).length;
    const activeAlerts = state.alerts.filter((alert) => !alert.is_read).length;
    const explodingForecasts = items.filter((trend) => (trend.prediction_label || "").toUpperCase() === "EXPLODING").length;

    if (statTotal) statTotal.textContent = String(total);
    if (statHighViral) statHighViral.textContent = String(highViral);
    if (statActiveAlerts) statActiveAlerts.textContent = String(activeAlerts);
    if (statExplodingForecasts) statExplodingForecasts.textContent = String(explodingForecasts);
  }

  function calculateForecastStats(items) {
    const likely = items.filter((trend) => ["EXPLODING", "GROWING"].includes((trend.prediction_label || "").toUpperCase())).length;
    const opportunity = items.filter((trend) => safeNumber(trend.opportunity_score) >= 75).length;
    const risky = items.filter((trend) => safeNumber(trend.risk_score) >= 60).length;
    const downward = items.filter((trend) => ["DECLINING", "SATURATED"].includes((trend.prediction_label || "").toUpperCase())).length;

    if (forecastLikely) forecastLikely.textContent = String(likely);
    if (forecastOpportunity) forecastOpportunity.textContent = String(opportunity);
    if (forecastRisky) forecastRisky.textContent = String(risky);
    if (forecastDownward) forecastDownward.textContent = String(downward);
  }

  function renderIntelligencePanel() {
    const trends = state.filteredTrends.length ? state.filteredTrends : state.allTrends;
    const ragPayload = state.ws.currentRagPayload || {};
    const ragAnalysis = ragPayload.rag_analysis || {};
    const forecastPayload = state.ws.currentForecastPayload || {};
    const bestForecast = getBestForecastTrend(trends);
    const topSource = getTopSource(trends);

    if (intelRagTitle) {
      intelRagTitle.textContent = ragPayload.current_trend || "No RAG insight yet";
    }
    if (intelRagText) {
      intelRagText.textContent = ragAnalysis.final_recommendation || ragAnalysis.summary || "Run RAG analysis to ground the next move in historical context.";
    }

    const forecastTrend = forecastPayload.forecast || bestForecast;
    if (intelForecastTitle) {
      intelForecastTitle.textContent = forecastPayload.current_trend || forecastTrend?.title || "No forecast yet";
    }
    if (intelForecastText) {
      intelForecastText.textContent = forecastTrend?.forecast_explanation || forecastTrend?.recommended_creator_actions?.[0] || "Generate a forecast to see the strongest recommendation.";
    }

    if (intelSourceTitle) {
      intelSourceTitle.textContent = topSource.label || "Not available";
    }
    if (intelSourceText) {
      intelSourceText.textContent = topSource.detail || "Fetch or refresh live trends to identify the most active source.";
    }

    if (intelLiveTitle) {
      intelLiveTitle.textContent = state.ws.connected ? "Connected live" : "Reconnecting";
    }
    if (intelLiveText) {
      const liveBits = [];
      liveBits.push(`${state.ws.onlineUsers} connected users`);
      if (state.ws.lastUpdated) {
        liveBits.push(`Last update ${formatDate(state.ws.lastUpdated)}`);
      } else {
        liveBits.push("Awaiting the first live event");
      }
      intelLiveText.textContent = liveBits.join(" · ");
    }
  }

  function getBestForecastTrend(items) {
    const candidates = items.filter((trend) => trend && (trend.prediction_label || trend.virality_probability || trend.forecast_confidence));
    if (!candidates.length) return null;

    const weighted = [...candidates].sort((a, b) => {
      const weightA = forecastRank(a.prediction_label) * 1000 + safeNumber(a.forecast_confidence) * 10 + safeNumber(a.opportunity_score);
      const weightB = forecastRank(b.prediction_label) * 1000 + safeNumber(b.forecast_confidence) * 10 + safeNumber(b.opportunity_score);
      return weightB - weightA;
    });
    return weighted[0] || null;
  }

  function forecastRank(label) {
    const value = String(label || "").toUpperCase();
    if (value === "EXPLODING") return 5;
    if (value === "GROWING") return 4;
    if (value === "STABLE") return 3;
    if (value === "DECLINING") return 2;
    if (value === "SATURATED") return 1;
    return 0;
  }

  function getTopSource(items) {
    if (!items.length) {
      return { label: "Not available", detail: "No trends have been loaded yet." };
    }

    const counts = new Map();
    items.forEach((trend) => {
      const key = String(trend.platform || trend.source_label || trend.source_type || "unknown").toLowerCase();
      const entry = counts.get(key) || { count: 0, label: trend.source_label || trend.platform || "Unknown" };
      entry.count += 1;
      counts.set(key, entry);
    });

    let top = null;
    for (const [key, value] of counts.entries()) {
      if (!top || value.count > top.count) {
        top = { key, ...value };
      }
    }

    if (!top) {
      return { label: "Not available", detail: "No source distribution is available." };
    }

    return {
      label: top.label,
      detail: `${top.count} trends from ${top.label} are currently visible.`,
    };
  }

  function showToast(message) {
    if (!toast) return;
    toast.textContent = message;
    toast.classList.add("is-visible");
    window.clearTimeout(showToast._timer);
    showToast._timer = window.setTimeout(() => {
      toast.classList.remove("is-visible");
    }, 3500);
  }

  function updateEmptyState(items) {
    if (!emptyState || !grid) return;
    const isEmpty = items.length === 0;
    emptyState.style.display = isEmpty ? "grid" : "none";
    grid.style.display = isEmpty ? "none" : "grid";
  }

  function applyFilters() {
    const search = state.filters.search.toLowerCase().trim();
    const platform = state.filters.platform;
    const virality = state.filters.virality;
    const sentiment = state.filters.sentiment;
    const sort = state.filters.sort;

    let items = [...state.allTrends];

    if (search) {
      items = items.filter((trend) => {
        const haystack = [
          trend.title,
          trend.name,
          trend.subreddit,
          trend.platform,
          trend.source_label,
          trend.source_type,
          trend.content_angle,
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();
        return haystack.includes(search);
      });
    }

    if (platform !== "all") {
      items = items.filter((trend) => (trend.platform || "").toLowerCase() === platform);
    }

    if (virality !== "all") {
      items = items.filter((trend) => currentViralityLabel(trend) === virality);
    }

    if (sentiment !== "all") {
      items = items.filter((trend) => currentSentimentLabel(trend) === sentiment);
    }

    items.sort((a, b) => {
      if (sort === "virality") {
        return safeNumber(b.virality_score) - safeNumber(a.virality_score);
      }
      if (sort === "upvotes") {
        return safeNumber(b.upvotes) - safeNumber(a.upvotes);
      }
      if (sort === "comments") {
        return safeNumber(b.comments) - safeNumber(a.comments);
      }

      const dateA = new Date(a.fetched_at || a.analyzed_at || 0).getTime();
      const dateB = new Date(b.fetched_at || b.analyzed_at || 0).getTime();
      return dateB - dateA;
    });

    state.filteredTrends = items;
    renderStats(items);
    renderTrends(items);
  }

  function renderStats(items) {
    calculateStats(items);
    calculateForecastStats(items);
    renderIntelligencePanel();
  }

  function renderAlerts(alerts) {
    if (!alertsList) return;
    alertsList.innerHTML = "";
    const items = Array.isArray(alerts) ? alerts : [];
    if (alertsEmpty) {
      alertsEmpty.style.display = items.length ? "none" : "grid";
    }

    if (!items.length) return;

    items.forEach((alert) => {
      const card = document.createElement("article");
      card.className = `alert-card glass-panel ${alert.is_read ? "" : "is-unread"}`;
      card.innerHTML = `
        <div class="alert-card__top">
          <div>
            <p class="trend-platform">${escapeHtml(alert.platform || "unknown")}</p>
            <h3>${escapeHtml(alert.title || "Untitled trend")}</h3>
          </div>
          <span class="trend-badge ${alert.is_read ? "alert-read" : "alert-unread"}">${alert.is_read ? "Read" : "Unread"}</span>
        </div>
        <p class="alert-message">${escapeHtml(alert.message || "")}</p>
        <div class="alert-card__meta">
          <span>Virality ${escapeHtml(alert.virality_score ?? 0)}</span>
          <span>${escapeHtml(alert.virality_label || "High Viral")}</span>
          <span>${escapeHtml(formatDate(alert.created_at))}</span>
        </div>
        <div class="alert-card__actions">
          ${
            alert.is_read
              ? `<button class="button secondary alert-action-btn" type="button" disabled>Marked Read</button>`
              : `<button class="button secondary alert-action-btn" type="button" data-mark-alert-read="${escapeHtml(
                  alert.id
                )}">Mark as Read</button>`
          }
        </div>
      `;

      const markReadButton = card.querySelector("[data-mark-alert-read]");
      if (markReadButton) {
        markReadButton.addEventListener("click", () => markAlertRead(alert.id));
      }

      alertsList.appendChild(card);
    });
  }

  function renderTrends(items) {
    if (!grid) return;
    grid.innerHTML = "";
    updateEmptyState(items);

    if (!items.length) return;

    items.forEach((trend) => {
      const title = trend.title || trend.name || "Untitled trend";
      const platform = trend.platform || "unknown";
      const sourceLabel = trend.source_label || platform.toUpperCase();
      const subreddit = trend.subreddit && trend.subreddit !== "n/a" ? trend.subreddit : "";
      const trendScore = currentTrendScore(trend);
      const upvotes = trend.upvotes ?? "";
      const comments = trend.comments ?? "";
      const fetchedAt = formatDate(trend.fetched_at);
      const analyzedAt = formatDate(trend.analyzed_at);
      const sourceType = trend.source_type || trend.source || "";
      const sentimentLabel = currentSentimentLabel(trend);
      const viralityScore = safeNumber(trend.virality_score);
      const viralityLabel = currentViralityLabel(trend);
      const predictionLabel = currentPredictionLabel(trend);
      const forecastConfidence = currentForecastConfidence(trend);
      const viralityProbability = currentViralityProbability(trend);
      const opportunityScore = currentOpportunityScore(trend);
      const riskScore = currentRiskScore(trend);
      const hasContentIdea = Boolean(trend.has_content_idea);
      const contentIdeaPayload = trend.content_idea || null;
      const progressWidth = Math.max(0, Math.min(100, viralityScore));
      const forecastWidth = Math.max(0, Math.min(100, viralityProbability));

      const card = document.createElement("article");
      card.className = "trend-item-card glass-panel";
      card.setAttribute("data-source-uid", String(trend.source_uid || trend.id || title));
      card.innerHTML = `
        <div class="trend-item-card__top">
          <div>
            <p class="trend-platform">${escapeHtml(sourceLabel)}</p>
            <h3>${escapeHtml(title)}</h3>
          </div>
          <div class="trend-badge-group">
            <span class="trend-badge source-${badgeKey(sourceLabel)}">${escapeHtml(sourceLabel)}</span>
            <span class="trend-badge sentiment-${badgeKey(sentimentLabel)}">${escapeHtml(sentimentLabel)}</span>
            <span class="trend-badge virality-${badgeKey(viralityLabel)}">${escapeHtml(viralityLabel)}</span>
            <span class="trend-badge">${escapeHtml(platform)}</span>
          </div>
        </div>
        <div class="trend-progress">
          <div class="trend-progress__bar" style="width: ${progressWidth}%"></div>
        </div>
        <div class="forecast-mini">
          <div class="trend-badge-group">
            <span class="trend-badge prediction-${badgeKey(predictionLabel)}">${escapeHtml(predictionLabel)}</span>
            <span class="trend-badge forecast-confidence">${escapeHtml(`Confidence ${forecastConfidence.toFixed(0)}%`)}</span>
          </div>
          <div class="forecast-mini__meter">
            <div class="forecast-mini__bar" style="width: ${forecastWidth}%"></div>
          </div>
          <div class="trend-item-card__footer trend-item-card__footer--secondary forecast-mini__footer">
            <span>Opportunity ${escapeHtml(opportunityScore.toFixed(0))}%</span>
            <span>Risk ${escapeHtml(riskScore.toFixed(0))}%</span>
          </div>
        </div>
        <div class="trend-item-card__meta">
          ${metricCard("Subreddit", subreddit || "n/a")}
          ${metricCard("Upvotes", upvotes)}
          ${metricCard("Comments", comments)}
          ${metricCard("Trend score", trendScore)}
        </div>
        <div class="trend-item-card__footer">
          <span>${escapeHtml(trend.url || "")}</span>
          <span>Fetched ${escapeHtml(fetchedAt)}</span>
        </div>
        <div class="trend-item-card__footer trend-item-card__footer--secondary">
          <span>Analyzed ${escapeHtml(analyzedAt)}</span>
          <span>Virality ${escapeHtml(progressWidth.toFixed(0))}%</span>
        </div>
        <div class="trend-item-card__actions">
          <button class="button secondary trend-action-btn" type="button" data-view-details="true">View Details</button>
          <button class="button secondary trend-action-btn" type="button" data-view-forecast="true">View Forecast</button>
          <button class="button secondary trend-action-btn" type="button" data-view-ai-summary="true">View AI Summary</button>
          <button class="button secondary trend-action-btn" type="button" data-rag-analyze="true">RAG Analyze</button>
          ${
            hasContentIdea
              ? `<button class="button secondary trend-action-btn" type="button" data-view-content-idea="true">View Content Idea</button>`
              : ""
          }
        </div>
      `;

      const detailButton = card.querySelector("[data-view-details='true']");
      if (detailButton) {
        detailButton.addEventListener("click", () => openTrendDetailsModal(trend));
      }

      const forecastButton = card.querySelector("[data-view-forecast='true']");
      if (forecastButton) {
        forecastButton.addEventListener("click", () => openForecastModal(trend));
      }

      const viewButton = card.querySelector("[data-view-content-idea='true']");
      if (viewButton) {
        viewButton.addEventListener("click", () => openContentIdeaModal(trend));
      }

      const aiButton = card.querySelector("[data-view-ai-summary='true']");
      if (aiButton) {
        aiButton.addEventListener("click", () => openAiSummaryModal(trend));
      }

      const ragButton = card.querySelector("[data-rag-analyze='true']");
      if (ragButton) {
        ragButton.addEventListener("click", () => openRagModal(trend));
      }

      grid.appendChild(card);
    });
  }

  function metricCard(label, value) {
    if (value === null || value === undefined || value === "") return "";
    return `
      <div class="trend-metric">
        <span>${escapeHtml(label)}</span>
        <strong>${formatMetricValue(value)}</strong>
      </div>
    `;
  }

  async function loadDashboard() {
    setLoading(true);
    setStatus("Loading stored trends...");
    try {
      const response = await fetch(apiUrl, { headers: { Accept: "application/json" } });
      if (!response.ok) throw new Error(`Failed to load trends (${response.status})`);
      const data = await response.json();
      state.allTrends = Array.isArray(data.items) ? data.items : [];
      applyFilters();
      updateLiveMeta();
      setStatus(`Loaded ${state.allTrends.length} stored trends.`);
    } catch (error) {
      console.error(error);
      state.allTrends = [];
      applyFilters();
      updateLiveMeta();
      setStatus("Could not load trends. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  async function loadAlerts() {
    try {
      const response = await fetch(alertsApiUrl, { headers: { Accept: "application/json" } });
      if (!response.ok) throw new Error(`Failed to load alerts (${response.status})`);
      const data = await response.json();
      state.alerts = Array.isArray(data.items) ? data.items : [];
      renderAlerts(state.alerts);
      renderStats(state.filteredTrends.length ? state.filteredTrends : state.allTrends);
      updateLiveMeta();
    } catch (error) {
      console.error(error);
      state.alerts = [];
      renderAlerts([]);
      renderStats(state.filteredTrends.length ? state.filteredTrends : state.allTrends);
    }
  }

  async function runAction(url, message) {
    setLoading(true);
    setStatus(message);
    try {
      const response = await fetch(url, { headers: { Accept: "application/json" } });
      if (!response.ok) throw new Error(`Request failed (${response.status})`);
      const data = await response.json();
      if (url === "/api/generate-alerts") {
        const count = Number(data.count || 0);
        showToast(count > 0 ? `${count} new high viral trend alerts generated.` : "No new alerts were generated.");
      }
      await loadDashboard();
      await loadAlerts();
    } catch (error) {
      console.error(error);
      setStatus("The refresh request failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  async function openTrendDetailsModal(trend) {
    if (!trendModal || !trendModalBody || !trendModalTitle) return;
    trendModalTitle.textContent = `${trend.title || trend.name || "Trend"} details`;
    trendModalBody.innerHTML = `<p class="modal-loading">Loading trend details...</p>`;
    trendModal.setAttribute("aria-hidden", "false");
    trendModal.classList.add("is-open");

    try {
      const response = await fetch(`/api/trends/${trend.id}`, { headers: { Accept: "application/json" } });
      if (!response.ok) throw new Error(`Failed to load trend details (${response.status})`);
      const detail = await response.json();
      trendModalBody.innerHTML = renderTrendDetails(detail);
    } catch (error) {
      console.error(error);
      trendModalBody.innerHTML = `<p class="modal-loading">Unable to load trend details right now.</p>`;
    }
  }

  async function markAlertRead(alertId) {
    try {
      const response = await fetch(`/api/alerts/${alertId}/read`, {
        method: "POST",
        headers: { Accept: "application/json" },
      });
      if (!response.ok) throw new Error(`Failed to mark alert as read (${response.status})`);
      await response.json();
      await loadAlerts();
    } catch (error) {
      console.error(error);
      setStatus("Could not mark alert as read. Please try again.");
    }
  }

  async function openContentIdeaModal(trend) {
    if (!modal || !modalBody || !modalTitle) return;
    modalTitle.textContent = `${trend.title || trend.name || "Trend"} content idea`;
    modalBody.innerHTML = `<p class="modal-loading">Loading content idea...</p>`;
    modal.setAttribute("aria-hidden", "false");
    modal.classList.add("is-open");

    try {
      let contentIdea = trend.content_idea;
      if (!contentIdea && trend.id) {
        const response = await fetch(`/api/trend/${trend.id}/content-idea`, {
          headers: { Accept: "application/json" },
        });
        if (response.ok) {
          contentIdea = await response.json();
        }
      }
      modalBody.innerHTML = renderContentIdea(contentIdea || trend);
    } catch (error) {
      console.error(error);
      modalBody.innerHTML = `<p class="modal-loading">Unable to load the content idea right now.</p>`;
    }
  }

  function closeModal(modalElement) {
    if (!modalElement) return;
    modalElement.setAttribute("aria-hidden", "true");
    modalElement.classList.remove("is-open");
  }

  function renderAiSummary(detail) {
    return `
      <div class="ai-summary-grid">
        <div class="ai-summary-item">
          <span>Trend Summary</span>
          <p>${escapeHtml(detail.trend_summary || detail.ai_summary || "No AI summary available yet.")}</p>
        </div>
        <div class="ai-summary-item">
          <span>Why It Is Trending</span>
          <p>${escapeHtml(detail.why_it_is_trending || detail.why_trending || "No explanation available yet.")}</p>
        </div>
        <div class="ai-summary-item">
          <span>Virality Explanation</span>
          <p>${escapeHtml(detail.virality_explanation || "No virality explanation available yet.")}</p>
        </div>
        <div class="ai-summary-item">
          <span>Audience Interest</span>
          <p>${escapeHtml(detail.audience_interest || "No audience insight available yet.")}</p>
        </div>
        <div class="ai-summary-item">
          <span>Future Prediction</span>
          <p>${escapeHtml(detail.future_prediction || "No prediction available yet.")}</p>
        </div>
      </div>
    `;
  }

  function renderForecastAnalysis(detail) {
    const similarTrends = Array.isArray(detail.similar_trends) ? detail.similar_trends : [];
    const forecast = detail.forecast || detail;
    const probability = currentViralityProbability(forecast);
    const confidence = currentForecastConfidence(forecast);
    const opportunity = currentOpportunityScore(forecast);
    const risk = currentRiskScore(forecast);
    return `
      <div class="forecast-summary-grid">
        <div class="forecast-summary-item">
          <span>Prediction Label</span>
          <p><span class="trend-badge prediction-${badgeKey(forecast.prediction_label || "PENDING")}">${escapeHtml(forecast.prediction_label || "Pending")}</span></p>
        </div>
        <div class="forecast-summary-item">
          <span>Growth Stage</span>
          <p>${escapeHtml(forecast.growth_stage || "growing")}</p>
        </div>
        <div class="forecast-summary-item">
          <span>Virality Probability</span>
          <p>${escapeHtml(probability.toFixed(1))}%</p>
        </div>
        <div class="forecast-summary-item">
          <span>Forecast Confidence</span>
          <p>${escapeHtml(confidence.toFixed(1))}%</p>
        </div>
        <div class="forecast-summary-item">
          <span>Opportunity Score</span>
          <p>${escapeHtml(opportunity.toFixed(1))}%</p>
        </div>
        <div class="forecast-summary-item">
          <span>Risk Score</span>
          <p>${escapeHtml(risk.toFixed(1))}%</p>
        </div>
      </div>
      <div class="forecast-bar">
        <div class="forecast-bar__fill" style="width: ${Math.max(0, Math.min(100, probability))}%"></div>
      </div>
      <section class="forecast-section">
        <h4>Forecast Explanation</h4>
        <p>${escapeHtml(forecast.forecast_explanation || "No forecast explanation available.")}</p>
      </section>
      <section class="forecast-section">
        <h4>Why It May Grow</h4>
        <p>${escapeHtml(forecast.why_the_trend_may_grow || "No growth reason available.")}</p>
      </section>
      <section class="forecast-section">
        <h4>Audience Behavior</h4>
        <p>${escapeHtml(forecast.possible_audience_behavior || "No audience behavior available.")}</p>
      </section>
      <section class="forecast-section">
        <h4>Business Opportunity</h4>
        <p>${escapeHtml(forecast.business_opportunity_analysis || "No business opportunity available.")}</p>
      </section>
      <section class="forecast-section">
        <h4>Recommended Creator Actions</h4>
        <ul class="forecast-list">
          ${
            Array.isArray(forecast.recommended_creator_actions) && forecast.recommended_creator_actions.length
              ? forecast.recommended_creator_actions.map((item) => `<li>${escapeHtml(item)}</li>`).join("")
              : `<li>No actions available.</li>`
          }
        </ul>
      </section>
      <section class="forecast-section">
        <h4>Similar Historical Trends</h4>
        ${
          similarTrends.length
            ? `<div class="forecast-similar-grid">${similarTrends.map(renderForecastSimilarTrend).join("")}</div>`
            : `<p class="modal-loading">No strong historical match was found. The forecast used broader trend signals instead.</p>`
        }
      </section>
    `;
  }

  function renderForecastSimilarTrend(trend) {
    return `
      <article class="forecast-similar-card">
        <div class="forecast-similar-card__top">
          <strong>${escapeHtml(trend.title || "Untitled trend")}</strong>
          <span class="trend-badge source-${badgeKey(trend.source_label || trend.platform)}">${escapeHtml(trend.source_label || trend.platform || "UNKNOWN")}</span>
        </div>
        <p>${escapeHtml(trend.summary || trend.description || "No summary available.")}</p>
        <div class="forecast-similar-card__meta">
          <span>Virality ${escapeHtml(trend.virality_score ?? 0)}</span>
          <span>${escapeHtml(trend.prediction_label || trend.virality_label || "Pending")}</span>
          <span>Match ${escapeHtml(trend.similarity_score ?? 0)}%</span>
        </div>
      </article>
    `;
  }

  async function openAiSummaryModal(trend) {
    if (!aiModal || !aiModalBody || !aiModalTitle) return;
    aiModalTitle.textContent = `${trend.title || trend.name || "Trend"} AI summary`;
    aiModalBody.innerHTML = `<p class="modal-loading">Generating AI summary...</p>`;
    aiModal.setAttribute("aria-hidden", "false");
    aiModal.classList.add("is-open");

    try {
      if (trend.ai_summary || trend.trend_summary || trend.why_it_is_trending) {
        aiModalBody.innerHTML = renderAiSummary(trend);
        return;
      }

      const params = new URLSearchParams({
        title: trend.title || trend.name || "",
        description: trend.description || trend.summary || "",
      });
      const response = await fetch(`/api/analyze-trend?${params.toString()}`, {
        headers: { Accept: "application/json" },
      });
      if (!response.ok) throw new Error(`Failed to analyze trend (${response.status})`);
      const data = await response.json();
      aiModalBody.innerHTML = renderAiSummary(data.item || {});
    } catch (error) {
      console.error(error);
      aiModalBody.innerHTML = `<p class="modal-loading">Unable to generate the AI summary right now.</p>`;
    }
  }

  async function openForecastModal(trend) {
    if (!forecastModal || !forecastModalBody || !forecastModalTitle) return;
    state.ws.currentForecastTrendId = trend.id || null;
    forecastModalTitle.textContent = `${trend.title || trend.name || "Trend"} forecast`;
    forecastModalBody.innerHTML = `<p class="modal-loading">Generating forecast...</p>`;
    forecastModal.setAttribute("aria-hidden", "false");
    forecastModal.classList.add("is-open");

    try {
      if (trend.prediction_label || trend.virality_probability || trend.forecast_confidence) {
        state.ws.currentForecastPayload = {
          current_trend: trend.title || trend.name || "Trend",
          forecast: trend,
          similar_trends: trend.similar_trends || [],
        };
        forecastModalBody.innerHTML = renderForecastAnalysis({
          forecast: trend,
          similar_trends: trend.similar_trends || [],
        });
        renderIntelligencePanel();
        return;
      }

      const params = new URLSearchParams({
        title: trend.title || trend.name || "",
        description: trend.description || trend.summary || "",
      });
      const response = await fetch(`/api/forecast-trend?${params.toString()}`, {
        headers: { Accept: "application/json" },
      });
      if (!response.ok) throw new Error(`Failed to forecast trend (${response.status})`);
      const data = await response.json();
      state.ws.currentForecastPayload = data;
      forecastModalBody.innerHTML = renderForecastAnalysis(data);
      renderIntelligencePanel();
    } catch (error) {
      console.error(error);
      forecastModalBody.innerHTML = `<p class="modal-loading">Unable to generate the forecast right now.</p>`;
    }
  }

  function renderRagAnalysis(payload) {
    const similarTrends = Array.isArray(payload.similar_trends) ? payload.similar_trends : [];
    const rag = payload.rag_analysis || {};
    return `
      <div class="rag-summary-grid">
        <div class="rag-summary-item">
          <span>Current Trend</span>
          <p>${escapeHtml(payload.current_trend || "n/a")}</p>
        </div>
        <div class="rag-summary-item">
          <span>Summary</span>
          <p>${escapeHtml(rag.summary || "No summary available.")}</p>
        </div>
        <div class="rag-summary-item">
          <span>Historical Comparison</span>
          <p>${escapeHtml(rag.historical_comparison || "No comparison available.")}</p>
        </div>
        <div class="rag-summary-item">
          <span>Virality Prediction</span>
          <p>${escapeHtml(rag.virality_prediction || "No prediction available.")}</p>
        </div>
        <div class="rag-summary-item">
          <span>Risk Level</span>
          <p>${escapeHtml(rag.risk_level || "Medium")}</p>
        </div>
        <div class="rag-summary-item">
          <span>Final Recommendation</span>
          <p>${escapeHtml(rag.final_recommendation || "No recommendation available.")}</p>
        </div>
      </div>
      <section class="rag-section">
        <h4>Recommended Content Opportunities</h4>
        <ul class="rag-list">
          ${
            Array.isArray(rag.content_opportunities) && rag.content_opportunities.length
              ? rag.content_opportunities.map((item) => `<li>${escapeHtml(item)}</li>`).join("")
              : `<li>No content opportunities generated.</li>`
          }
        </ul>
      </section>
      <section class="rag-section">
        <h4>Similar Past Trends</h4>
        ${
          similarTrends.length
            ? `<div class="rag-similar-grid">${similarTrends.map(renderRagSimilarTrend).join("")}</div>`
            : `<p class="modal-loading">No close historical match was found, so the model broadened the context window.</p>`
        }
      </section>
    `;
  }

  function renderRagSimilarTrend(trend) {
    return `
      <article class="rag-similar-card">
        <div class="rag-similar-card__top">
          <strong>${escapeHtml(trend.title || "Untitled trend")}</strong>
          <span class="trend-badge source-${badgeKey(trend.source_label || trend.platform)}">${escapeHtml(trend.source_label || trend.platform || "UNKNOWN")}</span>
        </div>
        <p>${escapeHtml(trend.summary || trend.description || "No summary available.")}</p>
        <div class="rag-similar-card__meta">
          <span>Virality ${escapeHtml(trend.virality_score ?? 0)}</span>
          <span>${escapeHtml(trend.virality_label || "Low Viral")}</span>
          <span>Match ${escapeHtml(trend.similarity_score ?? 0)}%</span>
          <span>${trend.has_alert ? "Alerted" : "No alert"}</span>
        </div>
      </article>
    `;
  }

  async function openRagModal(trend) {
    if (!ragModal || !ragModalBody || !ragModalTitle) return;
    state.ws.currentRagTrendId = trend.id || null;
    ragModalTitle.textContent = `${trend.title || trend.name || "Trend"} historical intelligence`;
    ragModalBody.innerHTML = `<p class="modal-loading">Running RAG analysis...</p>`;
    ragModal.setAttribute("aria-hidden", "false");
    ragModal.classList.add("is-open");

    try {
      const params = new URLSearchParams({
        title: trend.title || trend.name || "",
        description: trend.description || trend.summary || "",
      });
      const response = await fetch(`/api/rag-analyze-trend?${params.toString()}`, {
        headers: { Accept: "application/json" },
      });
      if (!response.ok) throw new Error(`Failed to run RAG analysis (${response.status})`);
      const data = await response.json();
      state.ws.currentRagPayload = data;
      ragModalBody.innerHTML = renderRagAnalysis(data);
    } catch (error) {
      console.error(error);
      ragModalBody.innerHTML = `<p class="modal-loading">Unable to run RAG analysis right now.</p>`;
    }
  }

  async function runAction(url, message) {
    setLoading(true);
    setStatus(message);
    try {
      const response = await fetch(url, { headers: { Accept: "application/json" } });
      if (!response.ok) throw new Error(`Request failed (${response.status})`);
      const data = await response.json();
      if (url === "/api/fetch-live-trends") {
        const count = Number(data.count || 0);
        showToast(count > 0 ? `${count} live trends fetched successfully.` : "No live trends were fetched.");
      }
      if (url === "/api/fetch-news-trends" || url === "/api/fetch-youtube-trends") {
        const count = Number(data.count || 0);
        showToast(count > 0 ? `${count} ${data.source || "live"} trends fetched.` : "No trends were fetched.");
      }
      if (url === "/api/forecast-live-trends") {
        const count = Number(data.count || 0);
        showToast(count > 0 ? `${count} trends forecasted successfully.` : "No forecasts were generated.");
        if (Array.isArray(data.items) && data.items.length) {
          state.ws.currentForecastPayload = {
            current_trend: data.items[0]?.title || data.items[0]?.name || "Trend",
            forecast: getBestForecastTrend(data.items) || data.items[0],
            similar_trends: [],
          };
          renderIntelligencePanel();
        }
      }
      if (url === "/api/generate-alerts") {
        const count = Number(data.count || 0);
        showToast(count > 0 ? `${count} new high viral trend alerts generated.` : "No new alerts were generated.");
      }
      await loadDashboard();
      await loadAlerts();
    } catch (error) {
      console.error(error);
      setStatus("The refresh request failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  function bindFilterEvents() {
    if (searchInput) {
      searchInput.addEventListener("input", () => {
        state.filters.search = searchInput.value;
        applyFilters();
      });
    }

    if (platformFilter) {
      platformFilter.addEventListener("change", () => {
        state.filters.platform = platformFilter.value;
        applyFilters();
      });
    }

    if (viralityFilter) {
      viralityFilter.addEventListener("change", () => {
        state.filters.virality = viralityFilter.value;
        applyFilters();
      });
    }

    if (sentimentFilter) {
      sentimentFilter.addEventListener("change", () => {
        state.filters.sentiment = sentimentFilter.value;
        applyFilters();
      });
    }

    if (sortFilter) {
      sortFilter.addEventListener("change", () => {
        state.filters.sort = sortFilter.value;
        applyFilters();
      });
    }
  }

  if (fetchRedditBtn) {
    fetchRedditBtn.addEventListener("click", () => runAction("/api/fetch-reddit-trends", "Fetching Reddit trends..."));
  }

  if (fetchGoogleBtn) {
    fetchGoogleBtn.addEventListener("click", () => runAction("/api/fetch-google-trends", "Fetching Google Trends..."));
  }

  if (fetchLiveBtn) {
    fetchLiveBtn.addEventListener("click", () => runAction("/api/fetch-live-trends", "Fetching live trends from News and YouTube..."));
  }

  if (analyzeTrendsBtn) {
    analyzeTrendsBtn.addEventListener("click", () => runAction("/api/analyze-trends", "Analyzing stored trends..."));
  }

  if (ragAnalyzeBtn) {
    ragAnalyzeBtn.addEventListener("click", () => {
      const targetTrend = state.filteredTrends[0] || state.allTrends[0];
      if (!targetTrend) {
        setStatus("Load or fetch trends first to run RAG analysis.");
        showToast("Load trends first before running RAG analysis.");
        return;
      }
      openRagModal(targetTrend);
    });
  }

  if (forecastTrendsBtn) {
    forecastTrendsBtn.addEventListener("click", () => runAction("/api/forecast-live-trends", "Forecasting active trends..."));
  }

  if (generateContentBtn) {
    generateContentBtn.addEventListener("click", () => runAction("/api/generate-content-ideas", "Generating content ideas..."));
  }

  if (generateAlertsBtn) {
    generateAlertsBtn.addEventListener("click", () => runAction("/api/generate-alerts", "Generating alerts..."));
  }

  if (refreshBtn) {
    refreshBtn.addEventListener("click", loadDashboard);
  }

  if (modal) {
    modal.addEventListener("click", (event) => {
      if (event.target && event.target.matches("[data-close-modal]")) {
        closeModal(modal);
      }
    });
  }

  if (trendModal) {
    trendModal.addEventListener("click", (event) => {
      if (event.target && event.target.matches("[data-close-trend-modal]")) {
        closeModal(trendModal);
      }
    });
  }

  if (aiModal) {
    aiModal.addEventListener("click", (event) => {
      if (event.target && event.target.matches("[data-close-ai-modal]")) {
        closeModal(aiModal);
      }
    });
  }

  if (ragModal) {
    ragModal.addEventListener("click", (event) => {
      if (event.target && event.target.matches("[data-close-rag-modal]")) {
        closeModal(ragModal);
      }
    });
  }

  if (forecastModal) {
    forecastModal.addEventListener("click", (event) => {
      if (event.target && event.target.matches("[data-close-forecast-modal]")) {
        closeModal(forecastModal);
      }
    });
  }

  if (soundToggle) {
    state.ws.soundEnabled = soundToggle.checked;
    soundToggle.addEventListener("change", () => {
      state.ws.soundEnabled = soundToggle.checked;
      addActivity(state.ws.soundEnabled ? "Sound alerts enabled." : "Sound alerts disabled.", "info");
    });
  }

  setLiveStatus(false, "Connecting to live dashboard...");
  setTickerText("Waiting for live updates...");
  updateLiveMeta();
  connectWebSocket();

  window.addEventListener("beforeunload", () => {
    if (state.ws.reconnectTimer) {
      window.clearTimeout(state.ws.reconnectTimer);
    }
    if (state.ws.refreshTimer) {
      window.clearTimeout(state.ws.refreshTimer);
    }
    if (state.ws.socket) {
      try {
        state.ws.socket.close();
      } catch (error) {
        console.warn("Failed to close websocket cleanly", error);
      }
    }
  });

  bindFilterEvents();
  loadDashboard();
  loadAlerts();
}

  function renderTrendDetails(detail) {
    const contentIdea = detail.content_idea;
    return `
    <div class="trend-detail-grid">
      <div class="trend-detail-item">
        <span>Title</span>
        <p>${escapeHtml(detail.title || detail.name || "Untitled trend")}</p>
      </div>
      <div class="trend-detail-item">
        <span>Platform</span>
        <p>${escapeHtml(detail.platform || "unknown")}</p>
      </div>
      <div class="trend-detail-item">
        <span>Source Label</span>
        <p>${escapeHtml(detail.source_label || detail.platform || "unknown")}</p>
      </div>
      <div class="trend-detail-item">
        <span>Subreddit</span>
        <p>${escapeHtml(detail.subreddit || "n/a")}</p>
      </div>
      <div class="trend-detail-item">
        <span>Source Type</span>
        <p>${escapeHtml(detail.source_type || "n/a")}</p>
      </div>
      <div class="trend-detail-item">
        <span>URL</span>
        <p>${escapeHtml(detail.url || "n/a")}</p>
      </div>
      <div class="trend-detail-item">
        <span>Description</span>
        <p>${escapeHtml(detail.description || "n/a")}</p>
      </div>
      <div class="trend-detail-item">
        <span>Upvotes</span>
        <p>${escapeHtml(detail.upvotes ?? 0)}</p>
      </div>
      <div class="trend-detail-item">
        <span>Comments</span>
        <p>${escapeHtml(detail.comments ?? 0)}</p>
      </div>
      <div class="trend-detail-item">
        <span>Channel Name</span>
        <p>${escapeHtml(detail.channel_name || "n/a")}</p>
      </div>
      <div class="trend-detail-item">
        <span>View Count</span>
        <p>${escapeHtml(detail.view_count ?? 0)}</p>
      </div>
      <div class="trend-detail-item">
        <span>Trend Score</span>
        <p>${escapeHtml(detail.trend_score ?? detail.search_interest ?? 0)}</p>
      </div>
      <div class="trend-detail-item">
        <span>Sentiment</span>
        <p>${escapeHtml(detail.sentiment_label || "Neutral")}</p>
      </div>
      <div class="trend-detail-item">
        <span>Positive Score</span>
        <p>${escapeHtml(detail.positive_score ?? 0)}</p>
      </div>
      <div class="trend-detail-item">
        <span>Negative Score</span>
        <p>${escapeHtml(detail.negative_score ?? 0)}</p>
      </div>
      <div class="trend-detail-item">
        <span>Neutral Score</span>
        <p>${escapeHtml(detail.neutral_score ?? 0)}</p>
      </div>
      <div class="trend-detail-item">
        <span>Compound Score</span>
        <p>${escapeHtml(detail.compound_score ?? 0)}</p>
      </div>
      <div class="trend-detail-item">
        <span>Virality Score</span>
        <p>${escapeHtml(detail.virality_score ?? 0)}</p>
      </div>
      <div class="trend-detail-item">
        <span>Virality Label</span>
        <p>${escapeHtml(detail.virality_label || "Low Viral")}</p>
      </div>
      <div class="trend-detail-item">
        <span>Prediction Label</span>
        <p>${escapeHtml(detail.prediction_label || "Pending")}</p>
      </div>
      <div class="trend-detail-item">
        <span>Growth Stage</span>
        <p>${escapeHtml(detail.growth_stage || "growing")}</p>
      </div>
      <div class="trend-detail-item">
        <span>Virality Probability</span>
        <p>${escapeHtml(detail.virality_probability ?? 0)}</p>
      </div>
      <div class="trend-detail-item">
        <span>Forecast Confidence</span>
        <p>${escapeHtml(detail.forecast_confidence ?? 0)}</p>
      </div>
      <div class="trend-detail-item">
        <span>Opportunity Score</span>
        <p>${escapeHtml(detail.opportunity_score ?? 0)}</p>
      </div>
      <div class="trend-detail-item">
        <span>Risk Score</span>
        <p>${escapeHtml(detail.risk_score ?? 0)}</p>
      </div>
      <div class="trend-detail-item">
        <span>AI Summary</span>
        <p>${escapeHtml(detail.ai_summary || detail.trend_summary || "n/a")}</p>
      </div>
      <div class="trend-detail-item">
        <span>Why Trending</span>
        <p>${escapeHtml(detail.why_trending || detail.why_it_is_trending || "n/a")}</p>
      </div>
      <div class="trend-detail-item">
        <span>Audience Interest</span>
        <p>${escapeHtml(detail.audience_interest || "n/a")}</p>
      </div>
      <div class="trend-detail-item">
        <span>Future Prediction</span>
        <p>${escapeHtml(detail.future_prediction || "n/a")}</p>
      </div>
      <div class="trend-detail-item">
        <span>Fetched At</span>
        <p>${escapeHtml(detail.fetched_at || "n/a")}</p>
      </div>
      <div class="trend-detail-item">
        <span>Analyzed At</span>
        <p>${escapeHtml(detail.analyzed_at || "n/a")}</p>
      </div>
    </div>
    ${
      contentIdea
        ? `<div class="trend-detail-content-idea">${renderContentIdea(contentIdea)}</div>`
        : ""
    }
  `;
}

function renderContentIdea(contentIdea) {
  const hashtags = Array.isArray(contentIdea.hashtags) ? contentIdea.hashtags.join(" ") : "";
  return `
    <div class="content-idea-grid">
      <div class="content-idea-item">
        <span>Hook</span>
        <p>${escapeHtml(contentIdea.hook || "No hook available yet.")}</p>
      </div>
      <div class="content-idea-item">
        <span>Reel Idea</span>
        <p>${escapeHtml(contentIdea.reel_idea || "No reel idea available yet.")}</p>
      </div>
      <div class="content-idea-item">
        <span>YouTube Shorts Idea</span>
        <p>${escapeHtml(contentIdea.youtube_shorts_idea || "No Shorts idea available yet.")}</p>
      </div>
      <div class="content-idea-item">
        <span>Caption</span>
        <p>${escapeHtml(contentIdea.caption || "No caption available yet.")}</p>
      </div>
      <div class="content-idea-item">
        <span>Hashtags</span>
        <p>${escapeHtml(hashtags || "No hashtags available yet.")}</p>
      </div>
      <div class="content-idea-item">
        <span>Content Angle</span>
        <p>${escapeHtml(contentIdea.content_angle || "No angle available yet.")}</p>
      </div>
    </div>
  `;
}




