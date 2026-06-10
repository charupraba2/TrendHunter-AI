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

document.addEventListener("click", async (event) => {
  const button = event.target && typeof event.target.closest === "function" ? event.target.closest("#trackPostBtn") : null;
  if (!button) return;
  const lastHandled = Number(window.__trackPostClickStamp || 0);
  if (Date.now() - lastHandled < 500) return;
  event.preventDefault();
  console.log("Track Performance clicked via delegation");
  if (typeof window.trackPublishedPost === "function") {
    await window.trackPublishedPost();
  }
});

function setupDashboard(root) {
  window.latestAnalysis = window.latestAnalysis || null;
  window.latestCompetitorAnalysis = window.latestCompetitorAnalysis || null;
  window.latestStrategy = window.latestStrategy || null;
  window.generatedLinkedInPost = window.generatedLinkedInPost || "";
  window.selectedRegion = window.selectedRegion || "India";
  window.visualAnalytics = window.visualAnalytics || {
    radar: null,
    bar: null,
    comparison: null,
    forecast: null,
    platformRadar: null,
    platformComparison: null,
    engagementGrowth: null,
    postPerformanceGrowth: null,
    postPerformanceLifecycle: null,
  };
  const apiUrl = root.dataset.trendsApi || "/api/trends";
  const grid = document.getElementById("trend-grid");
  const emptyState = document.getElementById("dashboard-empty");
  const status = document.getElementById("dashboard-status");
  const alertsList = document.getElementById("alerts-list");
  const alertsEmpty = document.getElementById("alerts-empty");
  const dashboardTabs = Array.from(root.querySelectorAll("[data-dashboard-tab]"));
  const dashboardPanels = Array.from(root.querySelectorAll("[data-tab-panel]"));
  const dashboardWorkspaceSearch = document.getElementById("dashboard-workspace-search");
  const dashboardNotificationsBtn = document.getElementById("dashboard-notifications-btn");
  const dashboardProfileBtn = document.getElementById("dashboard-profile-btn");
  const sidebarAssistantBtn = document.getElementById("sidebar-assistant-btn");
  const sidebarSettingsBtn = document.getElementById("sidebar-settings-btn");
  const openAssistantSidebarBtn = document.getElementById("openAssistantSidebarBtn");
  const fetchRedditBtn = document.getElementById("fetch-reddit-btn");
  const fetchGoogleBtn = document.getElementById("fetch-google-btn");
  const fetchLiveBtn = document.getElementById("fetch-live-btn");
  const analyzeTrendsBtn = document.getElementById("analyze-trends-btn");
  const ragAnalyzeBtn = document.getElementById("rag-analyze-btn");
  const forecastTrendsBtn = document.getElementById("forecast-trends-btn");
  const generateContentBtn = document.getElementById("generate-content-btn");
  const generateAlertsBtn = document.getElementById("generate-alerts-btn");
  const refreshCurrentTrendsBtn = document.getElementById("refresh-current-trends-btn");
  const postLinkedInBtn = document.getElementById("post-linkedin-btn");
  const exportPdfBtn = document.getElementById("export-pdf-btn");
  const refreshBtn = document.getElementById("refresh-dashboard-btn");
  const dashboardLoader = document.getElementById("dashboard-loader");
  const statusText = document.querySelector("#dashboard-status .dashboard-status__text");
  const searchInput = document.getElementById("trend-search");
  if (dashboardWorkspaceSearch && searchInput) {
    dashboardWorkspaceSearch.value = searchInput.value || "";
    dashboardWorkspaceSearch.addEventListener("input", (event) => {
      searchInput.value = event.target.value;
      searchInput.dispatchEvent(new Event("input", { bubbles: true }));
    });
  }
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
  const linkedinPostModal = document.getElementById("linkedin-modal");
  const linkedinPostModalBody = document.getElementById("linkedin-modal-body");
  const linkedinPostModalTitle = document.getElementById("linkedin-modal-title");
  const creatorForm = document.getElementById("creator-form");
  const creatorAnalyzeBtn = document.getElementById("creator-analyze-btn");
  const creatorDemoBtn = document.getElementById("creator-demo-btn");
  const generateLinkedInBtn = document.getElementById("generate-linkedin-btn");
  const clearAnalysisBtn = document.getElementById("clearAnalysisBtn");
  const creatorPlatform = document.getElementById("creator-platform");
  const creatorContentType = document.getElementById("creator-content-type");
  const creatorAudience = document.getElementById("creator-audience");
  const creatorTitle = document.getElementById("creator-title");
  const creatorCaption = document.getElementById("creator-caption");
  const creatorHashtags = document.getElementById("creator-hashtags");
  const thumbnailUpload = document.getElementById("thumbnail-upload");
  const thumbnailPreviewImage = document.getElementById("thumbnail-preview-image");
  const thumbnailUploadPlaceholder = document.getElementById("thumbnail-upload-placeholder");
  const thumbnailUploadStatus = document.getElementById("thumbnail-upload-status");
  const analysisResult = document.getElementById("analysisResult");
  const creatorResultsEmpty = document.getElementById("analysisEmpty") || document.getElementById("creator-results-empty");
  const creatorResultsContent = document.getElementById("analysisContent") || document.getElementById("creator-results-content") || analysisResult;
  const thumbnailAnalysis = document.getElementById("thumbnail-analysis");
  const thumbnailAnalysisContent = document.getElementById("thumbnail-analysis-content");
  const viralityRadarChartCanvas = document.getElementById("viralityRadarChart");
  const viralityBarChartCanvas = document.getElementById("viralityBarChart");
  const viralityComparisonChartCanvas = document.getElementById("viralityComparisonChart");
  const engagementForecastChartCanvas = document.getElementById("engagementForecastChart");
  const forecastLikesEl = document.getElementById("forecastLikes");
  const forecastCommentsEl = document.getElementById("forecastComments");
  const forecastSharesEl = document.getElementById("forecastShares");
  const forecastReachEl = document.getElementById("forecastReach");
  const forecastGrowthTrendEl = document.getElementById("forecastGrowthTrend");
  const forecastConfidenceEl = document.getElementById("forecastConfidence");
  const forecastPeakTimeEl = document.getElementById("forecastPeakTime");
  const engagementGrowthPredictionChartCanvas = document.getElementById("engagementGrowthPredictionChart");
  const performanceForm = document.getElementById("performance-form") || document.getElementById("postTrackingForm");
  const postTrackingForm = document.getElementById("postTrackingForm") || performanceForm;
  const performanceUrlInput = document.getElementById("publishedPostUrl");
  const manualLikesInput = document.getElementById("manualLikes");
  const manualCommentsInput = document.getElementById("manualComments");
  const manualSharesInput = document.getElementById("manualShares");
  const manualImpressionsInput = document.getElementById("manualImpressions");
  const postAgeInput = document.getElementById("postAge");
  const performanceTrackBtn = document.getElementById("track-performance-btn") || document.getElementById("trackPostBtn");
  const trackPostBtn = document.getElementById("trackPostBtn") || performanceTrackBtn;
  const performanceEmpty = document.getElementById("performance-empty");
  const performanceContent = document.getElementById("performance-results-content");
  const postPerformanceResult = document.getElementById("postPerformanceResult");
  const performancePlatformBadge = document.getElementById("performance-platform-badge");
  const performanceRegionBadge = document.getElementById("performance-region-badge");
  const performanceSummaryTitle = document.getElementById("performance-summary-title");
  const performanceSummaryText = document.getElementById("performance-summary-text");
  const performanceLifecycleStage = document.getElementById("performanceLifecycleStage");
  const performanceMomentumBadge = document.getElementById("performanceMomentumBadge");
  const performanceTrendRelevanceBadge = document.getElementById("performanceTrendRelevanceBadge");
  const performanceLikesEl = document.getElementById("performanceLikes");
  const performanceCommentsEl = document.getElementById("performanceComments");
  const performanceSharesEl = document.getElementById("performanceShares");
  const performanceReachEl = document.getElementById("performanceReach");
  const performanceImpressionsEl = document.getElementById("performanceImpressions");
  const performanceGrowthEl = document.getElementById("performanceEngagementGrowth");
  const performanceMomentumEl = document.getElementById("performanceViralityMomentum");
  const performanceMomentumBar = document.getElementById("performanceViralityMomentumBar");
  const performanceGrowthSpeedEl = document.getElementById("performanceGrowthSpeed");
  const performanceGrowthSpeedBar = document.getElementById("performanceGrowthSpeedBar");
  const performanceTrendStrengthEl = document.getElementById("performanceTrendStrength");
  const performanceTrendStrengthBar = document.getElementById("performanceTrendStrengthBar");
  const performanceEngagementVelocityEl = document.getElementById("performanceEngagementVelocity");
  const performanceEngagementVelocityBar = document.getElementById("performanceEngagementVelocityBar");
  const performanceExpectedReachEl = document.getElementById("performanceExpectedReach");
  const performanceExpectedImpressionsEl = document.getElementById("performanceExpectedImpressions");
  const performancePeakTimeEl = document.getElementById("performancePeakTime");
  const performanceDecayEl = document.getElementById("performanceDecay");
  const performanceRecommendationsEl = document.getElementById("performanceRecommendations");
  const postPerformanceGrowthChartCanvas = document.getElementById("postPerformanceGrowthChart");
  const postPerformanceLifecycleChartCanvas = document.getElementById("postPerformanceLifecycleChart");
  const forecastModeSelect = document.getElementById("forecast-mode");
  const forecastStudioTitle = document.getElementById("forecastStudioTitle");
  const forecastStudioSubtitle = document.getElementById("forecastStudioSubtitle");
  const forecastModeBadge = document.getElementById("forecast-mode-badge");
  const forecastEngagementTitle = document.getElementById("forecastEngagementTitle");
  const forecastProbabilityTitle = document.getElementById("forecastProbabilityTitle");
  const platformIntelligenceSection = document.getElementById("platform-intelligence");
  const platformAlgorithmRadarChartCanvas = document.getElementById("platformAlgorithmRadarChart");
  const platformComparisonChartCanvas = document.getElementById("platformComparisonChart");
  const platformAlgorithmCards = document.getElementById("platformAlgorithmCards");
  const platformAlgorithmRecommendations = document.getElementById("platformAlgorithmRecommendations");
  const platformComparisonMode = document.getElementById("platformComparisonMode");
  const competitorForm = document.getElementById("competitor-form");
  const competitorName = document.getElementById("competitorName") || document.getElementById("competitor-name");
  const competitorTopic = document.getElementById("competitor-topic");
  const competitorPlatform = document.getElementById("competitor-platform");
  const competitorAnalyzeBtn = document.getElementById("competitorBtn") || document.getElementById("competitor-analyze-btn");
  const competitorResultsEmpty = document.getElementById("competitor-results-empty");
  const competitorResultsContent = document.getElementById("competitorResult") || document.getElementById("competitor-results-content");
  const strategyPanel = document.getElementById("strategy-panel");
  const strategyBtn = document.getElementById("strategyBtn");
  const strategyStatus = document.getElementById("strategyStatus");
  const strategyEmpty = document.getElementById("strategyEmpty");
  const strategyLoader = document.getElementById("strategyLoader");
  const strategyContent = document.getElementById("strategyContent");
  const aiBtn = document.getElementById("aiAssistantBtn");
  const aiPanel = document.getElementById("aiAssistantPanel");
  const closeBtn = document.getElementById("closeAssistantBtn");
  const aiChatInput = document.getElementById("aiChatInput");
  const aiChatSendBtn = document.getElementById("aiChatSendBtn");
  const aiChatMessages = document.getElementById("aiChatMessages");
  const assistantFab = aiBtn;
  const assistantSidebar = aiPanel;
  const assistantOverlay = null;
  const assistantClose = closeBtn;
  const assistantForm = null;
  const assistantInput = aiChatInput;
  const assistantSend = aiChatSendBtn;
  const assistantMessages = aiChatMessages;
  console.log("AI Assistant elements:", aiBtn, aiPanel);
  const workspaceRefreshBtn = document.getElementById("workspace-refresh-btn");
  const workspaceAnalyses = document.getElementById("workspace-analyses");
  const workspaceLinkedInPosts = document.getElementById("workspace-linkedin-posts");
  const workspaceReports = document.getElementById("workspace-reports");
  const currentTrendsList = document.getElementById("current-trends-list");
  const currentTrendsRefreshBtn = document.getElementById("current-trends-refresh-btn");
  const trendRegion = document.getElementById("trendRegion");
  const trendRegionSummary = document.getElementById("trendRegionSummary");
  const trendMatchScore = document.getElementById("trend-match-score");
  const trendMatchNote = document.getElementById("trend-match-note");
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
    currentTrends: [],
    filters: {
      search: "",
      platform: "all",
      virality: "all",
      sentiment: "all",
      sort: "latest",
    },
    activeTab: "overview",
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
      currentCreatorPayload: null,
      currentLinkedInPost: null,
      currentStrategyPayload: null,
      currentTrendSnapshot: null,
      currentThumbnailResult: null,
      currentThumbnailPreviewUrl: null,
      currentAssistantTyping: null,
      currentPostPerformance: null,
    },
  };

  state.forecastMode = forecastModeSelect?.value || state.forecastMode || "Global";
  syncForecastStudioUI(state.forecastMode);

  function setStatus(message) {
    if (statusText) {
      statusText.textContent = message;
    } else if (status) {
      status.textContent = message;
    }
  }

  function setDashboardTab(tabName) {
    const nextTab = tabName || "overview";
    state.activeTab = nextTab;
    dashboardTabs.forEach((button) => {
      const isActive = button.dataset.dashboardTab === nextTab;
      button.classList.toggle("is-active", isActive);
      button.setAttribute("aria-selected", isActive ? "true" : "false");
    });
    dashboardPanels.forEach((panel) => {
      const isActive = panel.dataset.tabPanel === nextTab;
      panel.classList.toggle("is-active", isActive);
      panel.hidden = !isActive;
    });
    window.requestAnimationFrame(() => {
      window.dispatchEvent(new Event("resize"));
    });
  }

  function setLoading(isLoading) {
    state.loading = isLoading;
    [fetchRedditBtn, fetchGoogleBtn, fetchLiveBtn, refreshCurrentTrendsBtn, analyzeTrendsBtn, ragAnalyzeBtn, forecastTrendsBtn, generateContentBtn, generateAlertsBtn, refreshBtn, creatorAnalyzeBtn, creatorDemoBtn, generateLinkedInBtn, postLinkedInBtn, exportPdfBtn, competitorAnalyzeBtn, currentTrendsRefreshBtn, workspaceRefreshBtn, strategyBtn, clearAnalysisBtn, performanceTrackBtn].forEach((button) => {
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
      case "performance_update":
        updatePostPerformance(payload.performance || payload.item || payload);
        addActivity(
          `Post performance updated for ${payload.performance?.content_title || payload.performance?.post_url || "a published post"}.`,
          "success"
        );
        showToast(`Post performance tracked for ${payload.performance?.content_title || "your post"}.`);
        break;
      case "rag_update":
        updateRagPanel(payload);
        addActivity(`AI generated a new recommendation for ${payload.current_trend || "a trend"}.`, "success");
        showToast(`AI recommendation updated for ${payload.current_trend || "a trend"}.`);
        scheduleLiveRefresh("RAG analysis");
        break;
      case "creator_analysis":
        showCreatorAnalysis(payload);
        addActivity(
          `Creator analysis completed for ${payload.current_request?.title || "a post idea"}.`,
          "success",
          payload.analysis?.prediction_label || ""
        );
        showToast(
          payload.analysis?.virality_score >= 75
            ? `High-potential post detected for ${payload.current_request?.title || "your idea"}.`
            : `Creator analysis completed for ${payload.current_request?.title || "your idea"}.`
        );
        if (payload.analysis?.virality_score >= 75) {
          playAlertTone();
        }
        break;
      case "activity":
        addActivity(payload.message || "Live activity received.", payload.level || "info");
        if (payload.kind === "trend_fetch" || payload.kind === "analysis" || payload.kind === "content_idea" || payload.kind === "forecast" || payload.kind === "creator_analysis") {
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

      socket.addEventListener("close", (event) => {
        state.ws.socket = null;
        if (event?.code === 1008 || event?.code === 1000) {
          setLiveStatus(false, "Live dashboard paused.");
          return;
        }
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
    if (value >= 85) return "High Viral";
    if (value >= 65) return "Trending";
    if (value >= 45) return "Average";
    return "Low Reach";
  }

  function currentSentimentLabel(trend) {
    return trend.sentiment_label || "Neutral";
  }

  function currentViralityLabel(trend) {
    const label = String(trend.virality_label || "").trim();
    if (label) {
      const normalized = label.toLowerCase();
      if (normalized === "high viral" || normalized === "trending" || normalized === "average" || normalized === "low reach") {
        return label;
      }
      if (normalized === "medium viral") return "Average";
      if (normalized === "low viral") return "Low Reach";
    }
    return viralityLabelFromScore(trend.virality_score);
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

  function formatBigNumber(value) {
    const number = safeNumber(value);
    if (number >= 1000000) return escapeHtml(`${(number / 1000000).toFixed(1)}M`);
    if (number >= 1000) return escapeHtml(`${(number / 1000).toFixed(1)}K`);
    return escapeHtml(Math.round(number).toString());
  }

  function calculateStats(items) {
    const total = items.length;
    const highViral = items.filter((trend) => safeNumber(trend.virality_score) >= 85).length;
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
    const performancePayload = state.ws.currentPostPerformance || {};
    const creatorPayload = state.ws.currentCreatorPayload || {};
    const creatorRequest = creatorPayload.current_request || {};
    const creatorAnalysis = creatorPayload.analysis || {};
    const bestForecast = getBestForecastTrend(trends);
    const topSource = getTopSource(trends);

    if (intelRagTitle) {
      intelRagTitle.textContent = creatorRequest.title || ragPayload.current_trend || "No creator analysis yet";
    }
    if (intelRagText) {
      intelRagText.textContent = creatorAnalysis.summary || ragAnalysis.final_recommendation || ragAnalysis.summary || "Run creator analysis or RAG to ground the next move in historical context.";
    }

    const forecastTrend = creatorAnalysis.prediction_label ? creatorAnalysis : forecastPayload.forecast || bestForecast;
    if (intelForecastTitle) {
      intelForecastTitle.textContent = creatorAnalysis.prediction_label || forecastPayload.current_trend || forecastTrend?.title || "No forecast yet";
    }
    if (intelForecastText) {
      intelForecastText.textContent = creatorAnalysis.growth_strategy || creatorAnalysis.why_it_may_trend || forecastTrend?.forecast_explanation || forecastTrend?.recommended_creator_actions?.[0] || performancePayload.summary || performancePayload.analysis_notes?.[0] || "Generate a forecast or creator analysis to see the strongest recommendation.";
    }

    if (intelSourceTitle) {
      intelSourceTitle.textContent = creatorRequest.platform_label || topSource.label || "Not available";
    }
    if (intelSourceText) {
      intelSourceText.textContent = creatorAnalysis.audience_persona || creatorRequest.content_type || topSource.detail || "Fetch or refresh live trends to identify the most active source.";
    }

    if (intelLiveTitle) {
      intelLiveTitle.textContent = creatorAnalysis.will_trend
        ? "High-potential post detected"
        : performancePayload.lifecycle_stage
          ? `${performancePayload.lifecycle_stage} post performance`
          : state.ws.connected
            ? "Connected live"
            : "Reconnecting";
    }
    if (intelLiveText) {
      const liveBits = [];
      if (creatorAnalysis.best_posting_time) {
        liveBits.push(`Best time ${creatorAnalysis.best_posting_time}`);
      }
      if (creatorAnalysis.audience_fit !== undefined) {
        liveBits.push(`Audience fit ${safeNumber(creatorAnalysis.audience_fit).toFixed(0)}%`);
      }
      if (performancePayload.virality_momentum !== undefined) {
        liveBits.push(`Momentum ${safeNumber(performancePayload.virality_momentum).toFixed(0)}%`);
      }
      if (performancePayload.growth_speed !== undefined) {
        liveBits.push(`Growth speed ${safeNumber(performancePayload.growth_speed).toFixed(0)}%`);
      }
      liveBits.push(`${state.ws.onlineUsers} connected users`);
      if (state.ws.lastUpdated) {
        liveBits.push(`Last update ${formatDate(state.ws.lastUpdated)}`);
      } else {
        liveBits.push("Awaiting the first live event");
      }
      intelLiveText.textContent = liveBits.join(" � ");
    }
  }

  function renderCurrentTrends(payload) {
    if (!currentTrendsList) return;
    const keywordItems = Array.isArray(payload?.trend_keywords) && payload.trend_keywords.length ? payload.trend_keywords : [];
    const trendItems = Array.isArray(payload?.items) ? payload.items : [];
    const items = keywordItems.length ? keywordItems : trendItems;
    state.currentTrends = trendItems.length ? trendItems : items;
    state.ws.currentTrendSnapshot = payload || null;
    const regionLabel = payload?.region_label || payload?.selected_region || payload?.region || trendRegion?.value || "India";
    window.selectedRegion = regionLabel;
    const sourceLabels = Array.isArray(payload?.source_labels) && payload.source_labels.length
      ? payload.source_labels
      : Array.isArray(payload?.items)
        ? Array.from(
            new Set(
              payload.items
                .map((item) => item?.source_label || item?.source_type || item?.platform)
                .filter(Boolean)
            )
          )
        : [];

    if (trendRegionSummary) {
      trendRegionSummary.textContent = `Region: ${regionLabel}${sourceLabels.length ? ` � Sources: ${sourceLabels.join(", ")}` : ""}`;
    }

    if (!items.length) {
      currentTrendsList.innerHTML = `<span class="trend-tag trend-tag--empty">No current trend keywords available.</span>`;
      return;
    }

    const sourceTags = sourceLabels.map((label) => `<span class="trend-tag trend-tag--source">${escapeHtml(label)}</span>`);
    const keywordTags = items
      .map((item) => {
        const keyword = item.keyword || item.title || item.name || "trend";
        const count = item.count ?? item.trend_score ?? "";
        return `<span class="trend-tag">${escapeHtml(keyword)}${count !== "" ? ` <strong>${escapeHtml(count)}</strong>` : ""}</span>`;
      })
      .join("");
    currentTrendsList.innerHTML = [...sourceTags, keywordTags].filter(Boolean).join("");
  }

  function renderThumbnailAnalysis(result) {
    if (!thumbnailAnalysis || !thumbnailAnalysisContent) return;
    const data = result || state.ws.currentThumbnailResult;
    if (!data) {
      thumbnailAnalysis.hidden = true;
      thumbnailAnalysisContent.innerHTML = "";
      return;
    }

    thumbnailAnalysis.hidden = false;
    thumbnailAnalysisContent.innerHTML = `
      <div class="thumbnail-analysis__card">
        <span>Thumbnail Score</span>
        <strong>${escapeHtml(safeNumber(data.thumbnail_score).toFixed(0))}%</strong>
      </div>
      <div class="thumbnail-analysis__card">
        <span>File Details</span>
        <p>${escapeHtml(data.file_name || "Uploaded image")} � ${escapeHtml(data.width || 0)} x ${escapeHtml(data.height || 0)} � ${escapeHtml(data.file_size_kb || 0)} KB</p>
      </div>
      <div class="thumbnail-analysis__card">
        <span>Image Metrics</span>
        <p>Brightness ${escapeHtml(data.brightness ?? 0)} � Contrast ${escapeHtml(data.contrast ?? 0)} � Text visibility ${escapeHtml(data.text_visibility ?? 0)}</p>
      </div>
      <div class="thumbnail-analysis__card">
        <span>Clickability</span>
        <p>${escapeHtml(safeNumber(data.clickability_score).toFixed(0))}%</p>
      </div>
      <div class="thumbnail-analysis__card">
        <span>Issues</span>
        <ul class="thumbnail-analysis__list">
          ${
            Array.isArray(data.issues) && data.issues.length
              ? data.issues.map((item) => `<li>${escapeHtml(item)}</li>`).join("")
              : "<li>No major image issues detected.</li>"
          }
        </ul>
      </div>
      <div class="thumbnail-analysis__card">
        <span>Suggestions</span>
        <ul class="thumbnail-analysis__list">
          ${
            Array.isArray(data.suggestions) && data.suggestions.length
              ? data.suggestions.map((item) => `<li>${escapeHtml(item)}</li>`).join("")
              : "<li>No suggestions available.</li>"
          }
        </ul>
      </div>
    `;
  }

  function setThumbnailPreview(file, previewUrl) {
    if (thumbnailPreviewImage) {
      if (previewUrl) {
        thumbnailPreviewImage.src = previewUrl;
        thumbnailPreviewImage.hidden = false;
      } else {
        thumbnailPreviewImage.removeAttribute("src");
        thumbnailPreviewImage.hidden = true;
      }
    }
    if (thumbnailUploadPlaceholder) {
      thumbnailUploadPlaceholder.hidden = Boolean(previewUrl);
    }
  }

  async function handleThumbnailUpload(event) {
    const file = event.target?.files?.[0];
    if (!file) {
      state.ws.currentThumbnailResult = null;
      renderThumbnailAnalysis(null);
      setThumbnailPreview(null, null);
      if (thumbnailUploadStatus) {
        thumbnailUploadStatus.textContent = "Upload an image to analyze its brightness, contrast, resolution, and file size.";
      }
      return;
    }

    const allowedTypes = ["image/jpeg", "image/png", "image/webp", "image/gif", "image/bmp"];
    if (!allowedTypes.includes(file.type)) {
      showToast("Please upload a JPG, PNG, WEBP, GIF, or BMP image.");
      if (thumbnailUpload) thumbnailUpload.value = "";
      return;
    }

    console.log("Thumbnail file selected", { name: file.name, type: file.type, size: file.size });

    if (state.ws.currentThumbnailPreviewUrl) {
      window.URL.revokeObjectURL(state.ws.currentThumbnailPreviewUrl);
    }
    state.ws.currentThumbnailPreviewUrl = window.URL.createObjectURL(file);
    setThumbnailPreview(file, state.ws.currentThumbnailPreviewUrl);
    if (thumbnailUploadStatus) {
      thumbnailUploadStatus.textContent = `Previewing ${file.name}. Analyzing image quality...`;
    }

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch("/api/analyze-thumbnail", {
        method: "POST",
        body: formData,
      });
      if (handleAuthRedirect(response)) return;
      const data = await parseJsonResponse(response);
      console.log("Thumbnail analysis response", data);
      if (!response.ok) throw new Error(data?.detail || data?.error || `Request failed (${response.status})`);
      if (!data?.success) throw new Error(data?.detail || data?.error || "Thumbnail analysis failed");

      state.ws.currentThumbnailResult = data;
      window.latestThumbnailResult = data;
      renderThumbnailAnalysis(data);
      if (thumbnailUploadStatus) {
        thumbnailUploadStatus.textContent = `Thumbnail analyzed. Score: ${safeNumber(data.thumbnail_score).toFixed(0)}%.`;
      }
      showToast(`Thumbnail analyzed with a score of ${safeNumber(data.thumbnail_score).toFixed(0)}%.`);
      if (window.latestAnalysis || state.ws.currentCreatorPayload) {
        refreshLinkedInDraft({ silent: true });
        refreshCreatorStrategy({ silent: true });
      }
    } catch (error) {
      console.error("Thumbnail analysis failed", error);
      showToast("Unable to analyze the thumbnail right now.");
      if (thumbnailUploadStatus) {
        thumbnailUploadStatus.textContent = "Thumbnail analysis failed. Please try again.";
      }
      state.ws.currentThumbnailResult = null;
      window.latestThumbnailResult = null;
      renderThumbnailAnalysis(null);
    }
  }

  function updateTrendMatchDisplay(score, note) {
    const numericScore = safeNumber(score);
    if (trendMatchScore) {
      trendMatchScore.textContent = `${numericScore.toFixed(0)}%`;
    }
    if (trendMatchNote) {
      trendMatchNote.textContent = note || "Trend match score updated from your latest analysis.";
    }
  }

  function getSelectedTrendRegion() {
    const region = trendRegion?.value || window.selectedRegion || "India";
    window.selectedRegion = region;
    if (performanceRegionBadge) {
      performanceRegionBadge.textContent = `Region: ${region}`;
    }
    return region;
  }

  async function loadCurrentTrends({ silent = false } = {}) {
    const region = getSelectedTrendRegion();
    const payload = {
      region,
      niche: creatorTitle?.value?.trim() || creatorContentType?.value || "",
      platform: creatorPlatform?.value || "LinkedIn",
      limit: 12,
    };
    try {
      const response = await fetch("/api/fetch-trends", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify(payload),
      });
      if (response.status === 401 || response.status === 403) {
        window.location.href = "/login";
        return;
      }
      if (!response.ok) throw new Error(`Failed to load current trends (${response.status})`);
      const data = await response.json();
      renderCurrentTrends(data);
      if (window.latestAnalysis || state.ws.currentCreatorPayload) {
        refreshCreatorStrategy({ silent: true });
      }
      if (!silent) {
        showToast(`Loaded ${data.region_label || region} trend snapshot.`);
      }
    } catch (error) {
      console.error(error);
      renderCurrentTrends({ region_label: region, region, items: [], trend_keywords: [], source_labels: [] });
      if (!silent) {
        showToast("Unable to load regional trends right now.");
      }
    }
  }

  function buildLatestAnalysisPayload() {
    const analysis = normalizeAnalysisPayload(window.latestAnalysis || state.ws.currentCreatorPayload || {});
    return {
      ...analysis,
      latest_analysis_result: analysis,
      thumbnail_result: state.ws.currentThumbnailResult || analysis.thumbnail_result || analysis.thumbnail_analysis || null,
      thumbnail_analysis: state.ws.currentThumbnailResult || analysis.thumbnail_result || analysis.thumbnail_analysis || null,
      competitor_analysis: window.latestCompetitorAnalysis || analysis.competitor_analysis || null,
      linkedin_post: state.ws.currentLinkedInPost || analysis.linkedin_post || "",
      linkedin_post_text: state.ws.currentLinkedInPost || analysis.linkedin_post_text || "",
      platform: creatorPlatform?.value || analysis.current_request?.platform || analysis.platform || "linkedin",
      content_type: creatorContentType?.value || analysis.current_request?.content_type || analysis.content_type || "",
      audience: creatorAudience?.value || analysis.current_request?.audience || analysis.audience || "",
      title: creatorTitle?.value?.trim() || analysis.current_request?.title || analysis.title || "",
      caption: creatorCaption?.value?.trim() || analysis.current_request?.caption || analysis.caption || "",
      hashtags: creatorHashtags?.value?.trim() || analysis.current_request?.hashtags || analysis.hashtags || "",
      trend_region: getSelectedTrendRegion(),
      region: getSelectedTrendRegion(),
    };
  }

  function buildStrategyPayload() {
    const analysis = normalizeAnalysisPayload(window.latestAnalysis || state.ws.currentCreatorPayload || {});
    const competitor = window.latestCompetitorAnalysis || analysis.competitor_analysis || null;
    const trendSnapshot = state.ws.currentTrendSnapshot || {};
    const trends = Array.isArray(state.currentTrends) && state.currentTrends.length ? state.currentTrends : Array.isArray(trendSnapshot.items) ? trendSnapshot.items : [];
    return {
      platform: creatorPlatform?.value || analysis.current_request?.platform || analysis.platform || "linkedin",
      content_type: creatorContentType?.value || analysis.current_request?.content_type || analysis.content_type || "",
      audience: creatorAudience?.value || analysis.current_request?.audience || analysis.audience || "",
      title: creatorTitle?.value?.trim() || analysis.current_request?.title || analysis.title || "",
      caption: creatorCaption?.value?.trim() || analysis.current_request?.caption || analysis.caption || "",
      hashtags: creatorHashtags?.value?.trim() || analysis.current_request?.hashtags || analysis.hashtags || "",
      trend_region: getSelectedTrendRegion(),
      region: getSelectedTrendRegion(),
      analysis_result: analysis,
      latest_analysis_result: analysis,
      competitor_analysis: competitor,
      trends,
      thumbnail_result: state.ws.currentThumbnailResult || analysis.thumbnail_result || analysis.thumbnail_analysis || null,
    };
  }

  function setStrategyLoading(isLoading) {
    if (strategyLoader) {
      strategyLoader.hidden = !isLoading;
    }
    if (strategyContent && isLoading) {
      strategyContent.hidden = true;
    }
    if (strategyEmpty && isLoading) {
      strategyEmpty.hidden = true;
    }
    if (strategyBtn) {
      strategyBtn.disabled = isLoading || !(window.latestAnalysis || state.ws.currentCreatorPayload);
    }
  }

  async function refreshCreatorStrategy({ silent = false } = {}) {
    const hasAnalysis = Boolean(window.latestAnalysis || state.ws.currentCreatorPayload || window.latestPostPerformance || state.ws.currentPostPerformance);
    if (!hasAnalysis) {
      if (!silent) {
        alert("Analyze content first");
        showToast("Analyze content first.");
      }
      renderStrategyPanel(null);
      return "";
    }

    setStrategyLoading(true);
    const payload = buildStrategyPayload();
    try {
      const response = await fetch("/api/creator-strategy", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify(payload),
      });
      if (handleAuthRedirect(response)) return "";
      const data = await parseJsonResponse(response);
      console.log("Creator strategy response", data);
      if (!response.ok) {
        const errorText = typeof data === "string" ? data : data?.detail || data?.error || `Request failed (${response.status})`;
        throw new Error(errorText);
      }
      renderStrategyPanel(data);
      if (!silent) {
        showToast("Creator strategy generated.");
      }
      return data;
    } catch (error) {
      console.error("Creator strategy generation failed", error);
      if (!silent) {
        alert(`Strategy generation failed: ${error.message || error}`);
        showToast("Strategy generation failed.");
      }
      if (strategyContent && state.ws.currentStrategyPayload) {
        strategyContent.hidden = false;
      } else {
        renderStrategyPanel(null);
      }
      return "";
    } finally {
      setStrategyLoading(false);
    }
  }

  function buildLinkedInPostDraft(source = window.latestAnalysis || state.ws.currentCreatorPayload || {}) {
    const analysis = normalizeAnalysisPayload(source || {});
    const request = analysis.current_request || {};
    const thumbnail = window.latestThumbnailResult || analysis.thumbnail_result || analysis.thumbnail_analysis || state.ws.currentThumbnailResult || {};
    const title = String(request.title || analysis.title || "").trim();
    const caption = String(request.caption || analysis.caption || "").trim();
    const hashtagsRaw = request.hashtags || analysis.hashtags || analysis.normalized_hashtags || "";
    const platform = String(request.platform || analysis.platform || "LinkedIn").trim() || "LinkedIn";
    const audience = String(request.audience || analysis.audience || "").trim();
    const linkedinProfile = "https://www.linkedin.com/in/charuka-p-91578b311";
    const githubUrl = "https://github.com/charupraba2";

    const thumbnailBits = [
      String(thumbnail.topic || "").trim(),
      String(thumbnail.visible_text || thumbnail.text || "").trim(),
      String(thumbnail.visual_theme || thumbnail.theme || "").trim(),
      String(thumbnail.learning_context || thumbnail.context_summary || "").trim(),
      String(thumbnail.project_context || thumbnail.project_type || "").trim(),
    ].filter(Boolean);
    const issueBits = Array.isArray(thumbnail.issues) ? thumbnail.issues.map((item) => String(item).trim()).filter(Boolean) : [];
    const suggestionBits = Array.isArray(thumbnail.suggestions) ? thumbnail.suggestions.map((item) => String(item).trim()).filter(Boolean) : [];
    const imageContextText = [...thumbnailBits, ...issueBits, ...suggestionBits].join(" ").trim();
    const titleCaptionText = [title, caption].filter(Boolean).join(" ").trim();

    if (!titleCaptionText && !imageContextText) {
      return "";
    }

    const combined = `${titleCaptionText} ${imageContextText}`.toLowerCase();
    const visibleText = String(thumbnail.visible_text || thumbnail.text || "").trim();
    const learningContext = String(thumbnail.learning_context || thumbnail.context_summary || "").trim();
    const projectContext = String(thumbnail.project_context || thumbnail.project_type || "").trim();
    const topicLabel = String(thumbnail.topic || title || projectContext || learningContext || "my latest project").trim();
    const thumbnailScore = thumbnail.thumbnail_score !== undefined && thumbnail.thumbnail_score !== null ? `${safeNumber(thumbnail.thumbnail_score).toFixed(0)}%` : "";

    let hook = `Sharing a quick update from ${topicLabel}.`;
    if (visibleText) {
      hook = `I turned the visual note on "${visibleText}" into a quick LinkedIn update.`;
    } else if (/ai|ml|machine|model|python|fastapi|technical|learning|note|concept/.test(combined)) {
      hook = `I shared a quick learning note on ${learningContext || topicLabel} and how it connects with real-world projects.`;
    } else if (/project|dashboard|build|demo|progress|workflow|launch|update|ship/.test(combined)) {
      hook = `Sharing a small progress update from my ${projectContext || topicLabel} dashboard.`;
    }

    const body = caption || (
      /project|dashboard|build|demo|progress|workflow|launch|update|ship/.test(combined)
        ? "This is a small progress update from the build process, with a focus on clarity, structure, and practical use."
        : "A quick breakdown of what I�m learning and how I�m applying it in a real project."
    );

    const contextLines = [];
    if (title) contextLines.push(`Title: ${title}`);
    if (audience) contextLines.push(`Audience: ${audience}`);
    if (platform) contextLines.push(`Platform: ${platform}`);
    if (visibleText) contextLines.push(`Visible text: ${visibleText}`);
    if (String(thumbnail.visual_theme || thumbnail.theme || "").trim()) contextLines.push(`Visual theme: ${String(thumbnail.visual_theme || thumbnail.theme || "").trim()}`);
    if (learningContext) contextLines.push(`Learning context: ${learningContext}`);
    if (projectContext) contextLines.push(`Project context: ${projectContext}`);
    if (thumbnailScore) contextLines.push(`Thumbnail score: ${thumbnailScore}`);

    const takeaway = suggestionBits.length
      ? `Takeaway: ${suggestionBits.slice(0, 2).join(" ")}`
      : issueBits.length
        ? `Takeaway: ${issueBits.slice(0, 2).join(" ")}`
        : "";

    let hashtags = "";
    if (Array.isArray(hashtagsRaw)) {
      hashtags = hashtagsRaw.map((item) => String(item).trim()).filter(Boolean).join(" ");
    } else {
      hashtags = String(hashtagsRaw || "").trim();
    }
    if (!hashtags) {
      hashtags = "#AI #Python #FastAPI";
    }

    const parts = [
      hook,
      "",
      body,
    ];

    if (contextLines.length) {
      parts.push("", `Image context: ${contextLines.join(" | ")}`);
    }

    if (takeaway) {
      parts.push("", takeaway);
    }

    parts.push(
      "",
      hashtags,
      "",
      `LinkedIn: ${linkedinProfile}`,
      `GitHub: ${githubUrl}`,
    );

    return parts.join("\n").trim();
  }

  function applyLinkedInDraft(text) {
    const output = document.getElementById("linkedinPostOutput") || document.getElementById("linkedinResult") || document.getElementById("linkedin-post-output");
    const draft = String(text || "").trim();
    state.ws.currentLinkedInPost = draft || null;
    window.generatedLinkedInPost = draft;
    if (output) {
      output.value = draft;
    }
    if (state.ws.currentCreatorPayload) {
      window.latestAnalysis = {
        ...(window.latestAnalysis || {}),
        linkedin_post: draft,
        linkedin_post_text: draft,
      };
    }
    return draft;
  }

  function refreshLinkedInDraft({ silent = false } = {}) {
    const draft = buildLinkedInPostDraft();
    if (!draft) {
      if (!silent) {
        alert("Please enter content or upload an image first.");
      }
      return "";
    }
    applyLinkedInDraft(draft);
    if (!silent) {
      showToast("LinkedIn post generated and ready to copy.");
    }
    return draft;
  }

  async function generateLinkedInPost() {
    return refreshLinkedInDraft({ silent: false });
  }

  async function postLinkedInDraft() {
    const output = document.getElementById("linkedinPostOutput") || document.getElementById("linkedinResult") || document.getElementById("linkedin-post-output");
    const text = output?.value || window.generatedLinkedInPost || "";
    if (!text.trim()) {
      alert("Generate LinkedIn post first");
      showToast("Generate LinkedIn post first.");
      return;
    }

    const shareUrl = "https://www.linkedin.com/feed/?shareActive=true";
    try {
      await navigator.clipboard.writeText(text);
      showToast("Post copied. Press Ctrl + V in LinkedIn.");
      window.open(shareUrl, "_blank", "noopener,noreferrer");
      return;
    } catch (error) {
      console.warn("Clipboard copy failed before LinkedIn redirect", error);
      if (output) {
        output.scrollIntoView({ behavior: "smooth", block: "center" });
        output.focus();
        output.select();
      }
      showToast("Clipboard blocked. Copy the draft manually, then LinkedIn will open.");
      prompt("Copy this post manually:", text);
      window.open(shareUrl, "_blank", "noopener,noreferrer");
    }
  }

  function openLinkedInPostModal() {
    const output = document.getElementById("linkedinPostOutput") || document.getElementById("linkedinResult") || document.getElementById("linkedin-post-output");
    const text = output?.value || window.generatedLinkedInPost || state.ws.currentLinkedInPost || "";
    if (!linkedinPostModal || !linkedinPostModalBody || !linkedinPostModalTitle) return;

    linkedinPostModalTitle.textContent = "Generated LinkedIn Post";
    linkedinPostModalBody.innerHTML = `
      <p class="modal-loading" style="margin-bottom: 1rem;">Review and copy the generated post below.</p>
      <textarea id="linkedinPostModalText" class="creator-linkedin__output" style="min-height: 320px; width: 100%;">${escapeHtml(text)}</textarea>
      <div class="creator-results__actions" style="margin-top: 1rem;">
        <button class="button secondary" type="button" id="copy-linkedin-post-modal-btn">Copy Post</button>
      </div>
    `;
    linkedinPostModal.setAttribute("aria-hidden", "false");
    linkedinPostModal.classList.add("is-open");
  }

  async function copyLinkedInPostFromModal() {
    const modalText = document.getElementById("linkedinPostModalText");
    const text = modalText?.value || window.generatedLinkedInPost || "";
    if (!text.trim()) {
      alert("Generate LinkedIn post first");
      return;
    }
    try {
      await navigator.clipboard.writeText(text);
      showToast("LinkedIn post copied to clipboard.");
    } catch (error) {
      console.warn("Clipboard copy failed from modal", error);
      prompt("Copy this post manually:", text);
    }
  }

  async function exportPdfReport() {
    const analysis = window.latestAnalysis;
    if (!analysis) {
      alert("Analyze content first");
      showToast("Analyze content first.");
      setStatus("Analyze content first to export a PDF report.");
      return;
    }

    try {
      const payload = buildLatestAnalysisPayload();
      console.log("Exporting PDF with payload", payload);
      const body = JSON.stringify(payload);
      let response = await fetch("/api/export-pdf", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/pdf",
        },
        body,
      });
      if (response.status === 404) {
        response = await fetch("/api/export-pdf-report", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/pdf",
          },
          body,
        });
      }
      if (handleAuthRedirect(response)) return;
      if (!response.ok) throw new Error(`Request failed (${response.status})`);
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = downloadUrl;
      link.download = "trendhunter_report.pdf";
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(downloadUrl);
      showToast("PDF report downloaded.");
      await loadWorkspace();
    } catch (error) {
      console.error(error);
      showToast("Could not export the PDF report right now.");
      setStatus("PDF export failed.");
    }
  }

  function renderCompetitorAnalysis(payload) {
    if (!competitorResultsContent || !competitorResultsEmpty) return;
    window.latestCompetitorAnalysis = payload || null;
    competitorResultsEmpty.hidden = true;
    competitorResultsContent.hidden = false;
    const hookWords = Array.isArray(payload.common_hook_words) ? payload.common_hook_words : [];
    const themes = Array.isArray(payload.keyword_themes) ? payload.keyword_themes : [];
    const recommendations = Array.isArray(payload.strategy_recommendations) ? payload.strategy_recommendations : [];
    const sampleTitles = Array.isArray(payload.sample_titles) ? payload.sample_titles : [];

    competitorResultsContent.innerHTML = `
      <div class="creator-results__header">
        <div>
          <p class="eyebrow">Competitor Insight Result</p>
          <h3>${escapeHtml(payload.competitor || "Competitor analysis")}</h3>
          <p class="section-copy">Region: ${escapeHtml(payload.region || window.selectedRegion || "Global")}</p>
        </div>
        <div class="creator-result-badges">
          <span class="trend-badge source-news">${escapeHtml(payload.content_style || "Balanced")}</span>
          <span class="trend-badge prediction-growing">${escapeHtml(payload.posting_pattern || "Observed pattern")}</span>
        </div>
      </div>
      <div class="creator-score-grid">
        ${creatorMetric("Sample Titles", sampleTitles.length, "")}
        ${creatorMetric("Hook Words", hookWords.length, "")}
        ${creatorMetric("Themes", themes.length, "")}
      </div>
      <div class="creator-recommendation-grid">
        ${creatorRecommendationCard("Common Hook Words", hookWords.map((item) => `${item.word} (${item.count})`).join(" � ") || "None")}
        ${creatorRecommendationCard("Content Style", payload.content_style || "Unknown")}
        ${creatorRecommendationCard("Posting Pattern", payload.posting_pattern || "Unknown")}
        ${creatorRecommendationCard("Keyword Themes", themes.map((item) => `${item.theme} (${item.weight})`).join(" � ") || "None")}
        ${creatorRecommendationCard("Strategy Recommendations", recommendations.join(" � ") || "No recommendations yet.")}
        ${creatorRecommendationCard("Sample Titles", sampleTitles.join(" � ") || "No sample titles found.")}
      </div>
    `;

    if (window.latestAnalysis || state.ws.currentCreatorPayload) {
      refreshCreatorStrategy({ silent: true });
    }
  }

  function renderStrategyCard(card) {
    if (!card) return "";
    const label = String(card.label || card.title || "Insight").trim();
    const value = String(card.value || card.text || "").trim();
    const detail = String(card.detail || card.note || "").trim();
    return `
      <article class="strategy-card">
        <span>${escapeHtml(label)}</span>
        <strong>${escapeHtml(value || "No insight yet")}</strong>
        ${detail ? `<p>${escapeHtml(detail)}</p>` : ""}
      </article>
    `;
  }

  function renderStrategyPanel(payload) {
    if (!strategyContent || !strategyEmpty || !strategyLoader) return;

    if (!payload || !payload.success) {
      strategyLoader.hidden = true;
      strategyContent.hidden = true;
      strategyEmpty.hidden = false;
      strategyContent.innerHTML = "";
      window.latestStrategy = null;
      state.ws.currentStrategyPayload = null;
      if (strategyStatus && !window.latestAnalysis) {
        strategyStatus.textContent = "Run content analysis first to unlock the strategy agent.";
      }
      return;
    }

    const cards = Array.isArray(payload.strategy_cards) ? payload.strategy_cards : [];
    const bullets = Array.isArray(payload.recommendation_bullets) ? payload.recommendation_bullets : [];
    const growthInsights = Array.isArray(payload.growth_insights) ? payload.growth_insights : [];
    const hashtags = Array.isArray(payload.recommended_hashtags) ? payload.recommended_hashtags : [];

    window.latestStrategy = payload;
    state.ws.currentStrategyPayload = payload;
    strategyLoader.hidden = true;
    strategyEmpty.hidden = true;
    strategyContent.hidden = false;
    strategyContent.innerHTML = `
      <div class="strategy-panel__result">
        <div class="creator-results__header">
          <div>
            <p class="eyebrow">Strategy Snapshot</p>
            <h3>${escapeHtml(payload.analysis_snapshot?.title || payload.summary || "Creator strategy")}</h3>
          </div>
          <div class="creator-result-badges">
            <span class="trend-badge source-${badgeKey(payload.source || "rules")}">${escapeHtml(payload.source || "rule-based")}</span>
            <span class="trend-badge prediction-growing">${escapeHtml(payload.confidence ? `${payload.confidence}% confidence` : "Action-ready")}</span>
          </div>
        </div>
        <p class="strategy-panel__summary">${escapeHtml(payload.summary || "Use the latest signals to shape the next post.")}</p>
        <div class="strategy-grid">
          ${cards.length ? cards.map(renderStrategyCard).join("") : ""}
        </div>
        <div class="strategy-callouts">
          <article class="strategy-callout">
            <span>Trend takeaway</span>
            <p>${escapeHtml(payload.trend_match_takeaway || "Trend match is currently limited. Lean on the strongest current keyword.")}</p>
          </article>
          <article class="strategy-callout">
            <span>Competitor takeaway</span>
            <p>${escapeHtml(payload.competitor_takeaway || "Competitor signals are not available yet.")}</p>
          </article>
        </div>
        <div class="strategy-panels">
          <article class="strategy-section">
            <h4>Recommendation bullets</h4>
            <ul class="strategy-list">
              ${
                bullets.length
                  ? bullets.map((item) => `<li>${escapeHtml(item)}</li>`).join("")
                  : "<li>No recommendations available.</li>"
              }
            </ul>
          </article>
          <article class="strategy-section">
            <h4>Growth insights</h4>
            <ul class="strategy-list">
              ${
                growthInsights.length
                  ? growthInsights.map((item) => `<li>${escapeHtml(item)}</li>`).join("")
                  : "<li>No growth insights available.</li>"
              }
            </ul>
          </article>
        </div>
        <div class="strategy-section">
          <h4>Recommended hashtags</h4>
          <p class="strategy-tags">${escapeHtml(hashtags.join(" ") || "No hashtags recommended yet.")}</p>
        </div>
      </div>
    `;
    if (strategyStatus) {
      strategyStatus.textContent = `Region: ${escapeHtml(payload.region || window.selectedRegion || "Global")} � Generated from virality ${safeNumber(payload.analysis_snapshot?.virality_score).toFixed(0)} and trend match ${safeNumber(payload.analysis_snapshot?.trend_match_score).toFixed(0)}%.`;
    }
  }

  function openAssistantSidebar() {
    if (!assistantSidebar) return;
    console.log("AI assistant sidebar opened");
    assistantSidebar.classList.remove("hidden");
    assistantSidebar.classList.add("is-open");
    assistantSidebar.setAttribute("aria-hidden", "false");
    if (assistantInput) {
      window.setTimeout(() => assistantInput.focus(), 50);
    }
    if (assistantMessages && !assistantMessages.childElementCount) {
      seedAssistantConversation();
    }
  }

  function closeAssistantSidebar() {
    if (!assistantSidebar) return;
    console.log("AI assistant sidebar closed");
    assistantSidebar.classList.remove("is-open");
    assistantSidebar.classList.add("hidden");
    assistantSidebar.setAttribute("aria-hidden", "true");
  }

  function clearAssistantChatHistory() {
    if (!assistantMessages) return;
    assistantMessages.innerHTML = "";
    seedAssistantConversation();
  }

  function seedAssistantConversation() {
    if (!assistantMessages || assistantMessages.childElementCount) return;
    appendAssistantMessage(
      "bot",
      "Hi ?? Ask me about your content strategy."
    );
  }

  function appendAssistantMessage(role, text, options = {}) {
    if (!assistantMessages) return null;
    const message = document.createElement("div");
    message.className = `ai-message ai-message--${role}`;
    if (options.typing) {
      message.classList.add("ai-message--typing");
      message.innerHTML = `
        <div class="ai-message__bubble" aria-label="Assistant typing">
          <span class="ai-typing"><span></span><span></span><span></span></span>
        </div>
      `;
    } else {
      message.innerHTML = `<div class="ai-message__bubble">${escapeHtml(text || "")}</div>`;
      if (Array.isArray(options.quickReplies) && options.quickReplies.length) {
        const quickWrap = document.createElement("div");
        quickWrap.className = "assistant-quick-actions";
        options.quickReplies.slice(0, 4).forEach((item) => {
          const button = document.createElement("button");
          button.type = "button";
          button.className = "assistant-quick-action";
          button.textContent = item;
          button.addEventListener("click", () => sendAssistantQuestion(item));
          quickWrap.appendChild(button);
        });
        message.appendChild(quickWrap);
      }
    }
    assistantMessages.appendChild(message);
    assistantMessages.scrollTop = assistantMessages.scrollHeight;
    return message;
  }

  function setAssistantTyping(isTyping) {
    if (assistantSend) {
      assistantSend.disabled = isTyping;
    }
    if (assistantInput) {
      assistantInput.disabled = isTyping;
    }
  }

  function buildAssistantPayload(question) {
    const latestAnalysis = window.latestAnalysis || state.ws.currentCreatorPayload || null;
    const latestStrategy = window.latestStrategy || state.ws.currentStrategyPayload || null;
    const latestCompetitor = window.latestCompetitorAnalysis || latestAnalysis?.competitor_analysis || null;
    const latestPerformance = window.latestPostPerformance || state.ws.currentPostPerformance || null;
    const currentTrends = state.currentTrends || [];
    const trendSnapshot = state.ws.currentTrendSnapshot || null;
    return {
      message: question,
      analysis: latestAnalysis,
      strategy_output: latestStrategy,
      competitor_analysis: latestCompetitor,
      post_performance: latestPerformance,
      trends: currentTrends,
      trend_snapshot: trendSnapshot,
      current_trends: trendSnapshot?.items || currentTrends,
      title: latestAnalysis?.current_request?.title || latestAnalysis?.title || creatorTitle?.value?.trim() || "",
      caption: latestAnalysis?.current_request?.caption || latestAnalysis?.caption || creatorCaption?.value?.trim() || "",
      audience: latestAnalysis?.current_request?.audience || latestAnalysis?.audience || creatorAudience?.value || "",
      platform: latestAnalysis?.current_request?.platform || latestAnalysis?.platform || creatorPlatform?.value || "",
      content_type: latestAnalysis?.current_request?.content_type || latestAnalysis?.content_type || creatorContentType?.value || "",
      hashtags: latestAnalysis?.current_request?.hashtags || latestAnalysis?.hashtags || creatorHashtags?.value || "",
      region: getSelectedTrendRegion(),
    };
  }

  async function sendAssistantQuestion(question) {
    const message = String(question || assistantInput?.value || "").trim();
    if (!message) {
      return;
    }

    console.log("AI assistant question submitted", message);

    openAssistantSidebar();
    appendAssistantMessage("user", message);
    if (assistantInput) {
      assistantInput.value = "";
    }

    const hasAnalysis = Boolean(
      window.latestAnalysis ||
      state.ws.currentCreatorPayload ||
      window.latestPostPerformance ||
      state.ws.currentPostPerformance
    );
    if (!hasAnalysis) {
      appendAssistantMessage("bot", "Analyze content first.");
      showToast("Analyze content first.");
      return;
    }

    const typing = appendAssistantMessage("bot", "", { typing: true });
    state.ws.currentAssistantTyping = typing;
    setAssistantTyping(true);

    try {
      const response = await fetch("/api/ai-chat", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify(buildAssistantPayload(message)),
      });
      if (handleAuthRedirect(response)) return;
      const data = await parseJsonResponse(response);
      console.log("AI assistant response", data);
      if (!response.ok) {
        const errorText = typeof data === "string" ? data : data?.detail || data?.error || `Request failed (${response.status})`;
        throw new Error(errorText);
      }
      if (typing) typing.remove();
      appendAssistantMessage("bot", data.reply || "I�m here, but I couldn�t generate a reply right now.", {
        quickReplies: data.quick_replies || [],
      });
    } catch (error) {
      console.error("AI chat request failed", error);
      if (typing) typing.remove();
      appendAssistantMessage("bot", `I couldn�t answer that right now. ${error.message || "Try again in a moment."}`);
      showToast("AI assistant is unavailable right now.");
    } finally {
      setAssistantTyping(false);
      state.ws.currentAssistantTyping = null;
    }
  }

  function renderWorkspaceSection(payload) {
    const analyses = Array.isArray(payload?.analyses) ? payload.analyses : [];
    const linkedinPosts = Array.isArray(payload?.linkedin_posts) ? payload.linkedin_posts : [];
    const reports = Array.isArray(payload?.reports) ? payload.reports : [];

    if (workspaceAnalyses) {
      workspaceAnalyses.innerHTML = analyses.length
        ? analyses.map((item) => `
            <div class="workspace-item">
              <strong>${escapeHtml(item.trend_title || "Untitled analysis")}</strong>
              <p>${escapeHtml((item.platform || "linkedin").toUpperCase())} � Virality ${escapeHtml(item.virality_score ?? 0)} � Match ${escapeHtml(item.trend_match_score ?? 0)}</p>
              <span>${escapeHtml(formatDate(item.created_at))}</span>
            </div>
          `).join("")
        : `<p class="modal-loading">No saved analyses yet.</p>`;
    }

    if (workspaceLinkedInPosts) {
      workspaceLinkedInPosts.innerHTML = linkedinPosts.length
        ? linkedinPosts.map((item) => `
            <div class="workspace-item">
              <strong>${escapeHtml(item.title || "LinkedIn draft")}</strong>
              <p>${escapeHtml((item.post_text || "").slice(0, 140) || "No content")}${(item.post_text || "").length > 140 ? "..." : ""}</p>
              <span>${escapeHtml(formatDate(item.created_at))}</span>
            </div>
          `).join("")
        : `<p class="modal-loading">No saved LinkedIn posts yet.</p>`;
    }

    if (workspaceReports) {
      workspaceReports.innerHTML = reports.length
        ? reports.map((item) => `
            <div class="workspace-item">
              <strong>${escapeHtml(item.filename || "trendhunter_report.pdf")}</strong>
              <p>${escapeHtml((item.payload?.title || item.payload?.current_request?.title || "Saved report"))}</p>
              <span>${escapeHtml(formatDate(item.created_at))}</span>
            </div>
          `).join("")
        : `<p class="modal-loading">No saved reports yet.</p>`;
    }
  }

  async function loadWorkspace() {
    try {
      const response = await fetch("/api/workspace", { headers: { Accept: "application/json" } });
      if (handleAuthRedirect(response)) return;
      if (!response.ok) throw new Error(`Request failed (${response.status})`);
      const data = await response.json();
      renderWorkspaceSection(data);
    } catch (error) {
      console.error("Failed to load workspace", error);
      renderWorkspaceSection({});
    }
  }

  function setAnalysisControlsEnabled(enabled) {
    if (generateLinkedInBtn) generateLinkedInBtn.disabled = !enabled;
    if (postLinkedInBtn) postLinkedInBtn.disabled = !enabled;
    if (exportPdfBtn) exportPdfBtn.disabled = !enabled;
    if (strategyBtn) strategyBtn.disabled = !enabled;
    if (clearAnalysisBtn) clearAnalysisBtn.disabled = !enabled;
    if (strategyStatus) {
      strategyStatus.textContent = enabled
        ? "Strategy unlocks with your latest analysis, trends, and competitor signals."
        : "Run content analysis first to unlock the strategy agent.";
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
            <h3 class="trend-title">${escapeHtml(title)}</h3>
          </div>
          <div class="trend-badge-group">
            <span class="trend-badge source-${badgeKey(sourceLabel)}">${escapeHtml(sourceLabel)}</span>
            <span class="trend-badge sentiment-${badgeKey(sentimentLabel)}">${escapeHtml(sentimentLabel)}</span>
            <span class="trend-badge virality-${badgeKey(viralityLabel)}">${escapeHtml(viralityLabel)}</span>
            <span class="trend-badge">${escapeHtml(platform)}</span>
          </div>
        </div>
        <p class="trend-description">${escapeHtml(trend.description || trend.summary || "No description available.")}</p>
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
        <div class="trend-item-card__footer trend-meta">
          <span class="trend-url">${escapeHtml(trend.url || "")}</span>
          <span>Fetched ${escapeHtml(fetchedAt)}</span>
        </div>
        <div class="trend-item-card__footer trend-item-card__footer--secondary trend-meta">
          <span>Analyzed ${escapeHtml(analyzedAt)}</span>
          <span>Virality ${escapeHtml(progressWidth.toFixed(0))}%</span>
        </div>
        <div class="trend-item-card__actions card-actions">
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
      const url = new URL(apiUrl, window.location.origin);
      url.searchParams.set("region", getSelectedTrendRegion());
      const response = await fetch(url.toString(), { headers: { Accept: "application/json" } });
      if (handleAuthRedirect(response)) return;
      if (!response.ok) throw new Error(`Failed to load trends (${response.status})`);
      const data = await response.json();
      state.allTrends = Array.isArray(data.items) ? data.items : [];
      applyFilters();
      updateLiveMeta();
      setStatus(`Loaded ${state.allTrends.length} stored trends for ${getSelectedTrendRegion()}.`);
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
      if (handleAuthRedirect(response)) return;
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

  async function loadPostPerformance() {
    try {
      const response = await fetch("/api/post-performance?limit=5", { headers: { Accept: "application/json" } });
      if (handleAuthRedirect(response)) return;
      if (!response.ok) throw new Error(`Failed to load post performance (${response.status})`);
      const data = await response.json();
      const latest = data.latest || (Array.isArray(data.items) && data.items.length ? data.items[0] : null);
      if (latest) {
        renderPostPerformance({
          performance: latest,
          current_post: latest.payload || latest,
          recommendations: latest.recommendations || {},
          forecast: latest.forecast || {},
          chart_data: latest.chart_data || {},
        });
      } else if (performanceEmpty && performanceContent) {
        performanceContent.hidden = true;
        performanceEmpty.style.display = "grid";
      }
    } catch (error) {
      console.error(error);
    }
  }

  window.trackPublishedPost = async function () {
    window.__trackPostClickStamp = Date.now();
    console.log("Track Performance clicked");
    const postUrl = String(performanceUrlInput?.value || "").trim();
    const likesValue = String(manualLikesInput?.value || "").trim();
    const commentsValue = String(manualCommentsInput?.value || "").trim();
    const sharesValue = String(manualSharesInput?.value || "").trim();
    const impressionsValue = String(manualImpressionsInput?.value || "").trim();
    const postAgeValue = String(postAgeInput?.value || "2 hours").trim();
    const likes = likesValue === "" ? null : Number(likesValue);
    const comments = commentsValue === "" ? null : Number(commentsValue);
    const shares = sharesValue === "" ? null : Number(sharesValue);
    const impressions = impressionsValue === "" ? null : Number(impressionsValue);
    if (!postUrl) {
      setStatus("Paste a published post URL before tracking performance.");
      showToast("Paste a published post URL first.");
      return;
    }
    if (!Number.isFinite(likes) || !Number.isFinite(comments) || !Number.isFinite(shares)) {
      setStatus("Add likes, comments, and shares before tracking performance.");
      showToast("Add likes, comments, and shares first.");
      return;
    }

    setLoading(true);
    setStatus("Tracking published post performance...");
    if (performanceContent) {
      performanceContent.hidden = false;
    }
    if (performanceEmpty) {
      performanceEmpty.style.display = "none";
    }

    try {
      console.log("Tracking post URL:", postUrl);
      const response = await fetch("/api/track-post", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({
          post_url: postUrl,
          publishedPostUrl: postUrl,
          platform: "",
          region: getSelectedTrendRegion(),
          likes,
          comments,
          shares,
          impressions: Number.isFinite(impressions) ? impressions : null,
          post_age: postAgeValue,
        }),
      });
      const data = await parseJsonResponse(response);
      console.log("Track post response:", data);
      if (!response.ok) throw new Error(data?.error || `Request failed (${response.status})`);
      if (!data?.success) throw new Error(data?.error || "Post performance tracking failed");
      renderPostPerformance(data);
      if (postPerformanceResult) {
        const perf = data.performance || data.analysis || {};
        postPerformanceResult.innerHTML = `
          <div class="metric-card">
            <h3>Post Performance Intelligence</h3>
            <p><b>Momentum Score:</b> ${safeNumber(perf.virality_momentum ?? data.momentum_score).toFixed(0)}%</p>
            <p><b>Lifecycle Stage:</b> ${escapeHtml(perf.lifecycle_stage || data.lifecycle_stage || "Rising")}</p>
            <p><b>Trend Relevance:</b> ${safeNumber(perf.trend_relevance ?? data.trend_relevance).toFixed(0)}%</p>
            <p><b>Recommendation:</b> ${escapeHtml((data.recommendations?.engagement_recommendation || data.recommendation || "Reply to comments quickly and create a follow-up post."))}</p>
          </div>
        `;
      }
      showToast(`Tracked performance for ${data.performance?.content_title || "published post"}.`);
      addActivity(
        `Tracked published post performance for ${data.performance?.content_title || postUrl}.`,
        "success",
        data.performance?.lifecycle_stage || ""
      );
      renderIntelligencePanel();
    } catch (error) {
      console.error(error);
      setStatus("Unable to track post performance right now. Please try again.");
      showToast("Unable to track post performance right now.");
      if (performanceContent) {
        performanceContent.innerHTML = `<p class="modal-loading">Unable to analyze this post right now.</p>`;
      }
      if (postPerformanceResult) {
        postPerformanceResult.innerHTML = `<p class="modal-loading">Unable to render post performance results right now.</p>`;
      }
      if (performanceEmpty) {
        performanceEmpty.hidden = true;
      }
    } finally {
      setLoading(false);
    }
  };

  async function submitPostPerformance(event) {
    event.preventDefault();
    await window.trackPublishedPost();
  }

  async function runAction(url, message) {
    setLoading(true);
    setStatus(message);
    try {
      let requestUrl = url;
      if (requestUrl.startsWith("/api/")) {
        const actionUrl = new URL(requestUrl, window.location.origin);
        actionUrl.searchParams.set("region", getSelectedTrendRegion());
        requestUrl = actionUrl.toString();
      }
      const response = await fetch(requestUrl, { headers: { Accept: "application/json" } });
      if (handleAuthRedirect(response)) return;
      if (!response.ok) throw new Error(`Request failed (${response.status})`);
      const data = await response.json();
      if (url === "/api/generate-alerts") {
        const count = Number(data.count || 0);
        showToast(count > 0 ? `${count} new high viral trend alerts generated.` : "No new alerts were generated.");
      }
      await loadDashboard();
      await loadAlerts();
      await loadPostPerformance();
      await loadCurrentTrends();
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

  function normalizeAnalysisPayload(payload) {
    const source = payload || {};
    const request = source.current_request || source.request || {};
    const analysis = source.analysis || source;
    const forecast = source.forecast || analysis.forecast || source.analysis?.forecast || {};
    const ragAnalysis = source.rag_analysis || analysis.rag_analysis || source.analysis?.rag_analysis || {};
    const similarTrends = Array.isArray(source.similar_trends || analysis.similar_trends)
      ? (source.similar_trends || analysis.similar_trends)
      : [];
    const warnings = Array.isArray(source.warnings || analysis.warnings) ? (source.warnings || analysis.warnings) : [];
    const thumbnailResult = source.thumbnail_result || source.thumbnail_analysis || analysis.thumbnail_result || analysis.thumbnail_analysis || state.ws.currentThumbnailResult || null;
    return {
      ...source,
      current_request: request,
      analysis,
      forecast,
      rag_analysis: ragAnalysis,
      similar_trends: similarTrends,
      warnings,
      thumbnail_result: thumbnailResult,
      thumbnail_analysis: thumbnailResult,
    };
  }

  function renderCreatorAnalysis(payload) {
    const normalized = normalizeAnalysisPayload(payload);
    const request = normalized.current_request || {};
    const analysis = normalized.analysis || {};
    const forecast = normalized.forecast || {};
    const ragAnalysis = normalized.rag_analysis || {};
    const similarTrends = Array.isArray(normalized.similar_trends) ? normalized.similar_trends : [];
    const warnings = Array.isArray(normalized.warnings) ? normalized.warnings : [];
    const thumbnailResult = normalized.thumbnail_result || normalized.thumbnail_analysis || state.ws.currentThumbnailResult || null;
    const thumbnailCards = thumbnailResult
      ? [
          creatorRecommendationCard("Thumbnail Score", `${safeNumber(thumbnailResult.thumbnail_score).toFixed(0)}%`),
          creatorRecommendationCard("Brightness", thumbnailResult.brightness ?? "n/a"),
          creatorRecommendationCard("Contrast", thumbnailResult.contrast ?? "n/a"),
          creatorRecommendationCard("Resolution", `${thumbnailResult.width || 0} x ${thumbnailResult.height || 0}`),
          creatorRecommendationCard("Issues", Array.isArray(thumbnailResult.issues) && thumbnailResult.issues.length ? thumbnailResult.issues.join(" � ") : "No major issues detected."),
          creatorRecommendationCard("Suggestions", Array.isArray(thumbnailResult.suggestions) && thumbnailResult.suggestions.length ? thumbnailResult.suggestions.join(" � ") : "No suggestions available."),
        ].join("")
      : "";
    const optimizedHashtags = Array.isArray(analysis.optimized_hashtags) ? analysis.optimized_hashtags : [];
    const thumbnailIdeas = Array.isArray(analysis.thumbnail_text_ideas) ? analysis.thumbnail_text_ideas : [];
    const platformTips = Array.isArray(analysis.platform_optimization_tips) ? analysis.platform_optimization_tips : [];
    const reachImprovement = Array.isArray(analysis.reach_improvement) ? analysis.reach_improvement : [];
    const similarSummary = similarTrends.length
      ? similarTrends.map((trend) => `
          <article class="creator-historical-card">
            <div class="creator-historical-card__top">
              <strong>${escapeHtml(trend.title || "Untitled trend")}</strong>
              <span class="trend-badge source-${badgeKey(trend.source_label || trend.platform)}">${escapeHtml(trend.source_label || trend.platform || "UNKNOWN")}</span>
            </div>
            <p>${escapeHtml(trend.summary || trend.description || "No summary available.")}</p>
            <div class="creator-historical-card__meta">
              <span>Virality ${escapeHtml(trend.virality_score ?? 0)}</span>
              <span>Match ${escapeHtml(trend.similarity_score ?? 0)}%</span>
              <span>${escapeHtml(trend.virality_label || trend.prediction_label || "Pending")}</span>
            </div>
          </article>
        `).join("")
      : `<p class="modal-loading">No close historical match was found. The creator strategy used broader historical context instead.</p>`;

    const gaugeScore = Math.max(0, Math.min(100, safeNumber(analysis.virality_score)));
    const growthPotential = Math.max(0, Math.min(100, safeNumber(analysis.growth_potential)));
    const opportunityScore = Math.max(0, Math.min(100, safeNumber(analysis.opportunity_score)));
    const saturationRisk = Math.max(0, Math.min(100, safeNumber(analysis.saturation_risk)));
    const engagementProbability = Math.max(0, Math.min(100, safeNumber(analysis.engagement_probability)));
    const regionLabel = normalized.region || request.region || window.selectedRegion || "Global";

    return `
      <div class="creator-results__header">
        <div>
          <p class="eyebrow">Creator Strategy Result</p>
          <h3>${escapeHtml(request.title || "Selected idea")}</h3>
        </div>
        <div class="creator-result-badges">
          <span class="trend-badge source-${badgeKey(request.platform_label || request.platform)}">${escapeHtml(request.platform_label || request.platform || "Unknown")}</span>
          <span class="trend-badge prediction-${badgeKey(analysis.prediction_label || "Pending")}">${escapeHtml(analysis.prediction_label || "Pending")}</span>
          <span class="trend-badge virality-${badgeKey(currentViralityLabel(analysis))}">${escapeHtml(currentViralityLabel(analysis))}</span>
          <span class="trend-badge source-${badgeKey(regionLabel)}">Region: ${escapeHtml(regionLabel)}</span>
        </div>
      </div>

      <div class="creator-gauge-wrap">
        <div class="creator-gauge" style="--creator-progress: ${gaugeScore};">
          <div class="creator-gauge__inner">
            <strong>${escapeHtml(gaugeScore.toFixed(0))}</strong>
            <span>Virality</span>
          </div>
        </div>
        <div class="creator-gauge-copy">
          <span class="summary-label">Growth Potential</span>
          <strong>${escapeHtml(growthPotential.toFixed(0))}%</strong>
          <p>${escapeHtml(analysis.growth_stage || "growing")} � ${escapeHtml(analysis.best_posting_time || "Best posting time unavailable")}</p>
        </div>
      </div>

      <div class="creator-score-grid">
        ${creatorMetric("Hook Strength", analysis.hook_strength, "%")}
        ${creatorMetric("Audience Fit", analysis.audience_fit, "%")}
        ${creatorMetric("Trend Alignment", analysis.trend_alignment, "%")}
        ${creatorMetric("Emotional Impact", analysis.emotional_impact, "%")}
        ${creatorMetric("Opportunity Score", opportunityScore, "%")}
        ${creatorMetric("Saturation Risk", saturationRisk, "%")}
        ${creatorMetric("Engagement Probability", engagementProbability, "%")}
        ${creatorMetric("Readability", analysis.readability, "%")}
        ${creatorMetric("Trend Match", payload.trend_match_score ?? analysis.trend_match_score, "%")}
      </div>

      <div class="creator-linkedin">
        <div class="creator-results__header">
          <div>
            <p class="eyebrow">LinkedIn Post</p>
            <h4>Review before copying</h4>
          </div>
        </div>
        <textarea id="linkedinPostOutput" class="creator-linkedin__output" placeholder="Generate a LinkedIn post from this analysis.">${escapeHtml(state.ws.currentLinkedInPost || "")}</textarea>
      </div>

      ${
        thumbnailCards
          ? `
            <section class="creator-thumbnail-section">
              <div class="creator-results__header">
                <div>
                  <p class="eyebrow">Thumbnail Result</p>
                  <h4>Image analysis summary</h4>
                </div>
              </div>
              <div class="creator-recommendation-grid">
                ${thumbnailCards}
              </div>
            </section>
          `
          : ""
      }

      ${
        warnings.length
          ? `<div class="creator-warning-list">${warnings.map((warning) => `<p>${escapeHtml(warning)}</p>`).join("")}</div>`
          : ""
      }
    `;
  }

  function creatorMetric(label, value, suffix = "") {
    if (value === null || value === undefined || value === "") {
      return "";
    }
    const numberValue = safeNumber(value);
    return `
      <article class="creator-score-card">
        <span>${escapeHtml(label)}</span>
        <strong>${escapeHtml(numberValue.toFixed(0))}${escapeHtml(suffix)}</strong>
      </article>
    `;
  }

  function creatorRecommendationCard(label, value) {
    if (value === null || value === undefined || value === "") {
      return "";
    }
    return `
      <article class="creator-recommendation-card">
        <span>${escapeHtml(label)}</span>
        <p>${escapeHtml(Array.isArray(value) ? value.join(" ") : value)}</p>
      </article>
    `;
  }

  function getViralityAnalyticsDataset(payload) {
    const normalized = normalizeAnalysisPayload(payload);
    const analysis = normalized.analysis || {};
    const metrics = [
      { key: "hook_strength", label: "Hook Strength" },
      { key: "emotional_impact", label: "Emotional Impact" },
      { key: "audience_fit", label: "Audience Fit" },
      { key: "trend_alignment", label: "Trend Alignment" },
      { key: "engagement_probability", label: "Engagement Probability" },
      { key: "readability", label: "Readability" },
      { key: "growth_potential", label: "Growth Potential" },
    ];

    const current = metrics.map((metric) => Math.max(0, Math.min(100, safeNumber(analysis[metric.key]))));
    const benchmark = metrics.map((metric) => {
      const base = {
        hook_strength: 90,
        emotional_impact: 88,
        audience_fit: 92,
        trend_alignment: 90,
        engagement_probability: 91,
        readability: 86,
        growth_potential: 93,
      };
      return base[metric.key] ?? 90;
    });
    const highViral = metrics.map((metric) => {
      const base = {
        hook_strength: 94,
        emotional_impact: 92,
        audience_fit: 95,
        trend_alignment: 93,
        engagement_probability: 96,
        readability: 90,
        growth_potential: 97,
      };
      return base[metric.key] ?? 95;
    });
    return {
      metrics,
      labels: metrics.map((metric) => metric.label),
      current,
      benchmark,
      highViral,
      score: Math.max(0, Math.min(100, safeNumber(analysis.virality_score))),
    };
  }

  function formatHourLabel(hourOffset) {
    const date = new Date();
    date.setHours(date.getHours() + hourOffset);
    return date.getHours().toString().padStart(2, "0") + ":00";
  }

  function getForecastModeConfig(mode) {
    const normalized = String(mode || "Global").trim().toLowerCase();
    const configs = {
      global: {
        label: "Global",
        multiplier: 1,
        peakShift: 0,
        subtitle: "Global mode compares broad trend momentum and creator opportunities across regions.",
      },
      india: {
        label: "India",
        multiplier: 1.08,
        peakShift: 1,
        subtitle: "India mode weights evening engagement and education-led creator content slightly higher.",
      },
      "tamil nadu": {
        label: "Tamil Nadu",
        multiplier: 1.04,
        peakShift: 1,
        subtitle: "Tamil Nadu mode emphasizes regional relevance and local audience timing signals.",
      },
      coimbatore: {
        label: "Coimbatore",
        multiplier: 0.97,
        peakShift: -1,
        subtitle: "Coimbatore mode favors practical, niche, and fast-to-consume creator content.",
      },
      chennai: {
        label: "Chennai",
        multiplier: 1.02,
        peakShift: 0,
        subtitle: "Chennai mode increases weight on professional and urban audience interactions.",
      },
      madurai: {
        label: "Madurai",
        multiplier: 0.95,
        peakShift: -1,
        subtitle: "Madurai mode reflects a more localized reach profile with strong community signals.",
      },
    };
    return configs[normalized] || configs.global;
  }

  function syncForecastStudioUI(datasetOrMode) {
    const modeLabel =
      typeof datasetOrMode === "string"
        ? getForecastModeConfig(datasetOrMode).label
        : datasetOrMode?.modeLabel || getForecastModeConfig(state.forecastMode).label;
    const config = getForecastModeConfig(modeLabel);
    if (forecastStudioTitle) {
      forecastStudioTitle.textContent = `${config.label} engagement forecast workspace`;
    }
    if (forecastStudioSubtitle) {
      forecastStudioSubtitle.textContent = config.subtitle;
    }
    if (forecastModeBadge) {
      forecastModeBadge.textContent = `${config.label} forecast mode`;
    }
    if (forecastEngagementTitle) {
      forecastEngagementTitle.textContent = `Estimated engagement momentum in ${config.label}`;
    }
    if (forecastProbabilityTitle) {
      forecastProbabilityTitle.textContent = `Viral probability and decay risk in ${config.label}`;
    }
  }

  function getEngagementForecastDataset(payload, mode = state.forecastMode) {
    const normalized = normalizeAnalysisPayload(payload);
    const analysis = normalized.analysis || {};
    const platformInfo = analysis.platform_intelligence || {};
    const platformScores = platformInfo.scores || {};
    const modeConfig = getForecastModeConfig(mode);
    const viralityScore = Math.max(0, Math.min(100, safeNumber(platformScores.platform_virality_score ?? analysis.platform_virality_score ?? analysis.virality_score)));
    const engagementProbability = Math.max(0, Math.min(100, safeNumber(platformScores.platform_engagement_probability ?? analysis.platform_engagement_probability ?? analysis.engagement_probability)));
    const confidence = Math.max(45, Math.min(98, 48 + (viralityScore * 0.28) + (engagementProbability * 0.24)));
    const baseReach = Math.max(1200, Math.round(((viralityScore * 180) + (engagementProbability * 75) + 1200) * modeConfig.multiplier));
    const peakIndex = Math.max(4, Math.min(20, Math.round((viralityScore / 100) * 16) + 4 + modeConfig.peakShift));

    const labels = Array.from({ length: 24 }, (_, index) => formatHourLabel(index));
    const likes = [];
    const comments = [];
    const shares = [];
    const reach = [];

    for (let hour = 0; hour < 24; hour += 1) {
      const distance = Math.abs(hour - peakIndex);
      const wave = Math.max(0.18, 1.18 - (distance * 0.09));
      const trendBoost = 1 + (engagementProbability / 240);
      const viralityBoost = 1 + (viralityScore / 320);
      const riseFactor = hour <= peakIndex ? 0.72 + (hour / Math.max(peakIndex, 1)) * 0.48 : 1.05 - ((hour - peakIndex) / Math.max(24 - peakIndex, 1)) * 0.24;
      const engagementScale = wave * trendBoost * viralityBoost * riseFactor;

      likes.push(Math.round(baseReach * 0.038 * engagementScale));
      comments.push(Math.round(baseReach * 0.006 * engagementScale));
      shares.push(Math.round(baseReach * 0.004 * engagementScale));
      reach.push(Math.round(baseReach * engagementScale));
    }

    const peakReach = Math.max(...reach);
    const peakTime = `${modeConfig.label} • ${labels[reach.indexOf(peakReach)] || labels[peakIndex] || labels[0]}`;
    const growthTrend = `${modeConfig.label} • ${peakIndex <= 8 ? "Fast early lift" : peakIndex <= 16 ? "Balanced growth" : "Late growth spike"}`;

    return {
      labels,
      likes,
      comments,
      shares,
      reach,
      peakTime,
      growthTrend,
      confidence,
      viralityScore,
      engagementProbability,
      modeLabel: modeConfig.label,
      estimateCards: {
        likes: likes[peakIndex] || likes[0] || 0,
        comments: comments[peakIndex] || comments[0] || 0,
        shares: shares[peakIndex] || shares[0] || 0,
        reach: peakReach,
      },
    };
  }

  function destroyViralityCharts() {
    if (!window.Chart || !window.visualAnalytics) return;
    ["radar", "bar", "comparison"].forEach((key) => {
      if (window.visualAnalytics[key]) {
        window.visualAnalytics[key].destroy();
        window.visualAnalytics[key] = null;
      }
    });
  }

  function buildChartTheme() {
    return {
      grid: "rgba(255, 255, 255, 0.08)",
      ticks: "#b8bfd6",
      labels: "#e5ecff",
      primary: "rgba(16, 185, 129, 0.84)",
      primaryFill: "rgba(16, 185, 129, 0.18)",
      accent: "rgba(245, 158, 11, 0.84)",
      accentFill: "rgba(245, 158, 11, 0.18)",
      secondary: "rgba(232, 121, 249, 0.84)",
      secondaryFill: "rgba(232, 121, 249, 0.16)",
      benchmark: "rgba(139, 92, 246, 0.9)",
      benchmarkFill: "rgba(139, 92, 246, 0.18)",
      comparison: "rgba(232, 121, 249, 0.88)",
      comparisonFill: "rgba(232, 121, 249, 0.16)",
    };
  }

  function createViralityCharts(payload) {
    if (!window.Chart || !viralityRadarChartCanvas || !viralityBarChartCanvas || !viralityComparisonChartCanvas) return;
    const dataset = getViralityAnalyticsDataset(payload);
    const theme = buildChartTheme();
    const commonOptions = {
      responsive: true,
      maintainAspectRatio: false,
      animation: {
        duration: 1200,
        easing: "easeOutQuart",
      },
      plugins: {
        legend: {
          labels: {
            color: theme.labels,
            usePointStyle: true,
            boxWidth: 10,
          },
        },
        tooltip: {
          backgroundColor: "rgba(15, 23, 42, 0.96)",
          titleColor: "#fff",
          bodyColor: "#f8fafc",
          borderColor: "rgba(255, 255, 255, 0.12)",
          borderWidth: 1,
        },
      },
    };

    destroyViralityCharts();

    window.visualAnalytics.radar = new window.Chart(viralityRadarChartCanvas, {
      type: "radar",
      data: {
        labels: dataset.labels,
        datasets: [
          {
            label: "Current Post",
            data: dataset.current,
            borderColor: theme.primary,
            backgroundColor: theme.primaryFill,
            pointBackgroundColor: "#fff",
            pointBorderColor: theme.primary,
            pointHoverBackgroundColor: "#fff",
            pointHoverBorderColor: theme.primary,
            borderWidth: 2,
            fill: true,
          },
          {
            label: "High Viral Benchmark",
            data: dataset.highViral,
            borderColor: theme.accent,
            backgroundColor: theme.accentFill,
            pointBackgroundColor: "#fff",
            pointBorderColor: theme.accent,
            pointHoverBackgroundColor: "#fff",
            pointHoverBorderColor: theme.accent,
            borderWidth: 2,
            fill: true,
          },
        ],
      },
      options: {
        ...commonOptions,
        scales: {
          r: {
            angleLines: { color: theme.grid },
            grid: { color: theme.grid },
            suggestedMin: 0,
            suggestedMax: 100,
            ticks: {
              backdropColor: "transparent",
              color: theme.ticks,
              stepSize: 20,
            },
            pointLabels: {
              color: theme.labels,
              font: {
                size: 11,
                weight: "600",
              },
            },
          },
        },
      },
    });

    window.visualAnalytics.bar = new window.Chart(viralityBarChartCanvas, {
      type: "bar",
      data: {
        labels: ["Current Post Score", "Ideal Viral Benchmark"],
        datasets: [
          {
            label: "Virality Score",
            data: [dataset.score, 90],
            borderRadius: 14,
            borderSkipped: false,
            backgroundColor: [theme.primary, theme.benchmark],
            borderColor: [theme.primary, theme.benchmark],
            borderWidth: 1,
          },
        ],
      },
      options: {
        ...commonOptions,
        scales: {
          x: {
            ticks: {
              color: theme.labels,
              font: {
                size: 10,
              },
            },
            grid: { color: "rgba(255, 255, 255, 0.04)" },
          },
          y: {
            beginAtZero: true,
            suggestedMax: 100,
            ticks: {
              color: theme.ticks,
              callback: (value) => `${value}%`,
            },
            grid: { color: theme.grid },
          },
        },
      },
    });

    window.visualAnalytics.comparison = new window.Chart(viralityComparisonChartCanvas, {
      type: "line",
      data: {
        labels: dataset.labels,
        datasets: [
          {
            label: "Current Post",
            data: dataset.current,
            borderColor: theme.primary,
            backgroundColor: theme.primaryFill,
            pointBackgroundColor: "#fff",
            pointBorderColor: theme.primary,
            tension: 0.38,
            fill: true,
          },
          {
            label: "High Viral Content",
            data: dataset.highViral,
            borderColor: theme.comparison,
            backgroundColor: theme.comparisonFill,
            pointBackgroundColor: "#fff",
            pointBorderColor: theme.comparison,
            tension: 0.38,
            fill: true,
          },
        ],
      },
      options: {
        ...commonOptions,
        scales: {
          x: {
            ticks: {
              color: theme.labels,
              maxRotation: 0,
              autoSkip: true,
              maxTicksLimit: 8,
              font: {
                size: 10,
              },
            },
            grid: { color: "rgba(255, 255, 255, 0.04)" },
          },
          y: {
            beginAtZero: true,
            suggestedMax: 100,
            ticks: {
              color: theme.ticks,
              callback: (value) => `${value}%`,
            },
            grid: { color: theme.grid },
          },
        },
      },
    });
  }

  function createEngagementForecastChart(payload) {
    if (!window.Chart || !engagementForecastChartCanvas) return;
    const dataset = getEngagementForecastDataset(payload, state.forecastMode);
    const theme = buildChartTheme();

    if (window.visualAnalytics.forecast) {
      window.visualAnalytics.forecast.destroy();
      window.visualAnalytics.forecast = null;
    }

    window.visualAnalytics.forecast = new window.Chart(engagementForecastChartCanvas, {
      type: "line",
      data: {
        labels: dataset.labels,
        datasets: [
          {
            label: `Estimated Engagement (${dataset.modeLabel})`,
            data: dataset.reach,
            borderColor: theme.primary,
            backgroundColor: theme.primaryFill,
            pointBackgroundColor: "#fff",
            pointBorderColor: theme.primary,
            pointRadius: 3,
            pointHoverRadius: 5,
            borderWidth: 2.5,
            tension: 0.42,
            fill: true,
          },
          {
            label: `Likes (${dataset.modeLabel})`,
            data: dataset.likes,
            borderColor: theme.accent,
            backgroundColor: theme.accentFill,
            pointBackgroundColor: "#fff",
            pointBorderColor: theme.accent,
            borderWidth: 1.8,
            tension: 0.35,
          },
          {
            label: `Comments (${dataset.modeLabel})`,
            data: dataset.comments,
            borderColor: theme.benchmark,
            backgroundColor: theme.benchmarkFill,
            pointBackgroundColor: "#fff",
            pointBorderColor: theme.benchmark,
            borderWidth: 1.8,
            tension: 0.35,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: {
          duration: 1400,
          easing: "easeOutQuart",
        },
        plugins: {
          legend: {
            labels: {
              color: theme.labels,
              usePointStyle: true,
              boxWidth: 10,
            },
          },
          tooltip: {
            backgroundColor: "rgba(15, 23, 42, 0.96)",
            titleColor: "#fff",
            bodyColor: "#f8fafc",
            borderColor: "rgba(255, 255, 255, 0.12)",
            borderWidth: 1,
          },
        },
        scales: {
          x: {
            ticks: {
              color: theme.labels,
              maxRotation: 0,
              autoSkip: true,
              maxTicksLimit: 8,
              font: {
                size: 10,
              },
            },
            grid: { color: "rgba(255, 255, 255, 0.04)" },
          },
          y: {
            beginAtZero: true,
            ticks: {
              color: theme.ticks,
              callback: (value) => `${value}`,
            },
            grid: { color: theme.grid },
          },
        },
      },
    });
  }

  function destroyEngagementGrowthChart() {
    if (window.visualAnalytics.engagementGrowth) {
      window.visualAnalytics.engagementGrowth.destroy();
      window.visualAnalytics.engagementGrowth = null;
    }
  }

  function createEngagementGrowthChart(payload) {
    if (!window.Chart || !engagementGrowthPredictionChartCanvas) return;
    const dataset = getEngagementForecastDataset(payload, state.forecastMode);
    const theme = buildChartTheme();
    destroyEngagementGrowthChart();

    window.visualAnalytics.engagementGrowth = new window.Chart(engagementGrowthPredictionChartCanvas, {
      type: "line",
      data: {
        labels: dataset.labels,
        datasets: [
          {
            label: `Estimated Reach (${dataset.modeLabel})`,
            data: dataset.reach,
            borderColor: theme.primary,
            backgroundColor: theme.primaryFill,
            pointBackgroundColor: "#fff",
            pointBorderColor: theme.primary,
            pointRadius: 2.5,
            pointHoverRadius: 4,
            borderWidth: 2.6,
            tension: 0.42,
            fill: true,
          },
          {
            label: `Estimated Likes (${dataset.modeLabel})`,
            data: dataset.likes,
            borderColor: theme.accent,
            backgroundColor: theme.accentFill,
            pointBackgroundColor: "#fff",
            pointBorderColor: theme.accent,
            pointRadius: 2,
            borderWidth: 1.6,
            tension: 0.35,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: {
          duration: 1500,
          easing: "easeOutQuart",
        },
        plugins: {
          legend: {
            labels: {
              color: theme.labels,
              usePointStyle: true,
              boxWidth: 10,
            },
          },
          tooltip: {
            backgroundColor: "rgba(15, 23, 42, 0.96)",
            titleColor: "#fff",
            bodyColor: "#f8fafc",
            borderColor: "rgba(255, 255, 255, 0.12)",
            borderWidth: 1,
          },
        },
        scales: {
          x: {
            ticks: {
              color: theme.labels,
              autoSkip: true,
              maxTicksLimit: 8,
              font: {
                size: 10,
              },
            },
            grid: { color: "rgba(255, 255, 255, 0.04)" },
          },
          y: {
            beginAtZero: true,
            ticks: {
              color: theme.ticks,
              callback: (value) => `${value}`,
            },
            grid: { color: theme.grid },
          },
        },
      },
    });
  }

  function updateEngagementGrowthPrediction(payload) {
    if (!window.Chart || !engagementGrowthPredictionChartCanvas) return;
    const dataset = getEngagementForecastDataset(payload, state.forecastMode);
    if (!dataset.labels.length) {
      destroyEngagementGrowthChart();
      return;
    }

    if (!window.visualAnalytics.engagementGrowth) {
      createEngagementGrowthChart(payload);
      return;
    }

    window.visualAnalytics.engagementGrowth.data.labels = dataset.labels;
    window.visualAnalytics.engagementGrowth.data.datasets[0].label = `Estimated Reach (${dataset.modeLabel})`;
    window.visualAnalytics.engagementGrowth.data.datasets[0].data = dataset.reach;
    window.visualAnalytics.engagementGrowth.data.datasets[1].label = `Estimated Likes (${dataset.modeLabel})`;
    window.visualAnalytics.engagementGrowth.data.datasets[1].data = dataset.likes;
    window.visualAnalytics.engagementGrowth.update();
  }

  function destroyPostPerformanceCharts() {
    if (window.visualAnalytics.postPerformanceGrowth) {
      window.visualAnalytics.postPerformanceGrowth.destroy();
      window.visualAnalytics.postPerformanceGrowth = null;
    }
    if (window.visualAnalytics.postPerformanceLifecycle) {
      window.visualAnalytics.postPerformanceLifecycle.destroy();
      window.visualAnalytics.postPerformanceLifecycle = null;
    }
  }

  function getPostPerformanceSource(payload) {
    return payload?.performance || payload?.item || payload?.analysis || payload || {};
  }

  function getPostPerformanceChartData(payload) {
    const source = getPostPerformanceSource(payload);
    const chartData = payload?.chart_data || source?.chart_data || {};
    const labels = Array.isArray(chartData.labels) && chartData.labels.length ? chartData.labels : ["T1", "T2", "T3", "T4", "T5", "T6", "T7"];
    return {
      labels,
      likes: Array.isArray(chartData.likes) && chartData.likes.length ? chartData.likes : labels.map(() => safeNumber(source.likes)),
      comments: Array.isArray(chartData.comments) && chartData.comments.length ? chartData.comments : labels.map(() => safeNumber(source.comments)),
      shares: Array.isArray(chartData.shares) && chartData.shares.length ? chartData.shares : labels.map(() => safeNumber(source.shares)),
      reach: Array.isArray(chartData.reach) && chartData.reach.length ? chartData.reach : labels.map(() => safeNumber(source.reach)),
      lifecycle: Array.isArray(chartData.lifecycle) && chartData.lifecycle.length ? chartData.lifecycle : labels.map(() => safeNumber(source.virality_momentum)),
    };
  }

  function createPostPerformanceCharts(payload) {
    if (!window.Chart || !postPerformanceGrowthChartCanvas || !postPerformanceLifecycleChartCanvas) return;
    const dataset = getPostPerformanceChartData(payload);
    const theme = buildChartTheme();
    destroyPostPerformanceCharts();

    window.visualAnalytics.postPerformanceGrowth = new window.Chart(postPerformanceGrowthChartCanvas, {
      type: "line",
      data: {
        labels: dataset.labels,
        datasets: [
          {
            label: "Reach",
            data: dataset.reach,
            borderColor: theme.primary,
            backgroundColor: theme.primaryFill,
            fill: true,
            tension: 0.38,
            borderWidth: 2.5,
            pointRadius: 2.5,
          },
          {
            label: "Likes",
            data: dataset.likes,
            borderColor: theme.accent,
            backgroundColor: theme.accentFill,
            fill: false,
            tension: 0.34,
            borderWidth: 2,
            pointRadius: 2,
          },
          {
            label: "Comments",
            data: dataset.comments,
            borderColor: theme.secondary,
            backgroundColor: theme.secondaryFill,
            fill: false,
            tension: 0.34,
            borderWidth: 1.8,
            pointRadius: 2,
          },
          {
            label: "Shares",
            data: dataset.shares,
            borderColor: theme.benchmark,
            backgroundColor: theme.benchmarkFill,
            fill: false,
            tension: 0.34,
            borderWidth: 1.8,
            pointRadius: 2,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 1400, easing: "easeOutQuart" },
        plugins: {
          legend: {
            labels: {
              color: theme.labels,
              usePointStyle: true,
              boxWidth: 10,
            },
          },
          tooltip: {
            backgroundColor: "rgba(15, 23, 42, 0.96)",
            titleColor: "#fff",
            bodyColor: "#f8fafc",
            borderColor: "rgba(255, 255, 255, 0.12)",
            borderWidth: 1,
          },
        },
        scales: {
          x: {
            ticks: { color: theme.labels, autoSkip: true, maxTicksLimit: 8, font: { size: 10 } },
            grid: { color: "rgba(255, 255, 255, 0.04)" },
          },
          y: {
            beginAtZero: true,
            ticks: { color: theme.ticks },
            grid: { color: theme.grid },
          },
        },
      },
    });

    window.visualAnalytics.postPerformanceLifecycle = new window.Chart(postPerformanceLifecycleChartCanvas, {
      type: "line",
      data: {
        labels: dataset.labels,
        datasets: [
          {
            label: "Lifecycle Momentum",
            data: dataset.lifecycle,
            borderColor: theme.primary,
            backgroundColor: theme.primaryFill,
            fill: true,
            tension: 0.42,
            borderWidth: 2.5,
            pointRadius: 2.5,
          },
          {
            label: "Engagement Pressure",
            data: dataset.likes.map((value, index) => Math.max(10, Math.min(100, safeNumber(value) / 12 + safeNumber(dataset.comments[index]) / 6))),
            borderColor: theme.secondary,
            backgroundColor: theme.secondaryFill,
            fill: false,
            tension: 0.34,
            borderWidth: 1.8,
            pointRadius: 2,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 1450, easing: "easeOutQuart" },
        plugins: {
          legend: {
            labels: {
              color: theme.labels,
              usePointStyle: true,
              boxWidth: 10,
            },
          },
          tooltip: {
            backgroundColor: "rgba(15, 23, 42, 0.96)",
            titleColor: "#fff",
            bodyColor: "#f8fafc",
            borderColor: "rgba(255, 255, 255, 0.12)",
            borderWidth: 1,
          },
        },
        scales: {
          x: {
            ticks: { color: theme.labels, autoSkip: true, maxTicksLimit: 8, font: { size: 10 } },
            grid: { color: "rgba(255, 255, 255, 0.04)" },
          },
          y: {
            beginAtZero: true,
            max: 100,
            ticks: { color: theme.ticks, callback: (value) => `${value}%` },
            grid: { color: theme.grid },
          },
        },
      },
    });
  }

  function updatePostPerformanceCharts(payload) {
    if (!window.Chart || !postPerformanceGrowthChartCanvas || !postPerformanceLifecycleChartCanvas) return;
    const dataset = getPostPerformanceChartData(payload);
    if (!dataset.labels.length) {
      destroyPostPerformanceCharts();
      return;
    }

    if (!window.visualAnalytics.postPerformanceGrowth || !window.visualAnalytics.postPerformanceLifecycle) {
      createPostPerformanceCharts(payload);
      return;
    }

    window.visualAnalytics.postPerformanceGrowth.data.labels = dataset.labels;
    window.visualAnalytics.postPerformanceGrowth.data.datasets[0].data = dataset.reach;
    window.visualAnalytics.postPerformanceGrowth.data.datasets[1].data = dataset.likes;
    window.visualAnalytics.postPerformanceGrowth.data.datasets[2].data = dataset.comments;
    window.visualAnalytics.postPerformanceGrowth.data.datasets[3].data = dataset.shares;
    window.visualAnalytics.postPerformanceGrowth.update();

    window.visualAnalytics.postPerformanceLifecycle.data.labels = dataset.labels;
    window.visualAnalytics.postPerformanceLifecycle.data.datasets[0].data = dataset.lifecycle;
    window.visualAnalytics.postPerformanceLifecycle.data.datasets[1].data = dataset.likes.map((value, index) => Math.max(10, Math.min(100, safeNumber(value) / 12 + safeNumber(dataset.comments[index]) / 6)));
    window.visualAnalytics.postPerformanceLifecycle.update();
  }

  function renderPostPerformanceRecommendations(performance, recommendations, forecast) {
    if (!performanceRecommendationsEl) return;
    const cards = Array.isArray(recommendations?.recommendation_cards) ? recommendations.recommendation_cards : [];
    const aiRecommendations = recommendations?.ai_recommendations || {};
    const source = [
      {
        title: "Repost Advice",
        value: aiRecommendations.repost_advice || (performance.should_repost ? "Yes, repost it." : "Wait and refine before reposting."),
      },
      {
        title: "Hook Advice",
        value: aiRecommendations.hook_advice || (performance.should_improve_hook ? "Improve the hook." : "The hook is serviceable."),
      },
      {
        title: "Caption Advice",
        value: aiRecommendations.caption_advice || (performance.should_shorten_caption ? "Shorten the caption." : "Caption length is fine."),
      },
      {
        title: "Trend Saturation",
        value: aiRecommendations.trend_saturation || (performance.is_saturated ? "The topic looks saturated." : "The topic still has room to grow."),
      },
      {
        title: "Follow-up Advice",
        value: aiRecommendations.follow_up_advice || (performance.should_follow_up ? "Create Part 2 soon." : "A follow-up is optional."),
      },
      {
        title: "Next Action",
        value: aiRecommendations.next_action || forecast.best_next_content || "Keep engaging with the current post.",
      },
    ];
    const combined = [...source, ...cards.map((item, index) => ({ title: `Signal ${index + 1}`, value: item }))];
    performanceRecommendationsEl.innerHTML = combined
      .map(
        (item) => `
          <article class="performance-recommendation-card">
            <span>${escapeHtml(item.title)}</span>
            <p>${escapeHtml(Array.isArray(item.value) ? item.value.join(" ") : item.value)}</p>
          </article>
        `
      )
      .join("");
  }

  function updatePostPerformance(payload) {
    const performance = getPostPerformanceSource(payload);
    if (!performance || !performance.post_url) return;
    state.ws.currentPostPerformance = performance;
    window.latestPostPerformance = performance;

    if (performanceEmpty) {
      performanceEmpty.style.display = "none";
    }
    if (performanceContent) {
      performanceContent.hidden = false;
    }

    if (performancePlatformBadge) {
      performancePlatformBadge.textContent = performance.platform_label || performance.platform || "Platform detected";
    }
    if (performanceRegionBadge) {
      performanceRegionBadge.textContent = `Region: ${performance.region || window.selectedRegion || "India"}`;
    }
    if (performanceSummaryTitle) {
      performanceSummaryTitle.textContent = performance.content_title || performance.post_url || "Published post";
    }
    if (performanceSummaryText) {
      performanceSummaryText.textContent = performance.summary || "Tracking engagement momentum and lifecycle in real time.";
    }
    if (performanceLifecycleStage) {
      performanceLifecycleStage.textContent = performance.lifecycle_stage || "Stable";
    }
    if (performanceMomentumBadge) {
      performanceMomentumBadge.textContent = `Momentum ${safeNumber(performance.virality_momentum).toFixed(0)}%`;
    }
    if (performanceTrendRelevanceBadge) {
      performanceTrendRelevanceBadge.textContent = `Relevance ${safeNumber(performance.trend_relevance).toFixed(0)}%`;
    }

    if (performanceLikesEl) performanceLikesEl.textContent = formatBigNumber(performance.likes);
    if (performanceCommentsEl) performanceCommentsEl.textContent = formatBigNumber(performance.comments);
    if (performanceSharesEl) performanceSharesEl.textContent = formatBigNumber(performance.shares);
    if (performanceReachEl) performanceReachEl.textContent = formatBigNumber(performance.reach);
    if (performanceImpressionsEl) performanceImpressionsEl.textContent = formatBigNumber(performance.impressions);
    if (performanceGrowthEl) performanceGrowthEl.textContent = `${safeNumber(performance.engagement_growth).toFixed(1)}%`;

    if (performanceMomentumEl) performanceMomentumEl.textContent = `${safeNumber(performance.virality_momentum).toFixed(0)}%`;
    if (performanceMomentumBar) performanceMomentumBar.style.width = `${Math.max(0, Math.min(100, safeNumber(performance.virality_momentum)))}%`;
    if (performanceGrowthSpeedEl) performanceGrowthSpeedEl.textContent = `${safeNumber(performance.growth_speed).toFixed(0)}%`;
    if (performanceGrowthSpeedBar) performanceGrowthSpeedBar.style.width = `${Math.max(0, Math.min(100, safeNumber(performance.growth_speed)))}%`;
    if (performanceTrendStrengthEl) performanceTrendStrengthEl.textContent = `${safeNumber(performance.trend_strength).toFixed(0)}%`;
    if (performanceTrendStrengthBar) performanceTrendStrengthBar.style.width = `${Math.max(0, Math.min(100, safeNumber(performance.trend_strength)))}%`;
    if (performanceEngagementVelocityEl) performanceEngagementVelocityEl.textContent = `${safeNumber(performance.engagement_velocity).toFixed(0)}%`;
    if (performanceEngagementVelocityBar) performanceEngagementVelocityBar.style.width = `${Math.max(0, Math.min(100, safeNumber(performance.engagement_velocity)))}%`;

    if (performanceExpectedReachEl) performanceExpectedReachEl.textContent = formatBigNumber(performance.expected_reach);
    if (performanceExpectedImpressionsEl) performanceExpectedImpressionsEl.textContent = formatBigNumber(performance.expected_impressions);
    if (performancePeakTimeEl) performancePeakTimeEl.textContent = performance.peak_engagement_time || "--";
    if (performanceDecayEl) performanceDecayEl.textContent = `${safeNumber(performance.engagement_decay).toFixed(0)}%`;

    renderPostPerformanceRecommendations(performance, payload.recommendations || {}, payload.forecast || {});
    updatePostPerformanceCharts(payload);
    renderIntelligencePanel();
  }

  function renderPostPerformance(payload) {
    updatePostPerformance(payload);
    const performance = getPostPerformanceSource(payload);
    if (!postPerformanceResult || !performance) return;

    const recommendations = payload?.recommendations || performance.recommendations || {};
    const forecast = payload?.forecast || performance.forecast || {};
    const lifecycle = performance.lifecycle_stage || "Stable";
    const nextAction = recommendations.next_action || recommendations.best_next_content || forecast.best_next_content || "Keep engaging with comments and monitor the next 24 hours.";
    const repostSuggestion = recommendations.should_repost ? "Yes, repost with a stronger hook." : "Not yet. Improve the hook before reposting.";

    postPerformanceResult.innerHTML = `
      <div class="post-performance-result-card">
        <div class="post-performance-result-card__row">
          <span class="summary-label">Performance Snapshot</span>
          <strong>${escapeHtml(performance.content_title || performance.post_url || "Published post")}</strong>
        </div>
        <div class="post-performance-result-card__grid">
          <div><span>Momentum</span><strong>${safeNumber(performance.virality_momentum).toFixed(0)}%</strong></div>
          <div><span>Lifecycle</span><strong>${escapeHtml(lifecycle)}</strong></div>
          <div><span>Trend Strength</span><strong>${safeNumber(performance.trend_strength).toFixed(0)}%</strong></div>
          <div><span>Engagement Velocity</span><strong>${safeNumber(performance.engagement_velocity).toFixed(0)}%</strong></div>
        </div>
        <div class="post-performance-result-card__copy">
          <p><strong>Engagement recommendation:</strong> ${escapeHtml(recommendations.engagement_recommendation || "Reply to comments quickly for better reach.")}</p>
          <p><strong>Next action:</strong> ${escapeHtml(nextAction)}</p>
          <p><strong>Repost suggestion:</strong> ${escapeHtml(repostSuggestion)}</p>
        </div>
      </div>
    `;
  }

  function updateEngagementForecast(payload) {
    if (!window.Chart || !engagementForecastChartCanvas) return;
    const dataset = getEngagementForecastDataset(payload, state.forecastMode);
    if (!dataset.labels.length) {
      if (window.visualAnalytics.forecast) {
        window.visualAnalytics.forecast.destroy();
        window.visualAnalytics.forecast = null;
      }
      return;
    }

    if (!window.visualAnalytics.forecast) {
      createEngagementForecastChart(payload);
    } else {
      window.visualAnalytics.forecast.data.labels = dataset.labels;
      window.visualAnalytics.forecast.data.datasets[0].label = `Estimated Engagement (${dataset.modeLabel})`;
      window.visualAnalytics.forecast.data.datasets[0].data = dataset.reach;
      window.visualAnalytics.forecast.data.datasets[1].label = `Likes (${dataset.modeLabel})`;
      window.visualAnalytics.forecast.data.datasets[1].data = dataset.likes;
      window.visualAnalytics.forecast.data.datasets[2].label = `Comments (${dataset.modeLabel})`;
      window.visualAnalytics.forecast.data.datasets[2].data = dataset.comments;
      window.visualAnalytics.forecast.update();
    }

    if (forecastLikesEl) forecastLikesEl.textContent = String(dataset.estimateCards.likes);
    if (forecastCommentsEl) forecastCommentsEl.textContent = String(dataset.estimateCards.comments);
    if (forecastSharesEl) forecastSharesEl.textContent = String(dataset.estimateCards.shares);
    if (forecastReachEl) forecastReachEl.textContent = String(dataset.estimateCards.reach);
    if (forecastGrowthTrendEl) forecastGrowthTrendEl.textContent = dataset.growthTrend;
    if (forecastConfidenceEl) forecastConfidenceEl.textContent = `${dataset.confidence.toFixed(0)}%`;
    if (forecastPeakTimeEl) forecastPeakTimeEl.textContent = dataset.peakTime;
    syncForecastStudioUI(dataset);
  }

  function getPlatformIntelligenceDataset(payload) {
    const normalized = normalizeAnalysisPayload(payload);
    const request = normalized.current_request || {};
    const analysis = normalized.analysis || {};
    const platformInfo = analysis.platform_intelligence || {};
    const scores = platformInfo.scores || {};
    const safeScores = {
      ctr_potential: safeNumber(scores.ctr_potential ?? analysis.ctr_potential ?? analysis.hook_strength),
      retention_potential: safeNumber(scores.retention_potential ?? analysis.retention_potential ?? analysis.readability),
      shareability: safeNumber(scores.shareability ?? analysis.shareability ?? analysis.emotional_impact),
      save_probability: safeNumber(scores.save_probability ?? analysis.save_probability ?? analysis.audience_fit),
      engagement_fit: safeNumber(scores.engagement_fit ?? analysis.engagement_fit ?? analysis.engagement_probability),
      algorithm_match_score: safeNumber(scores.algorithm_match_score ?? analysis.algorithm_match_score ?? analysis.virality_score),
      platform_virality_score: safeNumber(scores.platform_virality_score ?? analysis.platform_virality_score ?? analysis.virality_score),
      platform_engagement_probability: safeNumber(scores.platform_engagement_probability ?? analysis.platform_engagement_probability ?? analysis.engagement_probability),
    };
    const platformLabel = platformInfo.platform_label || request.platform_label || request.platform || analysis.platform_label || analysis.platform || "LinkedIn";
    const comparison = Array.isArray(platformInfo.comparison) ? platformInfo.comparison : [];
    const recommendations = Array.isArray(platformInfo.recommendations) ? platformInfo.recommendations : Array.isArray(analysis.platform_recommendations) ? analysis.platform_recommendations : [];
    return {
      labels: ["CTR Potential", "Retention", "Shareability", "Save Probability", "Engagement Fit", "Algorithm Match"],
      current: [
        safeScores.ctr_potential,
        safeScores.retention_potential,
        safeScores.shareability,
        safeScores.save_probability,
        safeScores.engagement_fit,
        safeScores.algorithm_match_score,
      ],
      benchmark: [92, 90, 90, 88, 91, 94],
      comparison,
      recommendations,
      summary: platformInfo.comparison_summary || analysis.platform_forecast_focus || "",
      currentPlatform: platformLabel,
      platformLabel,
      scores: safeScores,
      platformForecastFocus: platformInfo.forecast_focus || analysis.platform_forecast_focus || "",
      hookStyle: platformInfo.hook_style || "",
      captionStyle: platformInfo.caption_style || "",
      contentStructure: platformInfo.content_structure || "",
    };
  }

  function destroyPlatformIntelligenceCharts() {
    if (window.visualAnalytics.platformRadar) {
      window.visualAnalytics.platformRadar.destroy();
      window.visualAnalytics.platformRadar = null;
    }
    if (window.visualAnalytics.platformComparison) {
      window.visualAnalytics.platformComparison.destroy();
      window.visualAnalytics.platformComparison = null;
    }
  }

  function createPlatformIntelligenceCharts(payload) {
    if (!window.Chart || !platformAlgorithmRadarChartCanvas || !platformComparisonChartCanvas) return;
    const dataset = getPlatformIntelligenceDataset(payload);
    const theme = buildChartTheme();
    destroyPlatformIntelligenceCharts();

    window.visualAnalytics.platformRadar = new window.Chart(platformAlgorithmRadarChartCanvas, {
      type: "radar",
      data: {
        labels: dataset.labels,
        datasets: [
          {
            label: `Current ${dataset.platformLabel}`,
            data: dataset.current,
            borderColor: theme.primary,
            backgroundColor: theme.primaryFill,
            pointBackgroundColor: "#fff",
            pointBorderColor: theme.primary,
            borderWidth: 2,
          },
          {
            label: "Ideal algorithm benchmark",
            data: dataset.benchmark,
            borderColor: theme.accent,
            backgroundColor: theme.accentFill,
            pointBackgroundColor: "#fff",
            pointBorderColor: theme.accent,
            borderWidth: 2,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 1200, easing: "easeOutQuart" },
        plugins: {
          legend: {
            labels: {
              color: theme.labels,
              usePointStyle: true,
              boxWidth: 10,
            },
          },
          tooltip: {
            backgroundColor: "rgba(15, 23, 42, 0.96)",
            titleColor: "#fff",
            bodyColor: "#f8fafc",
            borderColor: "rgba(255, 255, 255, 0.12)",
            borderWidth: 1,
          },
        },
        scales: {
          r: {
            angleLines: { color: theme.grid },
            grid: { color: theme.grid },
            suggestedMin: 0,
            suggestedMax: 100,
            ticks: {
              backdropColor: "transparent",
              color: theme.ticks,
              stepSize: 20,
            },
            pointLabels: {
              color: theme.labels,
              font: {
                size: 11,
                weight: "600",
              },
            },
          },
        },
      },
    });

    const comparisonLabels = dataset.comparison.map((item) => item.platform_label);
    const comparisonScores = dataset.comparison.map((item) => item.score);
    window.visualAnalytics.platformComparison = new window.Chart(platformComparisonChartCanvas, {
      type: "bar",
      data: {
        labels: comparisonLabels.length ? comparisonLabels : ["LinkedIn", "YouTube", "Instagram", "Twitter/X"],
        datasets: [
          {
            label: "Platform fit score",
            data: comparisonScores.length ? comparisonScores : [75, 75, 75, 75],
            borderRadius: 14,
            borderSkipped: false,
            backgroundColor: [
              theme.primary,
              theme.accent,
              theme.benchmark,
              theme.comparison,
            ],
            borderColor: [
              theme.primary,
              theme.accent,
              theme.benchmark,
              theme.comparison,
            ],
            borderWidth: 1,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 1200, easing: "easeOutQuart" },
        plugins: {
          legend: {
            labels: {
              color: theme.labels,
              usePointStyle: true,
              boxWidth: 10,
            },
          },
          tooltip: {
            backgroundColor: "rgba(15, 23, 42, 0.96)",
            titleColor: "#fff",
            bodyColor: "#f8fafc",
            borderColor: "rgba(255, 255, 255, 0.12)",
            borderWidth: 1,
          },
        },
        scales: {
          x: {
            ticks: {
              color: theme.labels,
              maxRotation: 0,
              autoSkip: true,
              maxTicksLimit: 8,
              font: {
                size: 10,
              },
            },
            grid: { color: "rgba(255, 255, 255, 0.04)" },
          },
          y: {
            beginAtZero: true,
            suggestedMax: 100,
            ticks: {
              color: theme.ticks,
              callback: (value) => `${value}%`,
            },
            grid: { color: theme.grid },
          },
        },
      },
    });
  }

  function renderPlatformIntelligence(payload) {
    if (!platformAlgorithmCards || !platformAlgorithmRecommendations || !platformComparisonMode) return;
    const dataset = getPlatformIntelligenceDataset(payload);
    const comparison = dataset.comparison.length ? dataset.comparison : [
      { platform_label: "LinkedIn", score: 75, focus: "impressions + saves" },
      { platform_label: "YouTube", score: 75, focus: "views + retention" },
      { platform_label: "Instagram", score: 75, focus: "shares + reel reach" },
      { platform_label: "Twitter/X", score: 75, focus: "replies + repost velocity" },
    ];

    if (!payload) {
      platformAlgorithmCards.innerHTML = `
        <article class="creator-score-card platform-intelligence__score-card platform-intelligence__score-card--empty">
          <span>Platform Intelligence</span>
          <strong>Waiting</strong>
          <p>Analyze content to generate platform-specific score cards and recommendations.</p>
        </article>
      `;
      platformAlgorithmRecommendations.innerHTML = `<div class="platform-intelligence__rec-item">Analyze content first to see platform-aware recommendations.</div>`;
      platformComparisonMode.innerHTML = comparison.map((item) => `
        <article class="platform-comparison-card">
          <div class="platform-comparison-card__top">
            <strong>${escapeHtml(item.platform_label || "Platform")}</strong>
            <span>${escapeHtml(item.focus || "")}</span>
          </div>
          <div class="platform-comparison-card__bar">
            <div class="platform-comparison-card__fill" style="width: ${Math.max(0, Math.min(100, safeNumber(item.score)))}%"></div>
          </div>
          <p>${escapeHtml(safeNumber(item.score).toFixed(0))}% platform fit</p>
        </article>
      `).join("");
      destroyPlatformIntelligenceCharts();
      if (platformIntelligenceSection) {
        platformIntelligenceSection.dataset.platform = "none";
      }
      return;
    }

    const cards = [
      ["CTR Potential", dataset.scores.ctr_potential, "How well the hook can earn a click or tap."],
      ["Retention Potential", dataset.scores.retention_potential, "How well the structure can keep attention."],
      ["Shareability", dataset.scores.shareability, "How likely people are to reshare it."],
      ["Save Probability", dataset.scores.save_probability, "How likely the audience is to bookmark it."],
      ["Engagement Fit", dataset.scores.engagement_fit, "How well the content matches the platform signal."],
      ["Algorithm Match Score", dataset.scores.algorithm_match_score, "Overall platform-fit score."],
    ];

    platformAlgorithmCards.innerHTML = cards.map(([label, value, detail]) => `
      <article class="creator-score-card platform-intelligence__score-card">
        <span>${escapeHtml(label)}</span>
        <strong>${escapeHtml(safeNumber(value).toFixed(0))}%</strong>
        <p>${escapeHtml(detail)}</p>
      </article>
    `).join("");

    platformAlgorithmRecommendations.innerHTML = dataset.recommendations.length
      ? dataset.recommendations.map((item) => `<div class="platform-intelligence__rec-item">${escapeHtml(item)}</div>`).join("")
      : `<div class="platform-intelligence__rec-item">Analyze content to see platform-specific recommendations.</div>`;

    platformComparisonMode.innerHTML = comparison.map((item) => `
      <article class="platform-comparison-card">
        <div class="platform-comparison-card__top">
          <strong>${escapeHtml(item.platform_label || "Platform")}</strong>
          <span>${escapeHtml(item.focus || "")}</span>
        </div>
        <div class="platform-comparison-card__bar">
          <div class="platform-comparison-card__fill" style="width: ${Math.max(0, Math.min(100, safeNumber(item.score)))}%"></div>
        </div>
        <p>${escapeHtml(safeNumber(item.score).toFixed(0))}% platform fit</p>
      </article>
    `).join("");

    if (platformIntelligenceSection) {
      platformIntelligenceSection.dataset.platform = dataset.platformLabel;
    }

    if (!window.visualAnalytics.platformRadar || !window.visualAnalytics.platformComparison) {
      createPlatformIntelligenceCharts(payload);
    } else {
      const chartDataset = getPlatformIntelligenceDataset(payload);
      window.visualAnalytics.platformRadar.data.labels = chartDataset.labels;
      window.visualAnalytics.platformRadar.data.datasets[0].data = chartDataset.current;
      window.visualAnalytics.platformRadar.data.datasets[1].data = chartDataset.benchmark;
      window.visualAnalytics.platformRadar.update();

      window.visualAnalytics.platformComparison.data.labels = chartDataset.comparison.map((item) => item.platform_label);
      window.visualAnalytics.platformComparison.data.datasets[0].data = chartDataset.comparison.map((item) => item.score);
      window.visualAnalytics.platformComparison.update();
    }
  }

  function updateViralityCharts(payload) {
    if (!window.Chart) return;
    const dataset = getViralityAnalyticsDataset(payload);
    if (!dataset.labels.length) {
      destroyViralityCharts();
      return;
    }
    if (!window.visualAnalytics.radar || !window.visualAnalytics.bar || !window.visualAnalytics.comparison) {
      createViralityCharts(payload);
      return;
    }

    window.visualAnalytics.radar.data.labels = dataset.labels;
    window.visualAnalytics.radar.data.datasets[0].data = dataset.current;
    window.visualAnalytics.radar.data.datasets[1].data = dataset.highViral;
    window.visualAnalytics.radar.update();

    window.visualAnalytics.bar.data.datasets[0].data = [dataset.score, 90];
    window.visualAnalytics.bar.update();

    window.visualAnalytics.comparison.data.labels = dataset.labels;
    window.visualAnalytics.comparison.data.datasets[0].data = dataset.current;
    window.visualAnalytics.comparison.data.datasets[1].data = dataset.highViral;
    window.visualAnalytics.comparison.update();
  }

  function clearViralityCharts() {
    destroyViralityCharts();
    if (viralityRadarChartCanvas?.parentElement) {
      viralityRadarChartCanvas.parentElement.setAttribute("data-chart-empty", "true");
    }
  }

  function activateCreatorTab(tabName) {
    if (!creatorResultsContent) return;

    const buttons = creatorResultsContent.querySelectorAll("[data-creator-tab]");
    const panels = creatorResultsContent.querySelectorAll("[data-creator-panel]");

    buttons.forEach((button) => {
      button.classList.toggle("is-active", button.dataset.creatorTab === tabName);
    });

    panels.forEach((panel) => {
      panel.classList.toggle("is-active", panel.dataset.creatorPanel === tabName);
    });
  }

  function renderAnalysisResult(data) {
    const normalized = normalizeAnalysisPayload(data);
    window.latestAnalysis = normalized;
    console.log("latestAnalysis saved", window.latestAnalysis);
    console.log("Rendering analysis result", normalized);

    state.ws.currentCreatorPayload = normalized;
    state.ws.currentThumbnailResult = normalized.thumbnail_result || normalized.thumbnail_analysis || state.ws.currentThumbnailResult || null;
    window.latestThumbnailResult = state.ws.currentThumbnailResult;

    if (creatorResultsEmpty) {
      creatorResultsEmpty.hidden = true;
    }
    if (creatorResultsContent) {
      creatorResultsContent.hidden = false;
      creatorResultsContent.innerHTML = renderCreatorAnalysis(normalized);
    }

    activateCreatorTab("optimization");
    setAnalysisControlsEnabled(true);
    updateViralityCharts(normalized);
    updateEngagementForecast(normalized);
    updateEngagementGrowthPrediction(normalized);
    renderPlatformIntelligence(normalized);

    if (normalized.trend_match_score !== undefined && normalized.trend_match_score !== null) {
      updateTrendMatchDisplay(normalized.trend_match_score, "Trend match score updated from the latest creator analysis.");
    }

    if (state.ws.currentLinkedInPost) {
      const output = document.getElementById("linkedinPostOutput") || document.getElementById("linkedinResult") || document.getElementById("linkedin-post-output");
      window.generatedLinkedInPost = state.ws.currentLinkedInPost;
      if (output) output.value = state.ws.currentLinkedInPost;
    } else if (normalized.linkedin_post) {
      state.ws.currentLinkedInPost = normalized.linkedin_post;
      window.generatedLinkedInPost = normalized.linkedin_post;
      const output = document.getElementById("linkedinPostOutput") || document.getElementById("linkedinResult") || document.getElementById("linkedin-post-output");
      if (output) output.value = normalized.linkedin_post;
    } else {
      refreshLinkedInDraft({ silent: true });
    }

    renderThumbnailAnalysis(state.ws.currentThumbnailResult);
    renderIntelligencePanel();
    refreshCreatorStrategy({ silent: true });
  }

  function showCreatorAnalysis(payload) {
    renderAnalysisResult(payload);
  }

  function clearCreatorAnalysis() {
    if (!creatorResultsEmpty || !creatorResultsContent) return;
    console.log("Clearing dashboard analysis state");
    state.ws.currentCreatorPayload = null;
    state.ws.currentLinkedInPost = null;
    state.ws.currentStrategyPayload = null;
    state.ws.currentTrendSnapshot = null;
    window.latestAnalysis = null;
    window.latestStrategy = null;
    window.latestCompetitorAnalysis = null;
    window.latestThumbnailResult = null;
    window.generatedLinkedInPost = "";
    destroyViralityCharts();
    if (window.visualAnalytics.forecast) {
      window.visualAnalytics.forecast.destroy();
      window.visualAnalytics.forecast = null;
    }
    destroyEngagementGrowthChart();
    creatorResultsContent.hidden = true;
    creatorResultsContent.innerHTML = "";
    creatorResultsEmpty.hidden = false;
    if (competitorResultsEmpty) competitorResultsEmpty.hidden = false;
    if (competitorResultsContent) {
      competitorResultsContent.hidden = true;
      competitorResultsContent.innerHTML = "";
    }
    if (thumbnailUpload) thumbnailUpload.value = "";
    if (state.ws.currentThumbnailPreviewUrl) {
      window.URL.revokeObjectURL(state.ws.currentThumbnailPreviewUrl);
      state.ws.currentThumbnailPreviewUrl = null;
    }
    setThumbnailPreview(null, null);
    if (thumbnailUploadStatus) {
      thumbnailUploadStatus.textContent = "Upload an image to analyze its brightness, contrast, resolution, and file size.";
    }
    renderThumbnailAnalysis(null);
    if (analysisResult) {
      analysisResult.scrollIntoView({ behavior: "smooth", block: "start" });
    }
    setAnalysisControlsEnabled(false);
    updateTrendMatchDisplay(0, "Run content analysis to compare your post with current trends.");
    if (creatorTitle && creatorCaption && creatorHashtags) {
      creatorTitle.value = "";
      creatorCaption.value = "";
      creatorHashtags.value = "";
    }
    renderIntelligencePanel();
    renderStrategyPanel(null);
    renderPlatformIntelligence(null);
    clearAssistantChatHistory();
    closeAssistantSidebar();
    showToast("Dashboard cleared.");
  }

  function renderForecastAnalysis(detail) {
    const similarTrends = Array.isArray(detail.similar_trends) ? detail.similar_trends : [];
    const forecast = detail.forecast || detail;
    const probability = currentViralityProbability(forecast);
    const confidence = currentForecastConfidence(forecast);
    const opportunity = currentOpportunityScore(forecast);
    const risk = currentRiskScore(forecast);
    const regionLabel = detail.region || detail.region_label || forecast.region || window.selectedRegion || "Global";
    return `
      <div class="creator-results__header" style="margin-bottom: 1rem;">
        <div>
          <p class="eyebrow">Forecast Analytics</p>
          <h3>${escapeHtml(detail.current_trend || forecast.title || forecast.name || "Trend")}</h3>
        </div>
        <div class="creator-result-badges">
          <span class="trend-badge source-${badgeKey(regionLabel)}">Region: ${escapeHtml(regionLabel)}</span>
          <span class="trend-badge prediction-${badgeKey(forecast.prediction_label || "PENDING")}">${escapeHtml(forecast.prediction_label || "Pending")}</span>
        </div>
      </div>
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
        region: getSelectedTrendRegion(),
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
        region: getSelectedTrendRegion(),
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
          <span>${escapeHtml(trend.virality_label || "Low Reach")}</span>
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
        region: getSelectedTrendRegion(),
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

  function fillCreatorDemoIdea() {
    if (creatorPlatform) creatorPlatform.value = "instagram";
    if (creatorContentType) creatorContentType.value = "Reel";
    if (creatorAudience) creatorAudience.value = "Creators";
    if (creatorTitle) creatorTitle.value = "5 AI content ideas creators should post this week";
    if (creatorCaption) {
      creatorCaption.value = "Creators are using AI to speed up ideation, tighten hooks, and publish faster. This post breaks down a simple workflow anyone can copy today.";
    }
    if (creatorHashtags) creatorHashtags.value = "#creator #ai #contentstrategy #reels";
    setStatus("Demo creator idea loaded. You can analyze it now.");
  }

  function getCreatorPayload() {
    return {
      platform: creatorPlatform?.value || "instagram",
      title: creatorTitle?.value?.trim() || "",
      caption: creatorCaption?.value?.trim() || "",
      hashtags: creatorHashtags?.value?.trim() || "",
      content_type: creatorContentType?.value || "Post",
      target_audience: creatorAudience?.value || "General audience",
      audience: creatorAudience?.value || "General audience",
      trend_region: getSelectedTrendRegion(),
      region: getSelectedTrendRegion(),
      thumbnail_result: state.ws.currentThumbnailResult || window.latestThumbnailResult || null,
    };
  }

  async function parseJsonResponse(response) {
    const rawText = await response.text();
    if (!rawText) {
      return {};
    }
    try {
      return JSON.parse(rawText);
    } catch (error) {
      console.warn("Invalid JSON response received", error, rawText);
      return { success: false, error: "Invalid JSON response received from the server." };
    }
  }

  function handleAuthRedirect(response) {
    if (response.status === 401 || response.status === 403) {
      window.location.href = "/login";
      return true;
    }
    return false;
  }

  async function submitCreatorAnalysis(event) {
    event.preventDefault();
    const payload = getCreatorPayload();
    console.log("Creator analysis payload", payload);

    if (!payload.title) {
      setStatus("Please add a post title or idea before analyzing.");
      showToast("Add a post title or idea first.");
      return;
    }

    setLoading(true);
    setStatus("Analyzing creator content...");
    if (creatorResultsContent) {
      creatorResultsContent.hidden = false;
      creatorResultsContent.innerHTML = `<p class="modal-loading">Generating creator analysis...</p>`;
    }
    if (creatorResultsEmpty) {
      creatorResultsEmpty.hidden = true;
    }
    setAnalysisControlsEnabled(false);

    try {
      const response = await fetch("/api/analyze-post", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify(payload),
      });
      const data = await parseJsonResponse(response);
      if (handleAuthRedirect(response)) return;
      if (!response.ok) throw new Error(data?.error || `Request failed (${response.status})`);
      if (!data?.success) throw new Error(data?.error || "Analysis failed");
      window.latestAnalysis = data;
      console.log("latestAnalysis saved", window.latestAnalysis);
      renderAnalysisResult(data);
      refreshLinkedInDraft({ silent: true });
      updateTrendMatchDisplay(data.trend_match_score, "Trend match score updated from the latest creator analysis.");
      showToast(
        data.analysis?.virality_score >= 75
          ? `High-potential creator post detected for ${payload.title}.`
          : `Creator analysis completed for ${payload.title}.`
      );
      addActivity(
        `AI creator analysis completed for ${payload.title}.`,
        data.analysis?.virality_score >= 75 ? "success" : "info",
        data.analysis?.prediction_label || ""
      );
      renderIntelligencePanel();
    } catch (error) {
      console.error(error);
      setStatus("The creator analysis failed. Please try again.");
      showToast("Creator analysis failed. Please try again.");
      if (creatorResultsContent) {
        creatorResultsContent.innerHTML = `<p class="modal-loading">Unable to generate creator recommendations right now.</p>`;
      }
      if (creatorResultsEmpty) {
        creatorResultsEmpty.hidden = true;
      }
      setAnalysisControlsEnabled(false);
    } finally {
      setLoading(false);
    }
  }

  async function submitCompetitorAnalysis(event) {
    event.preventDefault();
    const competitor = competitorName?.value?.trim() || "";
    const topic = competitorTopic?.value?.trim() || "";

    if (!competitor && !topic) {
      setStatus("Enter a competitor name or topic first.");
      showToast("Enter a competitor name or topic first.");
      return;
    }

    setLoading(true);
    setStatus("Analyzing competitor content...");
    if (competitorResultsContent) {
      competitorResultsContent.hidden = false;
      competitorResultsContent.innerHTML = `<p class="modal-loading">Analyzing competitor signals...</p>`;
    }
    if (competitorResultsEmpty) {
      competitorResultsEmpty.hidden = true;
    }

    try {
      let response = await fetch("/api/competitor-analysis", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({
          competitor,
          topic: topic || null,
          platform: competitorPlatform?.value || null,
          region: getSelectedTrendRegion(),
        }),
      });
      if (response.status === 404) {
        response = await fetch("/api/analyze-competitor", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
          },
          body: JSON.stringify({
            competitor,
            topic: topic || null,
            platform: competitorPlatform?.value || null,
            region: getSelectedTrendRegion(),
          }),
        });
      }
      const data = await parseJsonResponse(response);
      if (handleAuthRedirect(response)) return;
      if (!response.ok) throw new Error(data?.detail || data?.error || `Request failed (${response.status})`);
      if (!data?.success) throw new Error(data?.detail || data?.error || "Competitor analysis failed");
      renderCompetitorAnalysis(data);
      showToast(`Competitor analysis completed for ${competitor || topic}.`);
    } catch (error) {
      console.error(error);
      setStatus("The competitor analysis failed. Please try again.");
      showToast("Competitor analysis failed. Please try again.");
      if (competitorResultsContent) {
        competitorResultsContent.innerHTML = `<p class="modal-loading">Unable to generate competitor recommendations right now.</p>`;
      }
      if (competitorResultsEmpty) {
        competitorResultsEmpty.hidden = true;
      }
    } finally {
      setLoading(false);
    }
  }

  async function copyLinkedInPost() {
    const output = document.getElementById("linkedinPostOutput") || document.getElementById("linkedinResult") || document.getElementById("linkedin-post-output");
    const text = output?.value || state.ws.currentLinkedInPost || "";
    if (!text) {
      showToast("Generate the LinkedIn post first.");
      return;
    }
    try {
      await navigator.clipboard.writeText(text);
      showToast("LinkedIn post copied to clipboard.");
    } catch (error) {
      console.error(error);
      showToast("Could not copy the LinkedIn post.");
    }
  }

  async function runAction(url, message) {
    setLoading(true);
    setStatus(message);
    try {
      let requestUrl = url;
      if (requestUrl.startsWith("/api/")) {
        const actionUrl = new URL(requestUrl, window.location.origin);
        actionUrl.searchParams.set("region", getSelectedTrendRegion());
        requestUrl = actionUrl.toString();
      }
      const response = await fetch(requestUrl, { headers: { Accept: "application/json" } });
      if (handleAuthRedirect(response)) return;
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
      await loadCurrentTrends();
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

  if (refreshCurrentTrendsBtn) {
    refreshCurrentTrendsBtn.addEventListener("click", () => loadCurrentTrends({ silent: false }));
  }

  if (trendRegion) {
    trendRegion.addEventListener("change", async () => {
      window.selectedRegion = getSelectedTrendRegion();
      console.log("Region changed", window.selectedRegion);
      await loadCurrentTrends({ silent: false });
      await loadDashboard();
      if (window.latestAnalysis || state.ws.currentCreatorPayload) {
        refreshCreatorStrategy({ silent: true });
      }
    });
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

  if (generateLinkedInBtn) {
    generateLinkedInBtn.addEventListener("click", generateLinkedInPost);
  }

  if (strategyBtn) {
    strategyBtn.addEventListener("click", () => refreshCreatorStrategy({ silent: false }));
  }

  if (assistantFab) {
    assistantFab.addEventListener("click", () => {
      if (assistantSidebar?.classList.contains("hidden")) {
        openAssistantSidebar();
      } else if (assistantSidebar?.classList.contains("is-open")) {
        closeAssistantSidebar();
      } else {
        openAssistantSidebar();
      }
    });
    assistantFab.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        if (assistantSidebar?.classList.contains("hidden")) {
          openAssistantSidebar();
        } else if (assistantSidebar?.classList.contains("is-open")) {
          closeAssistantSidebar();
        } else {
          openAssistantSidebar();
        }
      }
    });
  }

  if (assistantClose) {
    assistantClose.addEventListener("click", closeAssistantSidebar);
  }

  if (assistantInput) {
    assistantInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        sendAssistantQuestion(assistantInput.value || "");
      }
    });
  }

  if (assistantSend) {
    assistantSend.addEventListener("click", () => {
      sendAssistantQuestion(assistantInput?.value || "");
    });
  }

  if (assistantMessages) {
    assistantMessages.addEventListener("click", (event) => {
      const button = event.target.closest("[data-assistant-question]");
      if (!button) return;
      sendAssistantQuestion(button.dataset.assistantQuestion || button.textContent || "");
    });
  }

  if (postLinkedInBtn) {
    postLinkedInBtn.addEventListener("click", postLinkedInDraft);
  }

  if (clearAnalysisBtn) {
    clearAnalysisBtn.addEventListener("click", clearCreatorAnalysis);
  }

  if (exportPdfBtn) {
    exportPdfBtn.addEventListener("click", exportPdfReport);
  }

  if (creatorDemoBtn) {
    creatorDemoBtn.addEventListener("click", fillCreatorDemoIdea);
  }

  if (creatorForm) {
    creatorForm.addEventListener("submit", submitCreatorAnalysis);
  }

  if (performanceForm) {
    performanceForm.addEventListener("submit", submitPostPerformance);
  }

  if (postTrackingForm && postTrackingForm !== performanceForm) {
    postTrackingForm.addEventListener("submit", submitPostPerformance);
  }

  if (trackPostBtn) {
    console.log("Track button found:", trackPostBtn);
  }

  if (thumbnailUpload) {
    thumbnailUpload.addEventListener("change", handleThumbnailUpload);
  }

  if (creatorResultsContent) {
    creatorResultsContent.addEventListener("click", (event) => {
      const tabButton = event.target.closest("[data-creator-tab]");
      if (!tabButton) return;
      activateCreatorTab(tabButton.dataset.creatorTab || "optimization");
    });
  }

  if (competitorForm) {
    competitorForm.addEventListener("submit", submitCompetitorAnalysis);
  }

  if (currentTrendsRefreshBtn) {
    currentTrendsRefreshBtn.addEventListener("click", loadCurrentTrends);
  }

  if (workspaceRefreshBtn) {
    workspaceRefreshBtn.addEventListener("click", loadWorkspace);
  }

  if (refreshBtn) {
    refreshBtn.addEventListener("click", loadDashboard);
  }

  if (forecastModeSelect) {
    forecastModeSelect.addEventListener("change", () => {
      state.forecastMode = forecastModeSelect.value || "Global";
      syncForecastStudioUI(state.forecastMode);
      const latestForecastSource = window.latestAnalysis || state.ws.currentCreatorPayload || state.ws.currentForecastPayload || null;
      if (latestForecastSource) {
        updateEngagementForecast(latestForecastSource);
        updateEngagementGrowthPrediction(latestForecastSource);
      }
    });
  }

  if (sidebarAssistantBtn) {
    sidebarAssistantBtn.addEventListener("click", openAssistantSidebar);
  }

  if (openAssistantSidebarBtn) {
    openAssistantSidebarBtn.addEventListener("click", openAssistantSidebar);
  }

  if (sidebarSettingsBtn) {
    sidebarSettingsBtn.addEventListener("click", () => {
      showToast("Settings panel coming soon.");
    });
  }

  if (dashboardNotificationsBtn) {
    dashboardNotificationsBtn.addEventListener("click", () => {
      setDashboardTab("trends");
      showToast("Live alerts are visible in the right rail.");
    });
  }

  if (dashboardProfileBtn) {
    dashboardProfileBtn.addEventListener("click", () => {
      showToast("Profile menu coming soon.");
    });
  }

  dashboardTabs.forEach((button) => {
    button.addEventListener("click", () => {
      setDashboardTab(button.dataset.dashboardTab || "overview");
    });
  });
  setDashboardTab(state.activeTab || "overview");

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

  if (linkedinPostModal) {
    linkedinPostModal.addEventListener("click", (event) => {
      if (event.target && event.target.matches("[data-close-linkedin-modal]")) {
        closeModal(linkedinPostModal);
      }
      if (event.target && event.target.id === "copy-linkedin-post-modal-btn") {
        copyLinkedInPostFromModal();
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
    if (state.ws.currentThumbnailPreviewUrl) {
      window.URL.revokeObjectURL(state.ws.currentThumbnailPreviewUrl);
    }
  });

  bindFilterEvents();
  renderPlatformIntelligence(null);
  loadDashboard();
  loadAlerts();
  loadPostPerformance();
  loadCurrentTrends({ silent: true });
  loadWorkspace();
  setAnalysisControlsEnabled(Boolean(window.latestAnalysis || state.ws.currentCreatorPayload));
  renderThumbnailAnalysis(state.ws.currentThumbnailResult);
  renderStrategyPanel(null);
  seedAssistantConversation();
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
        <p>${escapeHtml(detail.virality_label || "Low Reach")}</p>
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





