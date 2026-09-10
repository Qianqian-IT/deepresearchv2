/* ==========================================================================
   DeepResearch Enterprise —— 前端单页应用（原生 JS，无构建依赖）
   - 登录态存 localStorage；EventSource 走 ?token= 鉴权（浏览器不支持自定义头）
   - 进度：SSE 实时推送，失败自动降级为轮询 /events
   ========================================================================== */
(function () {
  'use strict';

  var API_BASE = window.DR_API_BASE || '';
  var TOKEN_KEY = 'dr_token';
  var PROFILE_KEY = 'dr_profile';

  var STAGES = [
    { key: 'planner', label: '规划拆解', note: '把目标拆成可检索的子问题' },
    { key: 'think', label: '推理决策', note: '决定下一步搜什么或收工' },
    { key: 'act', label: '检索取证', note: '调用搜索并做信源分级' },
    { key: 'observe', label: '筛选提炼', note: '过滤低质信息，保留事实' },
    { key: 'analyze', label: '交叉分析', note: '合并洞察、识别冲突与缺口' },
    { key: 'report', label: '报告成稿', note: '生成结构化调研报告' }
  ];

  var state = {
    token: localStorage.getItem(TOKEN_KEY) || '',
    profile: null,
    currentTask: null,
    eventSource: null,
    pollTimer: null,
    lastSeq: 0,
    findings: 0,
    logCount: 0,
    seenStages: {},
    lastStage: ''
  };

  /* ---------------------------------------------------------------- 工具 */
  function $(sel, root) { return (root || document).querySelector(sel); }
  function $all(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }

  function fmtNum(n) {
    n = Number(n || 0);
    if (n >= 1e6) return (n / 1e6).toFixed(2) + 'M';
    if (n >= 1e3) return (n / 1e3).toFixed(1) + 'k';
    return String(n);
  }

  function fmtTime(iso) {
    if (!iso) return '—';
    var d = new Date(iso);
    if (isNaN(d.getTime())) return '—';
    var p = function (x) { return String(x).padStart(2, '0'); };
    return p(d.getMonth() + 1) + '-' + p(d.getDate()) + ' ' + p(d.getHours()) + ':' + p(d.getMinutes());
  }

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function toast(message, kind) {
    var el = document.createElement('div');
    el.className = 'toast ' + (kind || '');
    el.textContent = message;
    $('#toast-wrap').appendChild(el);
    setTimeout(function () {
      el.style.opacity = '0';
      el.style.transition = 'opacity .3s';
      setTimeout(function () { el.remove(); }, 320);
    }, kind === 'error' ? 5200 : 3200);
  }

  var STATUS_TEXT = {
    pending_clarify: '待澄清', queued: '排队中', running: '运行中',
    succeeded: '已成功', failed: '已失败', cancelled: '已取消'
  };
  var STATUS_CLASS = {
    pending_clarify: 'pending', queued: 'pending', running: 'running',
    succeeded: 'succeeded', failed: 'failed', cancelled: 'cancelled'
  };

  /* ---------------------------------------------------------------- 请求 */
  function api(path, options) {
    options = options || {};
    var headers = { 'Content-Type': 'application/json' };
    if (state.token) headers.Authorization = 'Bearer ' + state.token;

    return fetch(API_BASE + path, {
      method: options.method || 'GET',
      headers: headers,
      body: options.body ? JSON.stringify(options.body) : undefined
    }).then(function (res) {
      if (res.status === 401) {
        logout(true);
        throw new Error('登录已失效，请重新登录');
      }
      return res.text().then(function (text) {
        var data = null;
        try { data = text ? JSON.parse(text) : null; } catch (e) { data = text; }
        if (!res.ok) {
          var detail = data && data.detail ? data.detail : ('请求失败（HTTP ' + res.status + '）');
          throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
        }
        return data;
      });
    });
  }

  function withLoading(btn, promise) {
    if (!btn) return promise;
    var html = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> 处理中';
    return promise.finally(function () {
      btn.disabled = false;
      btn.innerHTML = html;
    });
  }

  /* ---------------------------------------------------------------- 视图 */
  function switchView(name) {
    ['dashboard', 'new', 'clarify', 'progress', 'report', 'settings'].forEach(function (v) {
      var el = $('#view-' + v);
      if (el) el.classList.toggle('hidden', v !== name);
    });
    $all('.nav-item[data-nav]').forEach(function (b) {
      b.classList.toggle('active', b.getAttribute('data-nav') === name);
    });
    $('#sidebar').classList.remove('open');
    window.scrollTo({ top: 0, behavior: 'smooth' });

    if (name === 'dashboard') loadDashboard();
    if (name === 'settings') loadSettings();
  }

  function showApp() {
    $('#view-auth').classList.add('hidden');
    $('#shell').classList.remove('hidden');
    var p = state.profile || {};
    $('#side-tenant-name').textContent = p.tenant_name || '—';
    $('#side-user').textContent = (p.email || '—') + ' · ' + (p.role === 'owner' ? '管理员' : '成员');
  }

  function showAuth() {
    $('#shell').classList.add('hidden');
    $('#view-auth').classList.remove('hidden');
  }

  function saveSession(data) {
    state.token = data.access_token;
    state.profile = data;
    localStorage.setItem(TOKEN_KEY, data.access_token);
    localStorage.setItem(PROFILE_KEY, JSON.stringify(data));
  }

  function logout(silent) {
    stopStream();
    state.token = '';
    state.profile = null;
    state.currentTask = null;
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(PROFILE_KEY);
    showAuth();
    if (!silent) toast('已退出登录');
  }

  /* ---------------------------------------------------------------- 认证 */
  function bindAuth() {
    $all('.auth-tab').forEach(function (tab) {
      tab.addEventListener('click', function () {
        var mode = tab.getAttribute('data-auth-tab');
        $all('.auth-tab').forEach(function (t) { t.classList.toggle('active', t === tab); });
        $('#form-login').classList.toggle('hidden', mode !== 'login');
        $('#form-register').classList.toggle('hidden', mode !== 'register');
      });
    });

    $('#form-login').addEventListener('submit', function (e) {
      e.preventDefault();
      var email = $('#login-email').value.trim();
      var password = $('#login-password').value;
      withLoading($('#btn-login'), api('/api/auth/login', {
        method: 'POST', body: { email: email, password: password }
      })).then(function (data) {
        saveSession(data);
        showApp();
        switchView('dashboard');
        toast('登录成功，欢迎回来', 'ok');
      }).catch(function (err) { toast(err.message, 'error'); });
    });

    $('#form-register').addEventListener('submit', function (e) {
      e.preventDefault();
      var payload = {
        tenant_name: $('#reg-tenant').value.trim(),
        email: $('#reg-email').value.trim(),
        password: $('#reg-password').value
      };
      withLoading($('#btn-register'), api('/api/auth/register', {
        method: 'POST', body: payload
      })).then(function (data) {
        saveSession(data);
        showApp();
        switchView('settings');
        toast('企业创建成功，请先配置 BYOK 密钥', 'ok');
      }).catch(function (err) { toast(err.message, 'error'); });
    });

    $('#btn-logout').addEventListener('click', function () { logout(false); });
  }

  /* ------------------------------------------------------------ 控制台 */
  function loadDashboard() {
    var status = $('#filter-status').value;
    loadQuota();
    loadUsage();

    api('/api/tenants/credentials').then(function (cred) {
      var ok = cred.llm_configured && cred.tavily_configured;
      $('#stat-keys').textContent = ok ? '已配置' : '未配置';
      $('#stat-keys-note').textContent = ok
        ? ('模型 ' + (cred.llm_api_key_hint || '—') + ' · 搜索 ' + (cred.tavily_api_key_hint || '—'))
        : '请到「租户设置」填写密钥';
    }).catch(function () {});

    api('/api/tasks?limit=50' + (status ? ('&status=' + encodeURIComponent(status)) : ''))
      .then(renderTaskList)
      .catch(function (err) { toast(err.message, 'error'); });
  }

  function loadQuota() {
    api('/api/tenants/quota').then(function (q) {
      $('#stat-running').textContent = q.concurrent_running;
      $('#stat-running-note').textContent = '并发上限 ' + q.concurrent_limit;
      $('#stat-running-bar').style.width = pct(q.concurrent_running, q.concurrent_limit);
      $('#stat-today').textContent = q.tasks_today;
      $('#stat-today-note').textContent = '每日上限 ' + q.daily_limit;
      $('#stat-today-bar').style.width = pct(q.tasks_today, q.daily_limit);
    }).catch(function () {});
  }

  function loadUsage() {
    api('/api/tenants/usage').then(function (u) {
      $('#stat-tokens').textContent = fmtNum(u.total_tokens);
      $('#stat-calls').textContent = '调用 ' + u.total_calls + ' 次';
    }).catch(function () {});
  }

  function pct(a, b) {
    if (!b) return '0%';
    return Math.min(100, Math.round((a / b) * 100)) + '%';
  }

  function renderTaskList(tasks) {
    var box = $('#task-list');
    if (!tasks || !tasks.length) {
      box.innerHTML = '<div class="empty">还没有调研任务，点击右上角「新建调研」开始。</div>';
      return;
    }
    box.innerHTML = tasks.map(function (t) {
      var cls = STATUS_CLASS[t.status] || 'pending';
      return '' +
        '<div class="task-row" data-task-id="' + t.id + '">' +
          '<div>' +
            '<div class="task-goal">' + esc(t.goal) + '</div>' +
            '<div class="task-meta">创建于 ' + fmtTime(t.created_at) + '</div>' +
          '</div>' +
          '<div><span class="badge ' + cls + '">' + (STATUS_TEXT[t.status] || t.status) + '</span></div>' +
          '<div class="task-meta">' + (t.stats ? ('检索 ' + (t.stats.searches || 0) + ' 次 · 发现 ' + (t.stats.notes || 0) + ' 条') : '—') + '</div>' +
          '<div style="text-align:right">' +
            (t.has_report ? '<span class="badge succeeded">有报告</span>' : '<span class="muted" style="font-size:11.5px">无报告</span>') +
          '</div>' +
        '</div>';
    }).join('');

    $all('.task-row', box).forEach(function (row) {
      row.addEventListener('click', function () { openTask(row.getAttribute('data-task-id')); });
    });
  }

  function openTask(taskId) {
    api('/api/tasks/' + taskId).then(function (task) {
      state.currentTask = task;
      if (task.status === 'pending_clarify') return renderClarify(task);
      return openProgress(task);
    }).catch(function (err) { toast(err.message, 'error'); });
  }

  /* ------------------------------------------------------------ 新建调研 */
  function bindNew() {
    $('#btn-new-example').addEventListener('click', function () {
      $('#new-goal').value = '调研 2026 年国内大模型推理框架的工程化落地现状，重点对比 vLLM、SGLang、TensorRT-LLM 在吞吐、显存占用、部署复杂度上的差异，并给出面向中小团队的选型建议。';
    });

    $('#btn-create-task').addEventListener('click', function () {
      var goal = $('#new-goal').value.trim();
      if (goal.length < 4) { toast('请填写更具体的调研目标', 'error'); return; }
      withLoading($('#btn-create-task'), api('/api/tasks', {
        method: 'POST',
        body: { goal: goal, skip_clarify: $('#new-skip-clarify').checked }
      })).then(function (task) {
        state.currentTask = task;
        if (task.status === 'pending_clarify') {
          renderClarify(task);
          toast('目标信息不足，请补充以下几点', 'ok');
        } else {
          openProgress(task);
          toast('任务已提交，正在排队', 'ok');
        }
      }).catch(function (err) { toast(err.message, 'error'); });
    });
  }

  /* ------------------------------------------------------------ 澄清对话 */
  function renderClarify(task) {
    switchView('clarify');
    $('#clarify-goal').textContent = task.goal;
    var chat = $('#clarify-chat');
    var questions = task.clarify_questions || [];

    chat.innerHTML = '' +
      '<div class="bubble system">' +
        '<div class="avatar">AI</div>' +
        '<div class="body">' +
          '<div class="q">为了让调研更精准，我需要你补充以下信息：</div>' +
          '<div class="why">不回答也可以，直接提交将按原目标开跑。</div>' +
        '</div>' +
      '</div>' +
      questions.map(function (q, i) {
        return '' +
          '<div class="bubble system answer-item" style="align-items:stretch">' +
            '<div class="avatar">' + (i + 1) + '</div>' +
            '<div class="body" style="flex:1;max-width:none">' +
              '<div class="q">' + esc(q.question) + '</div>' +
              (q.why ? '<div class="why">' + esc(q.why) + '</div>' : '') +
              '<input class="input" data-answer-idx="' + i + '" placeholder="请输入你的回答（可留空）" />' +
            '</div>' +
          '</div>';
      }).join('');

    $('#btn-clarify-submit').onclick = function () { submitClarify(true); };
    $('#btn-clarify-skip').onclick = function () { submitClarify(false); };
  }

  function submitClarify(useAnswers) {
    var task = state.currentTask;
    if (!task) return;
    var questions = task.clarify_questions || [];
    var answers = questions.map(function (q, i) {
      var input = $('[data-answer-idx="' + i + '"]');
      return { question: q.question, answer: useAnswers && input ? input.value.trim() : '' };
    });

    var btn = useAnswers ? $('#btn-clarify-submit') : $('#btn-clarify-skip');
    withLoading(btn, api('/api/tasks/' + task.id + '/clarify', {
      method: 'POST', body: { answers: answers }
    })).then(function (updated) {
      state.currentTask = updated;
      openProgress(updated);
      toast('已提交，任务开始运行', 'ok');
    }).catch(function (err) { toast(err.message, 'error'); });
  }

  /* ------------------------------------------------------------ 进行中 */
  function openProgress(task) {
    switchView('progress');
    state.currentTask = task;
    state.lastSeq = 0;
    state.findings = 0;
    state.logCount = 0;
    state.seenStages = {};
    state.lastStage = '';

    $('#progress-goal').textContent = task.goal;
    $('#log-stream').innerHTML = '';
    $('#finding-list').innerHTML = '<p class="muted" style="font-size:12.5px;margin:0">检索出的有效发现会实时出现在这里…</p>';
    $('#log-count').textContent = '0 条事件';
    $('#finding-count').textContent = '0 条';
    setBadge(task.status);
    renderTimeline();

    if (isTerminal(task.status)) {
      finishTask(task);
      return;
    }
    startStream(task.id);
  }

  function isTerminal(status) {
    return status === 'succeeded' || status === 'failed' || status === 'cancelled';
  }

  function setBadge(status) {
    var badge = $('#progress-status-badge');
    badge.className = 'badge ' + (STATUS_CLASS[status] || 'pending');
    badge.textContent = STATUS_TEXT[status] || status;
    badge.classList.toggle('hidden', status === 'succeeded');
    $('#btn-cancel-task').classList.toggle('hidden', isTerminal(status));
  }

  function renderTimeline() {
    $('#timeline').innerHTML = STAGES.map(function (s) {
      var cls = 'tl-item';
      if (state.seenStages[s.key]) {
        cls += (state.lastStage === s.key && !isTerminal(state.currentTask.status)) ? ' active' : ' done';
      } else {
        cls += ' pending';
      }
      return '' +
        '<div class="' + cls + '" data-stage="' + s.key + '">' +
          '<div class="tl-dot">' + (state.seenStages[s.key] ? '✓' : '') + '</div>' +
          '<div>' +
            '<div class="tl-label">' + s.label + '</div>' +
            '<div class="tl-note">' + s.note + '</div>' +
          '</div>' +
        '</div>';
    }).join('');
  }

  function startStream(taskId) {
    stopStream();
    if (typeof EventSource === 'undefined') { startPolling(taskId); return; }

    var url = API_BASE + '/api/tasks/' + taskId + '/stream?token=' + encodeURIComponent(state.token);
    var es = new EventSource(url);
    state.eventSource = es;

    es.addEventListener('progress', function (ev) {
      try { handleEvent(JSON.parse(ev.data)); } catch (e) { /* 忽略坏包 */ }
    });
    es.onerror = function () {
      // 连接中断：任务若仍在跑，降级为轮询，保证进度不丢
      es.close();
      state.eventSource = null;
      if (state.currentTask && !isTerminal(state.currentTask.status)) startPolling(taskId);
    };
  }

  function stopStream() {
    if (state.eventSource) { state.eventSource.close(); state.eventSource = null; }
    if (state.pollTimer) { clearInterval(state.pollTimer); state.pollTimer = null; }
  }

  function startPolling(taskId) {
    if (state.pollTimer) return;
    var tick = function () {
      api('/api/tasks/' + taskId + '/events?after_seq=' + state.lastSeq)
        .then(function (events) { events.forEach(handleEvent); })
        .catch(function () {});
      api('/api/tasks/' + taskId).then(function (task) {
        state.currentTask = task;
        setBadge(task.status);
        if (isTerminal(task.status)) { stopStream(); finishTask(task); }
      }).catch(function () {});
    };
    tick();
    state.pollTimer = setInterval(tick, 2500);
  }

  function handleEvent(ev) {
    if (!ev || typeof ev.seq !== 'number') return;
    if (ev.seq <= state.lastSeq) return;
    state.lastSeq = ev.seq;

    if (ev.stage === 'finding') { appendFinding(ev.payload); return; }
    if (ev.stage === 'eof') return;

    if (STAGES.some(function (s) { return s.key === ev.stage; })) {
      state.seenStages[ev.stage] = true;
      state.lastStage = ev.stage;
      renderTimeline();
    }
    appendLog(ev);

    if (ev.stage === 'done' || ev.stage === 'error' || ev.stage === 'cancelled') {
      stopStream();
      api('/api/tasks/' + state.currentTask.id).then(function (task) {
        state.currentTask = task;
        setBadge(task.status);
        renderTimeline();
        finishTask(task);
      }).catch(function () {});
    }
  }

  function appendLog(ev) {
    var box = $('#log-stream');
    var line = document.createElement('div');
    line.className = 'log-line' + (ev.level === 'error' ? ' level-error' : '') +
      (ev.stage === 'done' ? ' stage-done' : '');
    line.innerHTML =
      '<span class="t">' + fmtTime(ev.ts || new Date().toISOString()).split(' ')[1] + '</span>' +
      '<span class="s">' + esc(ev.stage || '-') + '</span>' +
      '<span class="m">' + esc(ev.message || '') + '</span>';
    box.appendChild(line);
    box.scrollTop = box.scrollHeight;
    state.logCount += 1;
    $('#log-count').textContent = state.logCount + ' 条事件';
  }

  function appendFinding(payload) {
    var notes = (payload && payload.notes) || [];
    if (!notes.length) return;
    var box = $('#finding-list');
    if (state.findings === 0) box.innerHTML = '';

    notes.forEach(function (n) {
      var card = document.createElement('div');
      card.className = 'finding';
      var sources = (n.sources || []).slice(0, 4).map(function (s) {
        var tier = s.source_tier ? ('T' + s.source_tier + ' ') : '';
        return '<a href="' + esc(s.url) + '" target="_blank" rel="noopener">' + tier + esc(s.title || s.url) + '</a>';
      }).join('');
      card.innerHTML =
        '<div class="fact">' + esc(n.fact) + '</div>' +
        (sources ? '<div class="src">' + sources + '</div>' : '');
      box.appendChild(card);
      state.findings += 1;
    });
    box.scrollTop = box.scrollHeight;
    $('#finding-count').textContent = state.findings + ' 条';
  }

  function finishTask(task) {
    state.currentTask = task;
    setBadge(task.status);
    renderTimeline();

    if (task.status === 'succeeded' && task.has_report) {
      setTimeout(function () { loadReport(task.id); }, 500);
    } else if (task.status === 'failed') {
      toast('任务失败：' + (task.error || '未知错误'), 'error');
    } else if (task.status === 'cancelled') {
      toast('任务已取消');
    } else if (task.status === 'pending_clarify') {
      renderClarify(task);
    }
  }

  /* ------------------------------------------------------------ 报告 */
  function loadReport(taskId) {
    api('/api/tasks/' + taskId + '/report').then(function (r) {
      state.currentTask = state.currentTask || {};
      $('#report-goal').textContent = r.goal;
      $('#report-body').innerHTML = renderMarkdown(r.markdown || '');
      switchView('report');
      toast('报告已生成', 'ok');
    }).catch(function (err) { toast(err.message, 'error'); });
  }

  function renderMarkdown(md) {
    var html;
    if (window.marked && typeof window.marked.parse === 'function') {
      html = window.marked.parse(md);
    } else {
      html = '<pre>' + esc(md) + '</pre>';
    }
    // 轻量净化：移除脚本/内联事件，避免报告里的可疑 HTML 被执行
    return html
      .replace(/<script[\s\S]*?<\/script>/gi, '')
      .replace(/<iframe[\s\S]*?<\/iframe>/gi, '')
      .replace(/\son\w+\s*=\s*(".*?"|'.*?'|[^\s>]+)/gi, '');
  }

  function bindReport() {
    $('#btn-report-download').addEventListener('click', function () {
      var task = state.currentTask;
      if (!task) return;
      api('/api/tasks/' + task.id + '/report').then(function (r) {
        var blob = new Blob([r.markdown || ''], { type: 'text/markdown;charset=utf-8' });
        var a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = '调研报告-' + (r.goal || task.id).slice(0, 30).replace(/[\\/:*?"<>|]/g, '') + '.md';
        a.click();
        URL.revokeObjectURL(a.href);
      }).catch(function (err) { toast(err.message, 'error'); });
    });

    $('#btn-report-copy').addEventListener('click', function () {
      var task = state.currentTask;
      if (!task) return;
      api('/api/tasks/' + task.id + '/report').then(function (r) {
        navigator.clipboard.writeText(r.markdown || '')
          .then(function () { toast('已复制 Markdown 到剪贴板', 'ok'); })
          .catch(function () { toast('复制失败，请手动选择', 'error'); });
      }).catch(function (err) { toast(err.message, 'error'); });
    });
  }

  /* ------------------------------------------------------------ 租户设置 */
  function loadSettings() {
    api('/api/tenants/credentials').then(function (cred) {
      $('#set-provider').value = cred.provider || 'deepseek';
      $('#set-model').value = cred.llm_model || '';
      $('#set-base-url').value = cred.llm_base_url || '';
      $('#set-llm-hint').textContent = '当前：' + (cred.llm_api_key_hint || '未配置');
      $('#set-tavily-hint').textContent = '当前：' + (cred.tavily_api_key_hint || '未配置');
      var ok = cred.llm_configured && cred.tavily_configured;
      var badge = $('#keys-badge');
      badge.className = 'badge ' + (ok ? 'succeeded' : 'pending');
      badge.textContent = ok ? '已配置' : '未配置';
    }).catch(function (err) { toast(err.message, 'error'); });

    api('/api/tenants/usage').then(function (u) {
      $('#set-usage-calls').textContent = u.total_calls;
      $('#set-usage-in').textContent = fmtNum(u.total_input_tokens);
      $('#set-usage-out').textContent = fmtNum(u.total_output_tokens);
      $('#set-usage-total').textContent = fmtNum(u.total_tokens);
    }).catch(function () {});

    api('/api/tenants/quota').then(function (q) {
      $('#set-quota-conc').textContent = q.concurrent_running + ' / ' + q.concurrent_limit;
      $('#set-quota-daily').textContent = q.tasks_today + ' / ' + q.daily_limit;
    }).catch(function () {});

    loadMembers();
  }

  function loadMembers() {
    api('/api/tenants/members').then(function (members) {
      $('#member-list').innerHTML = members.map(function (m) {
        return '' +
          '<div class="kv">' +
            '<span class="k">' + esc(m.email) + '</span>' +
            '<span class="v">' + (m.role === 'owner' ? '管理员' : '成员') +
              (m.is_active ? '' : ' · 已停用') + '</span>' +
          '</div>';
      }).join('') || '<p class="muted" style="font-size:12.5px;margin:0">暂无成员</p>';
    }).catch(function () {});
  }

  function bindSettings() {
    $('#btn-keys-save').addEventListener('click', function () {
      var body = {
        provider: $('#set-provider').value,
        llm_model: $('#set-model').value.trim(),
        llm_base_url: $('#set-base-url').value.trim()
      };
      var llmKey = $('#set-llm-key').value.trim();
      var tvKey = $('#set-tavily-key').value.trim();
      if (llmKey) body.llm_api_key = llmKey;
      if (tvKey) body.tavily_api_key = tvKey;

      withLoading($('#btn-keys-save'), api('/api/tenants/credentials', {
        method: 'PUT', body: body
      })).then(function () {
        $('#set-llm-key').value = '';
        $('#set-tavily-key').value = '';
        toast('密钥已加密保存', 'ok');
        loadSettings();
      }).catch(function (err) { toast(err.message, 'error'); });
    });

    $('#btn-keys-clear').addEventListener('click', function () {
      if (!confirm('确定清空 BYOK 密钥？清空后将无法创建调研任务。')) return;
      withLoading($('#btn-keys-clear'), api('/api/tenants/credentials', { method: 'DELETE' }))
        .then(function () { toast('已清空密钥'); loadSettings(); })
        .catch(function (err) { toast(err.message, 'error'); });
    });

    $('#btn-add-member').addEventListener('click', function () {
      var email = prompt('成员邮箱：');
      if (!email) return;
      var password = prompt('初始密码（至少 8 位）：');
      if (!password) return;
      api('/api/tenants/members', {
        method: 'POST', body: { email: email.trim(), password: password, role: 'member' }
      }).then(function () { toast('成员已添加', 'ok'); loadMembers(); })
        .catch(function (err) { toast(err.message, 'error'); });
    });
  }

  /* ------------------------------------------------------------ 取消任务 */
  function bindCancel() {
    $('#btn-cancel-task').addEventListener('click', function () {
      var task = state.currentTask;
      if (!task) return;
      if (!confirm('确定取消该任务？')) return;
      withLoading($('#btn-cancel-task'), api('/api/tasks/' + task.id + '/cancel', { method: 'POST' }))
        .then(function (updated) {
          state.currentTask = updated;
          stopStream();
          setBadge(updated.status);
          renderTimeline();
          toast('任务已取消');
        })
        .catch(function (err) { toast(err.message, 'error'); });
    });
  }

  /* ------------------------------------------------------------ 启动 */
  function bindGlobal() {
    $all('[data-nav]').forEach(function (el) {
      el.addEventListener('click', function () { switchView(el.getAttribute('data-nav')); });
    });
    $('#btn-refresh').addEventListener('click', function () { loadDashboard(); toast('已刷新'); });
    $('#filter-status').addEventListener('change', loadDashboard);
    $('#btn-menu').addEventListener('click', function () { $('#sidebar').classList.toggle('open'); });
  }

  function boot() {
    bindAuth();
    bindGlobal();
    bindNew();
    bindReport();
    bindSettings();
    bindCancel();

    var savedProfile = localStorage.getItem(PROFILE_KEY);
    if (state.token && savedProfile) {
      try { state.profile = JSON.parse(savedProfile); } catch (e) { state.profile = null; }
      // 校验令牌是否仍有效
      api('/api/auth/me').then(function (me) {
        saveSession(me);
        showApp();
        switchView('dashboard');
      }).catch(function () { logout(true); });
    } else {
      showAuth();
    }
  }

  document.addEventListener('DOMContentLoaded', boot);
})();
