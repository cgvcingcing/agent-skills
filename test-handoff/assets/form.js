

(function () {
  'use strict';
  const schema = JSON.parse(document.getElementById('handoff-schema').textContent);
  const seed = JSON.parse(document.getElementById('handoff-data').textContent);
  const readOnly = document.documentElement.dataset.readOnly === 'true';
  const copy = value => JSON.parse(JSON.stringify(value));
  const makeId = () => window.crypto && crypto.randomUUID ? crypto.randomUUID() : Date.now().toString(36) + Math.random().toString(36).slice(2);
  const storageKey = 'test-handoff-form-v1:' + seed.documentId + (readOnly ? ':read-only' : '');
  const sectionViewKey = storageKey + ':sections';
  const rangeViewKey = storageKey + ':ranges';
  const recordViewKey = storageKey + ':records';
  const recordSpecs = {
    config: {
      title:'key',
      panels:[['purpose','适用场景','reference'],['reference','参考值','reference'],['actual','本环境实际值','info'],['operation','位置、生效与恢复','reference']],
      markers:[['actual','实际值已填','实际值待填','info']]
    },
    services: {
      title:'name',
      panels:[['role','负责内容','reference'],['deployment','部署与访问','reference'],['entry','页面与接口入口','info'],['owner','对接人','reference']],
      markers:[['deployment','部署信息已填','部署信息待填','info'],['owner','对接人已填','对接人待填','info']]
    },
    logs: {
      title:'scene',
      panels:[['keywords','日志关键词','reference'],['location','服务与日志位置','reference'],['check','查到后核对什么','success'],['query','检索命令与查询说明','info']],
      markers:[['location','日志位置已填','日志位置待填','info'],['query','查询已填','查询待填','info']]
    },
    database: {
      title:'object',
      panels:[['storage','库表与存储位置','reference'],['lookup','关联字段与查询条件','reference'],['check','要核对的结果','success'],['query','查询示例','info']],
      markers:[['storage','库表已填','库表待填','info'],['query','查询已填','查询待填','info']]
    },
    samples: {
      title:'scene',
      panels:[['example','业务样例','reference'],['expected','预期结果','success'],['actual','开发准备的数据与步骤','info']],
      markers:[['expected','预期结果已填','预期待填','success'],['actual','开发数据已填','开发数据待填','info']]
    }
  };
  const recordTables = Object.keys(recordSpecs);
  const statusNode = document.getElementById('save-status');
  const toastNode = document.getElementById('toast');
  const sectionStates = ['待补充', '已确认', '不涉及'];
  let state = copy(seed);
  let saveTimer = null;
  let toastTimer = null;
  let lastDeletion = null;
  let draftAvailable = true;
  let restored = false;
  let lastEmptyField = null;
  const collapsedSections = new Set(Array.from(document.querySelectorAll('.form-section[data-collapsed="true"]'), section => section.dataset.section));
  try {
    const savedView = JSON.parse(localStorage.getItem(sectionViewKey));
    if (Array.isArray(savedView)) {
      collapsedSections.clear();
      savedView.filter(name => Object.keys(schema).includes(name)).forEach(name => collapsedSections.add(name));
    }
  } catch (error) {
    // Collapsing still works when browser preferences are unavailable.
  }
  const collapsedRanges = new Set(Array.from(document.querySelectorAll('.scope-group[data-collapsed="true"]'), group => group.dataset.rangeId).filter(Boolean));
  try {
    const savedRanges = JSON.parse(localStorage.getItem(rangeViewKey));
    if (Array.isArray(savedRanges)) {
      collapsedRanges.clear();
      savedRanges.filter(id => typeof id === 'string').forEach(id => collapsedRanges.add(id));
    }
  } catch (error) {}

  const collapsedRecords = Object.fromEntries(recordTables.map(name => [name, new Set(
    Array.from(document.querySelectorAll('.record-group[data-collapsed="true"]'))
      .filter(group => group.dataset.recordTable === name).map(group => group.dataset.recordId)
  )]));
  try {
    const savedRecords = JSON.parse(localStorage.getItem(recordViewKey));
    if (savedRecords && typeof savedRecords === 'object') {
      for (const name of recordTables) if (Array.isArray(savedRecords[name])) {
        collapsedRecords[name] = new Set(savedRecords[name].filter(id => typeof id === 'string'));
      }
    }
  } catch (error) {}

  document.querySelectorAll('.rich-field').forEach(wrapper => {
    const field = wrapper.querySelector('.field');
    if (field) wrapper.replaceWith(field);
  });
  document.querySelectorAll('.handoff-table').forEach(table => {
    if (!table.closest('.tw')) {
      const wrapper = document.createElement('div');
      wrapper.className = 'tw';
      table.replaceWith(wrapper);
      wrapper.appendChild(table);
    }
  });

  function node(tag, className, text) {
    const item = document.createElement(tag);
    if (className) item.className = className;
    if (text !== undefined) item.textContent = text;
    return item;
  }

  function parts(value) {
    return value.split(/[\n；。]+/).map(item => item.trim()).filter(Boolean);
  }

  function presentationFor(name, key) {
    if (name === 'scope') return {range:'heading', module:'modules', scenarios:'scenarios'}[key] || 'record-list';
    if (name === 'config') return key === 'key' ? 'config' : 'record-list';
    if (name === 'services') return key === 'name' ? 'heading' : key === 'entry' ? 'record-command' : 'record-list';
    if (name === 'logs') return key === 'keywords' ? 'keywords' : key === 'scene' ? 'heading' : key === 'query' ? 'record-command' : 'record-list';
    if (name === 'database') return key === 'object' ? 'heading' : key === 'query' ? 'record-query' : key === 'check' ? 'record-checks' : 'record-list';
    if (name === 'samples') return key === 'scene' ? 'heading' : key === 'expected' ? 'record-result' : key === 'actual' ? 'record-steps' : 'record-list';
    return 'record-list';
  }

  function addEmphasis(container, text, marks) {
    const allowed = new Set(['critical', 'warning', 'info', 'success']);
    const entries = Array.isArray(marks) ? marks.filter(item => item && typeof item.text === 'string' && item.text && allowed.has(item.tone)) : [];
    let cursor = 0;
    while (cursor < text.length) {
      let selected = null;
      let offset = text.length;
      for (const item of entries) {
        const found = text.indexOf(item.text, cursor);
        if (found >= 0 && found < offset) { offset = found; selected = item; }
      }
      container.appendChild(document.createTextNode(text.slice(cursor, offset)));
      if (!selected) break;
      container.appendChild(node('strong', 'emphasis tone-' + selected.tone, selected.text));
      cursor = offset + selected.text.length;
    }
  }

  function priorityClass(value) {
    return value === 'P0' || value === '含 P0' ? 'p0' : value === 'P1' ? 'p1' : value === 'P2' ? 'p2' : 'pending';
  }

  function statementEnd(text, start) {
    let quote = '';
    for (let index = start; index < text.length; index++) {
      const char = text[index];
      if (quote) {
        if (char === '\\') { index++; continue; }
        if (char === quote) {
          if (text[index + 1] === quote) index++;
          else quote = '';
        }
      } else if (char === "'" || char === '"' || char === '`') quote = char;
      else if (char === ';') return index + 1;
    }
    return -1;
  }

  function recordSegments(value, query) {
    const segments = [];
    function prose(text) {
      for (const part of text.match(/[^\n；。]+[；。]?/g) || []) {
        if (part.trim()) segments.push({kind:'text', text:part.trim()});
      }
    }
    let rest = value;
    while (rest) {
      const match = rest.match(/^[\t ]*(?:kubectl|curl|rg|grep|jq|ssh|tail|cat)\s+|\b(?:SELECT|WITH|EXPLAIN|SHOW|DESCRIBE)\s+|^[\t ]*(?:const|let|var)\s+|^[\t ]*if\s*\(|\b(?:GET|POST|PUT|DELETE|PATCH)\s+(?:https?:\/\/|\/)/im);
      if (!match) { prose(rest); break; }
      const start = match.index;
      const http = /^(?:GET|POST|PUT|DELETE|PATCH)\s/i.test(match[0]);
      const shell = /^[\t ]*(?:kubectl|curl|rg|grep|jq|ssh|tail|cat)\s/i.test(match[0]);
      let end = http ? rest.slice(start).search(/[\n；。]/) : statementEnd(rest, start);
      if (shell) {
        end = rest.indexOf('\n', start);
        while (end >= 0 && /\\\s*$/.test(rest.slice(start, end))) end = rest.indexOf('\n', end + 1);
        if (end < 0) end = rest.length;
      } else if (http) end = end < 0 ? rest.length : start + end;
      else if (end < 0) {
        const lineStart = rest.lastIndexOf('\n', start - 1) + 1;
        if (!query || rest.slice(lineStart, start).trim()) { prose(rest); break; }
        const lineEnd = rest.indexOf('\n', start);
        end = lineEnd < 0 ? rest.length : lineEnd;
      }
      prose(rest.slice(0, start));
      segments.push({kind:'code', text:rest.slice(start, end).trim()});
      rest = rest.slice(end);
    }
    return segments;
  }

  function recordText(container, text, marks) {
    if (marks && marks.length) { addEmphasis(container, text, marks); return; }
    const tokens = /(\d+(?:\.\d+)?\s*(?:元|件|%))|\b[A-Za-z_][A-Za-z\d_]*(?:[._-][A-Za-z\d_]+)+\b/g;
    let cursor = 0;
    let match;
    while ((match = tokens.exec(text))) {
      container.appendChild(document.createTextNode(text.slice(cursor, match.index)));
      container.appendChild(node(match[1] ? 'strong' : 'code', match[1] ? 'amount' : 'record-token', match[0]));
      cursor = match.index + match[0].length;
    }
    container.appendChild(document.createTextNode(text.slice(cursor)));
  }

  function paintRecordContent(container, value, kind, display) {
    const list = node('ol', 'record-points');
    const segments = recordSegments(value, kind === 'record-query' || kind === 'record-command');
    const entries = [];
    for (let index = 0; index < segments.length; index++) {
      const segment = segments[index];
      if (segment.kind === 'text' && segment.text.length <= 80 && /[：:]$/.test(segment.text) && segments[index + 1] && segments[index + 1].kind === 'code') {
        entries.push({...segments[++index], caption:segment.text});
      } else entries.push(segment);
    }
    entries.forEach((segment, index) => {
      const item = node('li', 'record-point' + (segment.kind === 'code' ? ' record-code-point' : ''));
      const detail = Array.isArray(display.items) ? display.items[index] || {} : {};
      item.appendChild(node('span', 'record-point-index', String(index + 1).padStart(2, '0')));
      const content = node('div', 'record-point-copy');
      if (detail.label) content.appendChild(node('b', 'record-point-label', detail.label));
      if (segment.caption) content.appendChild(node('b', 'record-point-label', segment.caption));
      if (segment.kind === 'code') {
        const pre = node('pre', 'record-code');
        pre.appendChild(node('code', '', segment.text));
        content.appendChild(pre);
      } else recordText(content, segment.text, detail.emphasis || display.emphasis);
      item.appendChild(content);
      list.appendChild(item);
    });
    container.appendChild(list);
  }

  function paintPreview(container, value, kind, display) {
    container.replaceChildren();
    if (!value.trim()) return;
    display = display && display.value === value ? display : {};
    if (kind.startsWith('record-')) {
      paintRecordContent(container, value, kind, display);
      return;
    }
    if (kind === 'modules') {
      const sections = value.split(/[\n；]+/).map(item => item.trim()).filter(Boolean);
      let index = 0;
      sections.forEach(section => {
        const colon = section.indexOf('：');
        let content = section;
        if (colon > 0 && colon < 16) {
          container.appendChild(node('div', 'module-location', section.slice(0, colon)));
          content = section.slice(colon + 1);
        }
        const group = node('ol', 'record-points module-list');
        content.split(/[、，]+/).map(item => item.trim()).filter(Boolean).forEach(item => {
          const point = node('li', 'record-point');
          point.append(node('span', 'record-point-index', String(++index).padStart(2, '0')), node('div', 'record-point-copy', item));
          group.appendChild(point);
        });
        container.appendChild(group);
      });
      return;
    }
    if (kind === 'config') {
      let previousPrefix = '';
      value.split('\n').filter(line => line.trim()).forEach(line => {
        const trimmed = line.trim();
        const dot = trimmed.lastIndexOf('.');
        const prefix = dot > 0 ? trimmed.slice(0, dot + 1) : '';
        if (prefix && prefix !== previousPrefix) container.appendChild(node('div', 'config-namespace', prefix));
        container.appendChild(node('code', 'config-key', dot > 0 ? trimmed.slice(dot + 1) : trimmed));
        previousPrefix = prefix;
      });
      return;
    }
    if (kind === 'endpoints') {
      value.split('\n').filter(line => line.trim()).forEach(line => {
        const match = line.match(/^(GET|POST|PUT|DELETE|PATCH)\s+(.+)$/);
        if (match) {
          const endpoint = node('div', 'endpoint');
          endpoint.appendChild(node('span', 'http-method method-' + match[1].toLowerCase(), match[1]));
          endpoint.appendChild(node('code', 'endpoint-path', match[2]));
          container.appendChild(endpoint);
        } else container.appendChild(node('p', 'endpoint-note', line));
      });
      return;
    }
    if (kind === 'keywords' || kind === 'query') {
      value.split('\n').filter(line => line.trim()).forEach(line => container.appendChild(node('code', 'keyword-line', line)));
      return;
    }
    if (kind === 'heading' || kind === 'service') {
      container.appendChild(node('div', kind === 'service' ? 'service-name' : 'cell-heading', value));
      return;
    }
    if (kind === 'scenarios') {
      const list = node('ol', 'scenario-list');
      parts(value).forEach((text, index) => {
        const detail = Array.isArray(display.items) ? display.items[index] || {} : {};
        const item = node('li', 'scenario-item');
        item.appendChild(node('span', 'scenario-number', String(index + 1).padStart(2, '0')));
        const content = node('div', 'scenario-copy');
        if (detail.label || detail.priority) {
          const heading = node('div', 'scenario-heading');
          if (detail.label) heading.appendChild(node('b', 'scenario-label', detail.label));
          if (['P0', 'P1', 'P2'].includes(detail.priority)) heading.appendChild(node('span', 'mini-priority priority-' + priorityClass(detail.priority), detail.priority));
          content.appendChild(heading);
        }
        const line = node('span', 'scenario-text');
        addEmphasis(line, text, detail.emphasis);
        content.appendChild(line);
        item.appendChild(content);
        list.appendChild(item);
      });
      container.appendChild(list);
      return;
    }
    if (kind === 'text') {
      value.split('\n').forEach(text => container.appendChild(node('p', 'plain-line', text)));
      return;
    }
    paintRecordContent(container, value, 'record-list', display);
  }

  function attachRichField(field, kind, display) {
    if (field._richWrapper) return field._richWrapper;
    const wrapper = node('div', 'rich-field kind-' + kind);
    const preview = node('div', 'field-preview');
    preview.tabIndex = 0;
    preview.setAttribute('role', 'button');
    preview.setAttribute('aria-label', '编辑' + field.getAttribute('aria-label'));
    preview.title = '点击编辑';
    const edit = node('button', 'edit-field', '编辑');
    edit.type = 'button';
    edit.setAttribute('aria-label', '编辑' + field.getAttribute('aria-label'));
    const tools = node('div', 'edit-tools');
    tools.appendChild(node('span', 'edit-hint', kind === 'modules' ? '模块可用换行或顿号分隔' : '可换行逐条填写'));
    const cancel = node('button', 'cancel-edit', '取消');
    cancel.type = 'button';
    const done = node('button', 'done-edit', '完成');
    done.type = 'button';
    tools.append(cancel, done);
    if (field.parentNode) field.replaceWith(wrapper);
    wrapper.append(preview, edit, field, tools);
    field._richWrapper = wrapper;
    field._richKind = kind;
    field._richDisplay = display;
    field._richPreview = preview;
    let beforeEdit = field.value;
    function open() {
      if (wrapper.classList.contains('editing')) return;
      beforeEdit = field.value;
      wrapper.classList.add('editing');
      resize(field);
      field.focus({preventScroll: true});
    }
    function close() {
      wrapper.classList.remove('editing');
      updateField(field);
    }
    field._openEditor = open;
    edit.addEventListener('click', open);
    preview.addEventListener('click', () => { if (!window.getSelection().toString()) open(); });
    preview.addEventListener('keydown', event => {
      if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); open(); }
    });
    field.addEventListener('focus', () => {
      if (!wrapper.classList.contains('editing')) { beforeEdit = field.value; wrapper.classList.add('editing'); resize(field); }
    });
    done.addEventListener('click', close);
    function cancelEdit() {
      field.value = beforeEdit;
      field.dispatchEvent(new Event('input', {bubbles: true}));
      close();
    }
    cancel.addEventListener('click', cancelEdit);
    field.addEventListener('keydown', event => {
      if (event.key === 'Escape') { event.preventDefault(); cancelEdit(); }
      if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') { event.preventDefault(); close(); }
    });
    wrapper.addEventListener('focusout', () => requestAnimationFrame(() => {
      if (!wrapper.contains(document.activeElement)) close();
    }));
    updateField(field);
    return wrapper;
  }

  function readonlyField(value, kind, display) {
    const wrapper = node('div', 'rich-field readonly-field kind-' + kind);
    const preview = node('div', 'field-preview');
    if (value.trim()) paintPreview(preview, value, kind, display);
    else preview.appendChild(node('span', 'readonly-empty', '未填写'));
    wrapper.appendChild(preview);
    return wrapper;
  }

  function validate(raw) {
    if (!raw || raw.format !== 'test-handoff-form' || raw.version !== 1 || !raw.meta || !raw.tables || !raw.sections || !raw.extras) {
      throw new Error('请选择从这份填写表导出的 JSON 数据文件。');
    }
    const result = copy(seed);
    const seenIds = new Set();
    function text(value) {
      if (typeof value !== 'string' || value.length > 100000) throw new Error('数据中有无法读取的字段，请检查导出文件。');
      return value;
    }
    for (const key of Object.keys(seed.meta)) result.meta[key] = text(raw.meta[key]);
    for (const key of Object.keys(seed.extras)) result.extras[key] = text(raw.extras[key]);
    for (const name of Object.keys(schema)) {
      if (!Array.isArray(raw.tables[name]) || raw.tables[name].length > 500) throw new Error('表格数据格式不正确。');
      result.tables[name] = raw.tables[name].map(source => {
        if (!source || typeof source !== 'object') throw new Error('表格行格式不正确。');
        const base = seed.tables[name].find(item => item._id === source._id ||
          (name === 'scope' && item.range && item.range === source.range));
        const row = {_id: typeof source._id === 'string' && source._id && !seenIds.has(source._id) ? source._id : makeId()};
        seenIds.add(row._id);
        for (const col of schema[name].columns) {
          row[col.key] = text(source[col.key] === undefined && col.optional ?
            base && base[col.key] || (col.kind === 'select' ? col.options[0] : '') : source[col.key]);
          if (col.kind === 'select' && !col.options.includes(row[col.key])) throw new Error('测试范围的选项无法识别。');
        }
        if (source._display || base && base._display) row._display = copy(source._display || base._display);
        return row;
      });
      const section = raw.sections[name];
      if (!section || !sectionStates.includes(section.status)) throw new Error('确认状态无法识别。');
      result.sections[name] = {status: section.status, note: text(section.note)};
    }
    result._presentation = copy(raw._presentation && typeof raw._presentation === 'object' ? raw._presentation : seed._presentation || {});
    return result;
  }

  if (!readOnly) try {
    const rawDraft = localStorage.getItem(storageKey);
    if (rawDraft) {
      state = validate(JSON.parse(rawDraft));
      restored = true;
    }
  } catch (error) {
    draftAvailable = false;
  }

  function showToast(message, undo) {
    clearTimeout(toastTimer);
    toastNode.querySelector('span').textContent = message;
    document.getElementById('undo-delete').hidden = !undo;
    toastNode.hidden = false;
    toastTimer = setTimeout(() => { toastNode.hidden = true; }, undo ? 14000 : 5500);
  }

  function writeDraft() {
    if (readOnly) return;
    clearTimeout(saveTimer);
    try {
      localStorage.setItem(storageKey, JSON.stringify(state));
      draftAvailable = true;
      const time = new Date().toLocaleTimeString('zh-CN', {hour: '2-digit', minute: '2-digit', hour12: false});
      statusNode.textContent = '本机已暂存 ' + time;
    } catch (error) {
      draftAvailable = false;
      statusNode.textContent = '本机暂存不可用，请保存填写版 HTML';
    }
  }

  function changed() {
    if (readOnly) return;
    clearTimeout(saveTimer);
    statusNode.textContent = draftAvailable ? '正在暂存…' : '请保存填写版 HTML';
    saveTimer = setTimeout(writeDraft, 180);
  }

  function resize(field) {
    if (field.tagName !== 'TEXTAREA' || !field.getClientRects().length) return;
    field.style.height = '0px';
    field.style.height = Math.max(45, field.scrollHeight + 3) + 'px';
  }

  function updateSectionSummary(name) {
    const summary = document.querySelector('[data-section-summary="' + name + '"]');
    summary.replaceChildren(node('span', 'section-entry-count', state.tables[name].length + ' 项'));
    const status = node('span', 'heading-status', state.sections[name].status);
    status.dataset.status = state.sections[name].status;
    summary.appendChild(status);
    if (name === 'scope') {
      ['含 P0', 'P0', 'P1', 'P2', '待确认'].forEach(value => {
        const count = state.tables.scope.filter(row => (row.priority || '待确认') === value).length;
        if (count) summary.appendChild(node('span', 'priority-chip priority-' + priorityClass(value), value + ' · ' + count + ' 组'));
      });
    } else {
      const kinds = {
        config:['开测条件', 'warning'], services:['接口与部署', 'info'],
        logs:['检索线索', 'info'], database:['存储与关联', 'info'], samples:['预期结果', 'success']
      };
      const [label, tone] = kinds[name];
      summary.appendChild(node('span', 'heading-kind tone-' + tone, label));
    }
    const notices = state._presentation && state._presentation.notices && state._presentation.notices[name] || [];
    const critical = notices.filter(notice => notice.tone === 'critical').length;
    if (critical) summary.appendChild(node('span', 'heading-kind tone-critical', '关键提示 · ' + critical));
  }

  function applySectionView(name, collapsed) {
    const section = document.querySelector('[data-section="' + name + '"]');
    const toggle = section.querySelector('.section-toggle');
    const body = section.querySelector('.section-body');
    section.dataset.collapsed = String(collapsed);
    toggle.setAttribute('aria-expanded', String(!collapsed));
    toggle.querySelector('.section-toggle-label').textContent = collapsed ? '展开' : '收起';
    body.hidden = collapsed;
    if (!collapsed) body.querySelectorAll('textarea').forEach(resize);
  }

  function updateSectionControls() {
    document.getElementById('expand-all').disabled = collapsedSections.size === 0;
    document.getElementById('collapse-all').disabled = collapsedSections.size === Object.keys(schema).length;
  }

  function saveSectionView() {
    try { localStorage.setItem(sectionViewKey, JSON.stringify(Array.from(collapsedSections))); } catch (error) {}
  }

  function setSectionCollapsed(name, collapsed) {
    if (collapsed) collapsedSections.add(name);
    else collapsedSections.delete(name);
    applySectionView(name, collapsed);
    updateSectionControls();
    saveSectionView();
    requestAnimationFrame(markSection);
  }

  function revealField(field) {
    const section = field.closest('.form-section');
    if (section) setSectionCollapsed(section.dataset.section, false);
    const group = field.closest('.scope-group');
    if (group) setRangeCollapsed(group.dataset.rangeId, false);
    const record = field.closest('.record-group');
    if (record) setRecordCollapsed(record.dataset.recordTable, record.dataset.recordId, false);
  }

  function revealHash(hash, scroll) {
    let target;
    try { target = document.getElementById(decodeURIComponent(hash.slice(1))); } catch (error) { return; }
    if (!target) return;
    const section = target.closest('.form-section');
    if (!section) return;
    revealField(target);
    if (scroll) requestAnimationFrame(() => target.scrollIntoView({block:'start'}));
  }

  function updateField(field) {
    field.classList.toggle('empty', !field.value.trim());
    if (field.tagName === 'SELECT') field.dataset.value = field.value;
    if (field._richWrapper) {
      field._richWrapper.classList.toggle('has-value', !!field.value.trim());
      paintPreview(field._richPreview, field.value, field._richKind, field._richDisplay);
    }
    resize(field);
  }

  function rangeGroup(id) {
    return Array.from(document.querySelectorAll('.scope-group')).find(group => group.dataset.rangeId === id);
  }

  function applyRangeView(id, collapsed) {
    const group = rangeGroup(id);
    if (!group) return;
    group.dataset.collapsed = String(collapsed);
    group.querySelector('.range-toggle').setAttribute('aria-expanded', String(!collapsed));
    group.querySelector('.range-toggle-label').textContent = collapsed ? '展开' : '收起';
    group.querySelectorAll('.range-body').forEach(row => { row.hidden = collapsed; });
    if (!collapsed) group.querySelectorAll('textarea').forEach(resize);
  }

  function updateRangeControls() {
    const count = state.tables.scope.length;
    const collapsed = state.tables.scope.filter(row => collapsedRanges.has(row._id)).length;
    document.getElementById('expand-ranges').disabled = collapsed === 0;
    document.getElementById('collapse-ranges').disabled = count === 0 || collapsed === count;
  }

  function saveRangeView() {
    try { localStorage.setItem(rangeViewKey, JSON.stringify(Array.from(collapsedRanges))); } catch (error) {}
  }

  function setRangeCollapsed(id, collapsed) {
    if (!state.tables.scope.some(row => row._id === id)) return;
    if (collapsed) collapsedRanges.add(id);
    else collapsedRanges.delete(id);
    applyRangeView(id, collapsed);
    updateRangeControls();
    saveRangeView();
    requestAnimationFrame(markSection);
  }

  function updateRangeHeader(row) {
    const group = rangeGroup(row._id);
    if (!group) return;
    group.dataset.priority = priorityClass(row.priority);
    group.querySelector('.range-name').textContent = row.range.trim() || '待填写范围';
    const priority = group.querySelector('.range-priority');
    priority.className = 'range-priority priority-chip priority-' + priorityClass(row.priority);
    priority.textContent = row.priority || '待确认';
    const decision = group.querySelector('.range-decision');
    decision.textContent = row.decision;
    decision.dataset.value = row.decision;
    const handoff = group.querySelector('.range-handoff-state');
    handoff.textContent = row.handoff.trim() ? '开发补充已填' : '开发补充待填';
    handoff.className = 'range-handoff-state heading-kind tone-' + (row.handoff.trim() ? 'info' : 'warning');
  }

  function recordGroup(name, id) {
    return Array.from(document.querySelector('[data-table="' + name + '"]').tBodies)
      .find(group => group.dataset.recordId === id);
  }

  function applyRecordView(name, id, collapsed) {
    const group = recordGroup(name, id);
    if (!group) return;
    group.dataset.collapsed = String(collapsed);
    group.querySelector('.record-toggle').setAttribute('aria-expanded', String(!collapsed));
    group.querySelector('.record-toggle-label').textContent = collapsed ? '展开' : '收起';
    group.querySelector('.record-content').hidden = collapsed;
    if (!collapsed) group.querySelectorAll('textarea').forEach(resize);
  }

  function updateRecordControls(name) {
    const count = state.tables[name].length;
    const collapsed = state.tables[name].filter(row => collapsedRecords[name].has(row._id)).length;
    document.querySelector('[data-record-expand="' + name + '"]').disabled = collapsed === 0;
    document.querySelector('[data-record-collapse="' + name + '"]').disabled = count === 0 || collapsed === count;
  }

  function saveRecordView() {
    try {
      localStorage.setItem(recordViewKey, JSON.stringify(Object.fromEntries(recordTables.map(name => [name, Array.from(collapsedRecords[name])]))));
    } catch (error) {}
  }

  function setRecordCollapsed(name, id, collapsed) {
    if (!recordTables.includes(name) || !state.tables[name].some(row => row._id === id)) return;
    if (collapsed) collapsedRecords[name].add(id);
    else collapsedRecords[name].delete(id);
    applyRecordView(name, id, collapsed);
    updateRecordControls(name);
    saveRecordView();
    requestAnimationFrame(markSection);
  }

  function updateRecordHeader(name, row) {
    const group = recordGroup(name, row._id);
    if (!group) return;
    const title = row[recordSpecs[name].title].trim();
    const prefixNode = group.querySelector('.record-prefix');
    let prefix = '';
    let label = title;
    if (name === 'config' && title) {
      const lines = title.split('\n').map(line => line.trim()).filter(Boolean);
      prefix = lines[0].slice(0, lines[0].lastIndexOf('.') + 1);
      while (prefix && !lines.every(line => line.startsWith(prefix))) prefix = prefix.slice(0, prefix.slice(0, -1).lastIndexOf('.') + 1);
      label = lines.map(line => line.slice(prefix.length)).join(' / ');
    }
    prefixNode.textContent = prefix;
    prefixNode.hidden = !prefix;
    group.querySelector('.record-name').textContent = label || '待填写记录';
    const summary = group.querySelector('.record-summary');
    summary.replaceChildren();
    const tag = row._display && row._display.tag;
    if (tag && ['critical','warning','info','success'].includes(tag.tone)) summary.appendChild(node('span', 'heading-kind tone-' + tag.tone, tag.text));
    for (const [key, filled, empty, tone] of recordSpecs[name].markers) {
      const present = !!row[key].trim();
      summary.appendChild(node('span', 'heading-kind tone-' + (present ? tone : 'warning'), present ? filled : empty));
    }
  }

  function rowField(name, row, key) {
        const col = schema[name].columns.find(item => item.key === key);
        if (readOnly) {
          const field = col.kind === 'select' ? node('span', 'readonly-selection', row[key]) :
            readonlyField(row[key], presentationFor(name, key), row._display && row._display.fields && row._display.fields[key]);
          field.dataset.rowField = name + '.' + row._id + '.' + key;
          field.dataset.value = row[key];
          field.setAttribute('aria-label', schema[name].title + '：' + col.title);
          if (key === 'priority') field.classList.add('priority-chip', 'priority-' + priorityClass(row[key]));
          return field;
        }
        const field = document.createElement(col.kind === 'select' ? 'select' : 'textarea');
        field.className = 'field' + (col.kind === 'select' ? ' decision' : '');
        field.dataset.rowField = name + '.' + row._id + '.' + col.key;
        field.setAttribute('aria-label', schema[name].title + '：' + col.title);
        if (col.kind === 'select') {
          for (const label of col.options) {
            const option = document.createElement('option');
            option.value = option.textContent = label;
            field.appendChild(option);
          }
        } else {
          field.rows = 2;
          field.placeholder = col.hint || '';
        }
        field.value = row[col.key];
        field.addEventListener(col.kind === 'select' ? 'change' : 'input', () => {
          row[col.key] = field.value;
          field.classList.add('dirty');
          updateField(field);
          if (name === 'scope' && key === 'priority') {
            const rowNode = field.closest('.scope-group').querySelector('.scope-row');
            if (rowNode) rowNode.dataset.priority = priorityClass(field.value);
            updatePrioritySummary();
          }
          if (name === 'scope') updateRangeHeader(row);
          if (recordTables.includes(name)) updateRecordHeader(name, row);
          changed();
        });
        updateField(field);
        return col.kind === 'select' ? field : attachRichField(field, presentationFor(name, key), row._display && row._display.fields && row._display.fields[key]);
  }

  function removeButton(name, row, label) {
      const remove = document.createElement('button');
      remove.type = 'button';
      remove.className = 'remove-row';
      remove.textContent = label || '×';
      remove.title = '删除此行';
      remove.setAttribute('aria-label', '删除' + schema[name].title + '中的此行');
      remove.addEventListener('click', () => {
        const index = state.tables[name].findIndex(item => item._id === row._id);
        lastDeletion = {name, index, row: copy(row)};
        state.tables[name].splice(index, 1);
        renderTable(name);
        changed();
        showToast('已删除一行。', true);
      });
      return remove;
  }

  function scopeRows(body) {
    state.tables.scope.forEach((row, index) => {
      const group = index === 0 ? body : node('tbody', 'scope-group');
      group.classList.add('scope-group');
      group.dataset.rangeId = row._id;
      const heading = node('tr', 'range-heading');
      const headingCell = node('td');
      headingCell.colSpan = 4;
      const title = node('h3', 'range-heading-title');
      title.id = 'range-' + row._id;
      const toggle = node('button', 'range-toggle');
      toggle.type = 'button';
      toggle.dataset.toggleRange = row._id;
      toggle.setAttribute('aria-controls', 'range-main-' + index + ' range-followup-' + index);
      toggle.setAttribute('aria-expanded', 'true');
      const copy = node('span', 'range-heading-copy');
      const summary = node('span', 'range-summary');
      summary.append(node('span', 'range-priority'), node('span', 'range-decision'), node('span', 'range-handoff-state'));
      copy.append(node('span', 'range-name'), summary);
      const action = node('span', 'range-toggle-action');
      action.append(node('span', 'range-toggle-label', '收起'), node('span', 'range-chevron', '⌃'));
      toggle.append(node('span', 'range-index', String(index + 1).padStart(2, '0')), copy, action);
      toggle.addEventListener('click', () => setRangeCollapsed(row._id, !collapsedRanges.has(row._id)));
      title.appendChild(toggle);
      headingCell.appendChild(title);
      heading.appendChild(headingCell);
      const tr = node('tr', 'scope-row range-body');
      tr.id = 'range-main-' + index;
      tr.dataset.rowId = row._id;
      tr.dataset.priority = priorityClass(row.priority);
      [['module','页面 / 功能模块'], ['scenarios','业务场景与结果'], ['dependencies','数据 / 配置依赖']].forEach(([key, label]) => {
        const td = node('td', 'scope-' + key);
        td.append(node('div', 'record-panel-title', label), rowField('scope', row, key));
        tr.appendChild(td);
      });
      const footer = node('tr', 'scope-followup range-body');
      footer.id = 'range-followup-' + index;
      const cell = node('td');
      cell.colSpan = 4;
      const grid = node('div', 'scope-footer-grid');
      const comment = node('div', 'scope-comment');
      comment.append(node('div', 'record-panel-title', '开发补充'), rowField('scope', row, 'handoff'));
      const controls = node('div', 'scope-field-controls');
      const decision = node(readOnly ? 'div' : 'label', 'scope-decision');
      decision.append(node('span', 'subfield-label', '本次范围'), rowField('scope', row, 'decision'));
      const priority = node(readOnly ? 'div' : 'label', 'scope-priority');
      priority.append(node('span', 'subfield-label', '优先级'), rowField('scope', row, 'priority'));
      const evidence = node('details', 'priority-evidence');
      const evidenceLabel = node('summary', '', '查看优先级依据');
      evidenceLabel.setAttribute('aria-label', '查看' + (row.range || '本范围') + '的优先级依据');
      evidence.append(evidenceLabel, rowField('scope', row, 'priorityNote'));
      controls.append(priority, decision, evidence);
      if (!readOnly) {
        const rename = node('details', 'record-rename');
        rename.append(node('summary', '', '编辑名称'), rowField('scope', row, 'range'));
        controls.append(rename, removeButton('scope', row, '移除范围'));
      }
      grid.append(comment, controls);
      cell.appendChild(grid);
      footer.appendChild(cell);
      group.append(heading, tr, footer);
      if (index > 0) body.parentNode.appendChild(group);
      updateRangeHeader(row);
      applyRangeView(row._id, collapsedRanges.has(row._id));
    });
  }

  function recordRows(name, body) {
    const panels = recordSpecs[name].panels;
    const titleKey = recordSpecs[name].title;
    state.tables[name].forEach((row, index) => {
      const group = index === 0 ? body : node('tbody');
      group.className = 'record-group';
      group.dataset.recordTable = name;
      group.dataset.recordId = row._id;
      const heading = node('tr', 'record-heading');
      const headingCell = node('td');
      headingCell.colSpan = schema[name].columns.length + (readOnly ? 0 : 1);
      const title = node('h3', 'record-heading-title');
      title.id = 'record-' + name + '-' + row._id;
      const toggle = node('button', 'record-toggle');
      toggle.type = 'button';
      toggle.dataset.recordToggle = name;
      toggle.setAttribute('aria-expanded', 'true');
      toggle.setAttribute('aria-controls', 'record-content-' + name + '-' + index);
      const copy = node('span', 'record-heading-copy');
      copy.append(node('span', 'record-prefix'), node('span', 'record-name'), node('span', 'record-summary'));
      const action = node('span', 'record-toggle-action');
      action.append(node('span', 'record-toggle-label', '收起'), node('span', 'range-chevron', '⌃'));
      toggle.append(node('span', 'record-index', String(index + 1).padStart(2, '0')), copy, action);
      toggle.addEventListener('click', () => setRecordCollapsed(name, row._id, !collapsedRecords[name].has(row._id)));
      title.appendChild(toggle);
      headingCell.appendChild(title);
      heading.appendChild(headingCell);
      const content = node('tr', 'data-row record-content');
      content.id = 'record-content-' + name + '-' + index;
      content.dataset.rowId = row._id;
      const cell = node('td');
      cell.colSpan = headingCell.colSpan;
      const grid = node('div', 'record-grid');
      for (const [key, label, tone] of panels) {
        const panel = node('div', 'record-panel record-panel-' + key + ' record-panel-' + tone);
        panel.append(node('div', 'record-panel-title', label), rowField(name, row, key));
        grid.appendChild(panel);
      }
      cell.appendChild(grid);
      if (!readOnly) {
        const footer = node('div', 'record-footer');
        const rename = node('details', 'record-rename');
        rename.append(node('summary', '', '编辑名称'), rowField(name, row, titleKey));
        footer.append(rename, removeButton(name, row, '移除记录'));
        cell.appendChild(footer);
      }
      content.appendChild(cell);
      group.append(heading, content);
      if (index > 0) body.parentNode.appendChild(group);
      updateRecordHeader(name, row);
      applyRecordView(name, row._id, collapsedRecords[name].has(row._id));
    });
  }

  function renderTable(name) {
    const table = document.querySelector('[data-table="' + name + '"]');
    const body = table.tBodies[0];
    Array.from(table.tBodies).slice(1).forEach(group => group.remove());
    body.replaceChildren();
    if (name === 'scope') {
      body.className = '';
      delete body.dataset.rangeId;
      delete body.dataset.collapsed;
      const ids = new Set(state.tables.scope.map(row => row._id));
      for (const id of collapsedRanges) if (!ids.has(id)) collapsedRanges.delete(id);
      table.querySelector('colgroup').innerHTML = '<col style="width:16%"><col style="width:20%"><col style="width:40%"><col style="width:24%">';
      table.tHead.rows[0].innerHTML = '<th scope="col">测试范围 / 优先级</th><th scope="col">页面 / 功能模块</th><th scope="col">业务场景与结果</th><th scope="col">数据 / 配置依赖</th>';
      scopeRows(body);
      updatePrioritySummary();
      updateRangeControls();
    } else if (recordTables.includes(name)) {
      table.classList.add('records-table');
      table.closest('.tw').classList.add('record-table-wrap');
      body.className = '';
      delete body.dataset.recordId;
      delete body.dataset.recordTable;
      delete body.dataset.collapsed;
      const ids = new Set(state.tables[name].map(row => row._id));
      for (const id of collapsedRecords[name]) if (!ids.has(id)) collapsedRecords[name].delete(id);
      recordRows(name, body);
      updateRecordControls(name);
    } else for (const row of state.tables[name]) {
      const tr = node('tr', 'data-row');
      tr.dataset.rowId = row._id;
      for (const col of schema[name].columns) {
        const td = node('td', 'cell-' + col.key);
        const tag = row._display && row._display.tag;
        if (col === schema[name].columns[0] && tag && ['critical','warning','info','success'].includes(tag.tone)) td.appendChild(node('span', 'row-tag tone-' + tag.tone, tag.text));
        td.appendChild(rowField(name, row, col.key));
        tr.appendChild(td);
      }
      if (!readOnly) {
        const actions = node('td', 'actions-col');
        actions.appendChild(removeButton(name, row));
        tr.appendChild(actions);
      }
      body.appendChild(tr);
    }
    requestAnimationFrame(() => body.querySelectorAll('textarea').forEach(resize));
    updateSectionSummary(name);
  }

  function updateProgress() {
    let count = 0;
    for (const name of Object.keys(schema)) {
      const item = state.sections[name];
      const shortcut = document.querySelector('[data-shortcut="' + name + '"]');
      const done = item.status !== '待补充';
      shortcut.classList.toggle('confirmed', done);
      const select = document.querySelector('[data-section-status="' + name + '"]');
      select.dataset.value = item.status;
      document.querySelector('[data-confirm="' + name + '"]').dataset.status = item.status;
      shortcut.querySelector('.section-state').textContent = item.status;
      updateSectionSummary(name);
      if (done) count++;
    }
    document.getElementById('completion').textContent = count + ' / ' + Object.keys(schema).length + ' 项已确认';
  }

  function updatePrioritySummary() {
    const summary = document.getElementById('priority-summary');
    if (!summary) return;
    summary.replaceChildren();
    ['含 P0','P0','P1','P2','待确认'].forEach(value => {
      const count = state.tables.scope.filter(row => (row.priority || '待确认') === value).length;
      if (count) summary.appendChild(node('span', 'priority-chip priority-' + priorityClass(value), value + ' · ' + count + ' 组'));
    });
    if (!state.tables.scope.length) summary.textContent = '尚未填写测试范围';
    updateSectionSummary('scope');
  }

  function renderPresentation() {
    const p = state._presentation || {};
    const defaults = {
      scope:'按业务范围列出页面、功能模块和代表场景，写清预期结果。每组下方确认本次范围。',
      config:'列出开测需要的开关和配置，区分文档参考值与本环境实际值，并补充生效与恢复方法。',
      services:'列出涉及的服务、前端或其他依赖，填写实际入口、部署版本和对接人。',
      logs:'按排查场景提供可直接搜索的关键词、实际输出服务与查询示例。',
      database:'填写要核对的业务数据、真实存储位置、关联键与查询方法。没有落库的数据请说明实际查询位置。',
      samples:'准备测试可直接使用的数据，并说明操作后应看到什么。'
    };
    document.querySelector('[data-document-badge]').textContent = p.badge || '按材料预填 · 待开发确认';
    document.querySelectorAll('[data-presentation]').forEach(slot => slot.replaceChildren());
    for (const name of Object.keys(schema)) {
      document.querySelector('[data-intro="' + name + '"]').textContent = p.intros && p.intros[name] || defaults[name];
      const notices = p.notices && p.notices[name] || [];
      for (const notice of notices) {
        const slot = document.querySelector('[data-presentation="' + name + (notice.position === 'after' ? '-after' : '-before') + '"]');
        const tone = ['critical','warning','info','success'].includes(notice.tone) ? notice.tone : 'info';
        const block = node('div', 'semantic-note tone-' + tone);
        if (notice.title) block.appendChild(node('b', '', notice.title));
        const text = node('span');
        addEmphasis(text, notice.text || '', notice.emphasis);
        block.appendChild(text);
        slot.appendChild(block);
      }
    }
    if (Array.isArray(p.modes) && p.modes.length) {
      const grid = node('div', 'mode-grid');
      for (const mode of p.modes) {
        const card = node('div', 'mode-card' + (mode.recommended ? ' recommended' : ''));
        card.append(node('span', 'mode-letter', mode.label || ''), node('b', '', mode.title || ''), node('p', '', mode.description || ''), node('code', '', mode.config || ''));
        if (mode.tag) card.appendChild(node('span', 'mode-tag', mode.tag));
        grid.appendChild(card);
      }
      document.querySelector('[data-presentation="config-before"]').prepend(grid);
    }
    if (Array.isArray(p.sources) && p.sources.length) {
      const slot = document.querySelector('[data-presentation="sources"]');
      slot.appendChild(node('b', '', '预填依据'));
      for (const source of p.sources) {
        const line = node('p', 'source-line');
        line.appendChild(node('strong', '', source.name || '参考材料'));
        if (source.note) line.appendChild(document.createTextNode(' · ' + source.note));
        slot.appendChild(line);
      }
    }
  }

  function updateProjectLabel() {
    const label = state.meta.requirement.trim() || '待填写需求';
    document.querySelectorAll('[data-project-title]').forEach(item => { item.textContent = label; });
  }

  function render() {
    renderPresentation();
    document.querySelectorAll('[data-binding]').forEach(field => {
      const parts = field.dataset.binding.split('.');
      if (parts.length !== 2 || !(parts[0] in state) || !(parts[1] in state[parts[0]])) return;
      if (readOnly) {
        const content = readonlyField(state[parts[0]][parts[1]], parts[0] === 'extras' || parts[1] === 'change' ? 'record-list' : 'text');
        field.className = content.className;
        field.replaceChildren(...content.childNodes);
        return;
      }
      field.value = state[parts[0]][parts[1]];
      if (field.tagName === 'TEXTAREA') attachRichField(field, parts[0] === 'extras' || parts[1] === 'change' ? 'record-list' : 'text');
      updateField(field);
    });
    for (const name of Object.keys(schema)) {
      renderTable(name);
      const status = document.querySelector('[data-section-status="' + name + '"]');
      const note = document.querySelector('[data-section-note="' + name + '"]');
      if (readOnly) {
        status.textContent = state.sections[name].status;
        note.textContent = state.sections[name].note || '未填写确认说明';
      } else {
        status.value = state.sections[name].status;
        note.value = state.sections[name].note;
        note.nextElementSibling.textContent = note.value || note.placeholder;
      }
    }
    updateProgress();
    updateProjectLabel();
    for (const name of Object.keys(schema)) applySectionView(name, collapsedSections.has(name));
    updateSectionControls();
    requestAnimationFrame(() => document.querySelectorAll('textarea').forEach(resize));
  }

  if (!readOnly) {
    document.querySelectorAll('[data-binding]').forEach(field => {
      const parts = field.dataset.binding.split('.');
      if (parts.length !== 2) return;
      field.addEventListener('input', () => {
        state[parts[0]][parts[1]] = field.value;
        field.classList.add('dirty');
        updateField(field);
        if (parts[1] === 'requirement') updateProjectLabel();
        changed();
      });
    });

    for (const name of Object.keys(schema)) {
      document.querySelector('[data-add="' + name + '"]').addEventListener('click', () => {
        const row = {_id: makeId()};
        for (const col of schema[name].columns) row[col.key] = col.kind === 'select' ? col.options[0] : '';
        state.tables[name].push(row);
        renderTable(name);
        setSectionCollapsed(name, false);
        if (name === 'scope') setRangeCollapsed(row._id, false);
        if (recordTables.includes(name)) setRecordCollapsed(name, row._id, false);
        changed();
        requestAnimationFrame(() => {
          const titleKey = name === 'scope' ? 'range' : recordSpecs[name].title;
          const field = Array.from(document.querySelector('[data-table="' + name + '"]').querySelectorAll('[data-row-field]'))
            .find(item => item.dataset.rowField === name + '.' + row._id + '.' + titleKey);
          const details = field.closest('details');
          if (details) details.open = true;
          if (field._openEditor) field._openEditor();
          field.focus();
          field.scrollIntoView({block: 'center', behavior: 'smooth'});
        });
      });
      document.querySelector('[data-section-status="' + name + '"]').addEventListener('change', event => {
        state.sections[name].status = event.target.value;
        updateProgress();
        changed();
      });
      document.querySelector('[data-section-note="' + name + '"]').addEventListener('input', event => {
        state.sections[name].note = event.target.value;
        event.target.nextElementSibling.textContent = event.target.value || event.target.placeholder;
        resize(event.target);
        changed();
      });
    }

    document.getElementById('undo-delete').addEventListener('click', () => {
      if (!lastDeletion) return;
      const {name, index, row} = lastDeletion;
      state.tables[name].splice(index, 0, row);
      lastDeletion = null;
      renderTable(name);
      setSectionCollapsed(name, false);
      if (name === 'scope') setRangeCollapsed(row._id, false);
      if (recordTables.includes(name)) setRecordCollapsed(name, row._id, false);
      changed();
      showToast('已恢复删除的行。');
    });

    function safeJson(value) {
      return JSON.stringify(value).replace(/</g, '\\u003c');
    }

    function baseName() {
      return (state.meta.requirement.trim() || '需求').replace(/[\\/:*?"<>|\u0000-\u001f]/g, '_').slice(0, 70);
    }

    function download(content, filename, type) {
      const blob = new Blob([content], {type});
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    }

    document.getElementById('save-html').addEventListener('click', () => {
      writeDraft();
      const exported = copy(state);
      exported.documentId = makeId();
      const clone = document.documentElement.cloneNode(true);
      clone.querySelector('#handoff-data').textContent = safeJson(exported);
      const liveFields = document.querySelectorAll('input,textarea,select');
      const cloneFields = clone.querySelectorAll('input,textarea,select');
      liveFields.forEach((live, index) => {
        const field = cloneFields[index];
        if (live.tagName === 'TEXTAREA') field.textContent = live.value;
        else if (live.tagName === 'SELECT') Array.from(field.options).forEach(option => option.toggleAttribute('selected', option.value === live.value));
        else if (live.type !== 'file') field.setAttribute('value', live.value);
        field.classList.remove('need-attention');
      });
      clone.querySelector('#toast').hidden = true;
      clone.querySelectorAll('.rich-field.editing').forEach(wrapper => wrapper.classList.remove('editing'));
      clone.querySelector('#save-status').textContent = '已载入填写内容；修改后自动暂存';
      clone.querySelector('title').textContent = (state.meta.requirement.trim() || '需求') + ' · 测试交接填写表';
      clone.querySelectorAll('.tw').forEach(wrapper => wrapper.replaceWith(...wrapper.childNodes));
      download('<!DOCTYPE html>\n' + clone.outerHTML, baseName() + '_测试交接填写版.html', 'text/html;charset=utf-8');
      showToast('已生成填写版 HTML，可将下载文件发给同事。');
    });

    document.getElementById('export-json').addEventListener('click', () => {
      writeDraft();
      download(JSON.stringify(state, null, 2), baseName() + '_测试交接数据.json', 'application/json;charset=utf-8');
      showToast('已导出填写数据，可在同版填写表中导入。');
    });

    const importInput = document.getElementById('import-file');
    document.getElementById('import-json').addEventListener('click', () => importInput.click());
    importInput.addEventListener('change', async () => {
      const file = importInput.files && importInput.files[0];
      if (!file) return;
      try {
        if (file.size > 8 * 1024 * 1024) throw new Error('文件过大，请选择本填写表导出的数据文件。');
        const incoming = validate(JSON.parse(await file.text()));
        state = incoming;
        lastDeletion = null;
        render();
        writeDraft();
        showToast('已导入填写数据。');
      } catch (error) {
        showToast(error.message || '无法读取数据文件。');
      } finally {
        importInput.value = '';
      }
    });

    document.getElementById('next-empty').addEventListener('click', () => {
      const fields = Array.from(document.querySelectorAll('.field')).filter(field => field.tagName !== 'SELECT' && !field.value.trim());
      if (!fields.length) { showToast('可填写的空白项已填完，请核对各部分的开发确认状态。'); return; }
      const index = fields.indexOf(lastEmptyField);
      const field = fields[(index + 1) % fields.length];
      lastEmptyField = field;
      revealField(field);
      const details = field.closest('details');
      if (details) details.open = true;
      if (field._openEditor) field._openEditor();
      field.focus({preventScroll: true});
      field.scrollIntoView({block: 'center', behavior: 'smooth'});
      field.classList.add('need-attention');
      setTimeout(() => field.classList.remove('need-attention'), 2000);
    });
    window.addEventListener('beforeunload', writeDraft);
  }

  document.getElementById('print-form').addEventListener('click', () => {
    document.querySelectorAll('textarea').forEach(resize);
    window.print();
  });

  let resizeTimer;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => document.querySelectorAll('textarea').forEach(resize), 100);
  });
  let printDetails = [];
  window.addEventListener('beforeprint', () => {
    for (const name of Object.keys(schema)) applySectionView(name, false);
    for (const row of state.tables.scope) applyRangeView(row._id, false);
    for (const name of recordTables) for (const row of state.tables[name]) applyRecordView(name, row._id, false);
    printDetails = Array.from(document.querySelectorAll('.priority-evidence, .source-details, .extra-field, .metadata')).map(item => [item, item.open]);
    printDetails.forEach(([item]) => { item.open = true; });
    document.querySelectorAll('textarea').forEach(resize);
  });
  window.addEventListener('afterprint', () => {
    printDetails.forEach(([item, open]) => { item.open = open; });
    printDetails = [];
    for (const row of state.tables.scope) applyRangeView(row._id, collapsedRanges.has(row._id));
    for (const name of recordTables) for (const row of state.tables[name]) applyRecordView(name, row._id, collapsedRecords[name].has(row._id));
    for (const name of Object.keys(schema)) applySectionView(name, collapsedSections.has(name));
    document.querySelectorAll('textarea').forEach(resize);
  });

  document.querySelectorAll('[data-toggle-section]').forEach(toggle => {
    toggle.addEventListener('click', () => {
      const name = toggle.dataset.toggleSection;
      setSectionCollapsed(name, !collapsedSections.has(name));
    });
  });
  for (const [attribute, collapsed] of [['data-record-expand', false], ['data-record-collapse', true]]) {
    document.querySelectorAll('[' + attribute + ']').forEach(control => control.addEventListener('click', () => {
      const name = control.getAttribute(attribute);
      for (const row of state.tables[name]) {
        if (collapsed) collapsedRecords[name].add(row._id);
        else collapsedRecords[name].delete(row._id);
        applyRecordView(name, row._id, collapsed);
      }
      updateRecordControls(name);
      saveRecordView();
      requestAnimationFrame(markSection);
    }));
  }
  for (const [id, collapsed] of [['expand-ranges', false], ['collapse-ranges', true]]) {
    document.getElementById(id).addEventListener('click', () => {
      for (const row of state.tables.scope) {
        if (collapsed) collapsedRanges.add(row._id);
        else collapsedRanges.delete(row._id);
        applyRangeView(row._id, collapsed);
      }
      updateRangeControls();
      saveRangeView();
      requestAnimationFrame(markSection);
    });
  }
  for (const [id, collapsed] of [['expand-all', false], ['collapse-all', true]]) {
    document.getElementById(id).addEventListener('click', () => {
      for (const name of Object.keys(schema)) {
        if (collapsed) collapsedSections.add(name);
        else collapsedSections.delete(name);
        applySectionView(name, collapsed);
      }
      updateSectionControls();
      saveSectionView();
      requestAnimationFrame(markSection);
    });
  }
  document.addEventListener('click', event => {
    const link = event.target.closest('a[href^="#"]');
    if (link && !event.defaultPrevented && !event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey) revealHash(link.getAttribute('href'), false);
  });
  window.addEventListener('hashchange', () => revealHash(location.hash, true));

  const sideToggle = document.getElementById('side-toggle');
  sideToggle.addEventListener('click', () => {
    const hidden = document.body.classList.toggle('side-hidden');
    sideToggle.textContent = hidden ? '›' : '‹';
    sideToggle.setAttribute('aria-expanded', String(!hidden));
    sideToggle.title = hidden ? '展开侧栏' : '收起侧栏';
  });
  const backToTop = document.getElementById('totop');
  backToTop.addEventListener('click', () => window.scrollTo({top:0, behavior:'smooth'}));
  let scrollFrame = false;
  function markSection() {
    scrollFrame = false;
    let active = document.querySelector('.form-section h2');
    document.querySelectorAll('.form-section h2').forEach(heading => {
      if (heading.getBoundingClientRect().top <= 170) active = heading;
    });
    document.querySelectorAll('#toc a').forEach(link => {
      const current = active && link.dataset.target === active.id;
      link.classList.toggle('active', current);
      if (current) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    });
    backToTop.classList.toggle('show', window.scrollY > 450);
  }
  window.addEventListener('scroll', () => {
    if (!scrollFrame) { scrollFrame = true; requestAnimationFrame(markSection); }
  }, {passive:true});

  render();
  revealHash(location.hash, true);
  markSection();
  statusNode.textContent = readOnly ? '只读版 · 内容已锁定' : restored ? '已恢复本机暂存内容' : draftAvailable ? '本机自动暂存 · 分享请保存 HTML' : '本机暂存不可用，请保存填写版 HTML';
})();


