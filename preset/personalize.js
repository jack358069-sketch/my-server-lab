/* 访客个性化：从预设里挑选头像与背景，仅存在本浏览器（localStorage） */
(function () {
  'use strict';
  var BASE = 'http://47.115.150.227/preset/';
  var KEY = 'zerolab.look';
  var AVATARS = ['a1', 'a2', 'a3', 'a4', 'a5', 'a6'];
  var BGS = ['b1', 'b2', 'b3', 'b4', 'b5', 'b6'];
  var THEMES = ['auto', 'light', 'dark'];
  var state = { avatar: '', bg: '', theme: 'auto' };

  function valid(list, id) { return list.indexOf(id) >= 0 ? id : ''; }
  function load() {
    try {
      var o = JSON.parse(localStorage.getItem(KEY) || '{}');
      state.avatar = valid(AVATARS, o.avatar);
      state.bg = valid(BGS, o.bg);
      state.theme = THEMES.indexOf(o.theme) >= 0 ? o.theme : 'auto';
    } catch (e) { state = { avatar: '', bg: '', theme: 'auto' }; }
  }
  function save() {
    try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) { /* 隐私模式下忽略 */ }
  }
  function url(kind, id) { return BASE + kind + '/' + id + '.svg'; }

  var css = [
    '.zl-look-btn{position:fixed;right:20px;bottom:20px;z-index:9998;width:46px;height:46px;',
    'border:0;border-radius:50%;background:#fff;box-shadow:0 6px 20px rgba(0,0,0,.18);font-size:22px;',
    'cursor:pointer;transition:transform .18s ease}',
    '.zl-look-btn:hover{transform:scale(1.08)}',
    '.zl-look-mask{position:fixed;inset:0;background:rgba(0,0,0,.35);z-index:9999;opacity:0;',
    'pointer-events:none;transition:opacity .22s ease}',
    '.zl-look-mask.open{opacity:1;pointer-events:auto}',
    '.zl-look-panel{position:fixed;right:16px;bottom:78px;z-index:10000;width:min(360px,calc(100vw - 32px));',
    'max-height:min(78vh,640px);overflow:auto;background:#fff;border-radius:18px;padding:18px 20px;',
    'box-shadow:0 18px 50px rgba(0,0,0,.22);transform:translateY(14px) scale(.98);opacity:0;',
    'pointer-events:none;transition:opacity .2s ease,transform .2s ease;',
    'font-family:-apple-system,"PingFang SC","Microsoft YaHei",system-ui,sans-serif}',
    '.zl-look-panel.open{opacity:1;transform:none;pointer-events:auto}',
    '.zl-look-panel h3{margin:0 0 4px;font-size:17px}',
    '.zl-hint{color:#8a8a8e;font-size:12px;margin:0 0 12px}',
    '.zl-label{font-size:13px;color:#3a3a3c;margin:12px 0 8px;font-weight:600}',
    '.zl-grid{display:grid;grid-template-columns:repeat(6,1fr);gap:8px}',
    '.zl-grid.zl-bg-grid{grid-template-columns:repeat(3,1fr)}',
    '.zl-item{padding:0;border:2px solid transparent;border-radius:12px;background:none;cursor:pointer;line-height:0}',
    '.zl-item img{width:100%;height:44px;object-fit:cover;border-radius:10px;display:block}',
    '.zl-grid .zl-item:not(.zl-wide) img{height:44px;border-radius:50%;width:44px;margin:0 auto}',
    '.zl-item.selected{border-color:#0071e3}',
    '.zl-actions{display:flex;gap:10px;justify-content:flex-end;margin-top:16px}',
    '.zl-actions button{border:0;border-radius:999px;padding:9px 16px;font-size:13px;cursor:pointer}',
    '#zl-reset{background:#f2f2f7;color:#3a3a3c}',
    '#zl-close{background:#0071e3;color:#fff}',
    '.zl-progress{position:fixed;top:0;left:0;height:3px;width:0;z-index:10001;',
    'background:linear-gradient(90deg,#5aa7ff,#7c5cff);transition:width .12s linear}',
    'body.zl-theme-light{--fg:#1d1d1f;--muted:#6e6e73;--bg:#f5f5f7;--card:#fff;--accent:#0071e3;',
    'background:radial-gradient(1200px 600px at 20% 0%,#e8f0ff 0%,#f5f5f7 45%,#fafafa 100%) !important}',
    'body.zl-theme-dark{--fg:#f5f5f7;--muted:#98989d;--bg:#000;--card:#1c1c1e;--accent:#0a84ff;',
    'background:radial-gradient(1200px 600px at 20% 0%,#1d2b45 0%,#000 45%,#0a0a0c 100%) !important}',
    'body.has-user-bg{background-image:linear-gradient(rgba(255,255,255,.55),rgba(255,255,255,.7)),var(--zl-bg) !important;',
    'background-size:cover !important;background-attachment:fixed !important;background-position:center !important}',
    'body.zl-theme-light.has-user-bg{background-image:linear-gradient(rgba(255,255,255,.55),rgba(255,255,255,.7)),var(--zl-bg) !important}',
    'body.zl-theme-dark.has-user-bg{background-image:linear-gradient(rgba(0,0,0,.45),rgba(0,0,0,.62)),var(--zl-bg) !important}',
    'body.zl-theme-light .zl-look-btn{background:#fff;color:inherit}',
    'body.zl-theme-light .zl-look-panel{background:#fff;color:inherit}',
    'body.zl-theme-light .zl-label{color:#3a3a3c}',
    'body.zl-theme-light #zl-reset{background:#f2f2f7;color:#3a3a3c}',
    '@media (prefers-color-scheme:dark){',
    'body.has-user-bg:not(.zl-theme-light){background-image:linear-gradient(rgba(0,0,0,.45),rgba(0,0,0,.62)),var(--zl-bg) !important}',
    '.zl-look-btn{background:#1c1c1e;color:#f5f5f7}',
    '.zl-look-panel{background:#1c1c1e;color:#f5f5f7}',
    '.zl-label{color:#d1d1d6}',
    '#zl-reset{background:#2c2c2e;color:#f5f5f7}',
    '.zl-search-box{background:#1c1c1e;color:#f5f5f7}',
    '.zl-search-box input{background:#2c2c2e;border-color:#3a3a3c;color:#f5f5f7}}',
    'body.zl-theme-dark .zl-look-btn{background:#1c1c1e;color:#f5f5f7}',
    'body.zl-theme-dark .zl-look-panel{background:#1c1c1e;color:#f5f5f7}',
    'body.zl-theme-dark .zl-label{color:#d1d1d6}',
    'body.zl-theme-dark #zl-reset{background:#2c2c2e;color:#f5f5f7}',
    '.zl-theme-row{display:flex;gap:8px}',
    '.zl-theme-row button{flex:1;border:1px solid #d1d1d6;background:transparent;color:inherit;',
    'border-radius:10px;padding:8px 0;font-size:13px;cursor:pointer}',
    '.zl-theme-row button.selected{border-color:#0071e3;color:#0071e3}',
    'body.zl-theme-dark .zl-theme-row button{border-color:#3a3a3c}',
    '.zl-search-mask{position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:10002;opacity:0;',
    'pointer-events:none;transition:opacity .2s ease}',
    '.zl-search-mask.open{opacity:1;pointer-events:auto}',
    '.zl-search-box{position:fixed;top:18vh;left:50%;width:min(520px,calc(100vw - 32px));background:#fff;',
    'border-radius:16px;padding:14px;z-index:10003;display:flex;gap:8px;box-shadow:0 18px 50px rgba(0,0,0,.25);',
    'opacity:0;pointer-events:none;transform:translate(-50%,-8px);transition:opacity .2s ease,transform .2s ease}',
    '.zl-search-box.open{opacity:1;pointer-events:auto;transform:translate(-50%,0)}',
    '.zl-search-box input{flex:1;min-width:0;border:1px solid #d1d1d6;border-radius:10px;padding:10px 12px;font-size:15px;outline:none}',
    '.zl-search-box button{border:0;border-radius:10px;padding:0 16px;background:#0071e3;color:#fff;font-size:14px;cursor:pointer}',
    'body.zl-theme-dark .zl-search-box{background:#1c1c1e;color:#f5f5f7}',
    'body.zl-theme-dark .zl-search-box input{background:#2c2c2e;border-color:#3a3a3c;color:#f5f5f7}'
  ].join('');

  function injectCss() {
    var style = document.createElement('style');
    style.textContent = css;
    document.head.appendChild(style);
  }

  var original = { avatar: '', bg: '' };
  function collectTargets() {
    return {
      avatars: document.querySelectorAll('#profile-avatar, .hero .avatar'),
      banners: document.querySelectorAll('#header-background'),
      blog: document.getElementById('profile-avatar') !== null
    };
  }
  function remember(src) { if (!original.avatar) original.avatar = src || ''; }

  function apply() {
    document.body.classList.toggle('zl-theme-light', state.theme === 'light');
    document.body.classList.toggle('zl-theme-dark', state.theme === 'dark');
    var t = collectTargets();
    Array.prototype.forEach.call(t.avatars, function (el) {
      if (!el.dataset.zlOrig) el.dataset.zlOrig = el.getAttribute('src') || '';
      remember(el.dataset.zlOrig);
      el.src = state.avatar ? url('avatars', state.avatar) : el.dataset.zlOrig;
    });
    Array.prototype.forEach.call(t.banners, function (el) {
      if (!el.dataset.zlOrig) el.dataset.zlOrig = el.getAttribute('src') || '';
      original.bg = original.bg || el.dataset.zlOrig;
      el.src = state.bg ? url('bg', state.bg) : el.dataset.zlOrig;
    });
    if (!t.blog) {
      if (state.bg) {
        document.body.classList.add('has-user-bg');
        document.body.style.setProperty('--zl-bg', 'url("' + url('bg', state.bg) + '")');
      } else {
        document.body.classList.remove('has-user-bg');
        document.body.style.removeProperty('--zl-bg');
      }
    }
  }

  function thumb(kind, id, wide) {
    var b = document.createElement('button');
    b.type = 'button';
    b.className = 'zl-item' + (wide ? ' zl-wide' : '');
    b.dataset.kind = kind;
    b.dataset.id = id;
    b.setAttribute('aria-label', (kind === 'avatars' ? '头像 ' : '背景 ') + id);
    var img = document.createElement('img');
    img.src = url(kind, id);
    img.alt = '';
    b.appendChild(img);
    return b;
  }

  function buildPanel() {
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'zl-look-btn';
    btn.title = '个性设置';
    btn.setAttribute('aria-label', '个性设置');
    btn.textContent = '🎨';

    var mask = document.createElement('div');
    mask.className = 'zl-look-mask';

    var panel = document.createElement('div');
    panel.className = 'zl-look-panel';
    panel.setAttribute('role', 'dialog');
    panel.setAttribute('aria-label', '个性化设置');

    var h = document.createElement('h3');
    h.textContent = '个性化';
    var hint = document.createElement('p');
    hint.className = 'zl-hint';
    hint.textContent = '只在你自己的浏览器生效，不影响别人';

    var la = document.createElement('div');
    la.className = 'zl-label';
    la.textContent = '头像';
    var gridA = document.createElement('div');
    gridA.className = 'zl-grid';
    AVATARS.forEach(function (id) { gridA.appendChild(thumb('avatars', id, false)); });

    var lb = document.createElement('div');
    lb.className = 'zl-label';
    lb.textContent = '背景';
    var gridB = document.createElement('div');
    gridB.className = 'zl-grid zl-bg-grid';
    BGS.forEach(function (id) { gridB.appendChild(thumb('bg', id, true)); });

    var lt = null;
    var themeRow = null;
    if (document.getElementById('profile-avatar') === null) {
      lt = document.createElement('div');
      lt.className = 'zl-label';
      lt.textContent = '主题';
      themeRow = document.createElement('div');
      themeRow.className = 'zl-theme-row';
      [['auto', '跟随系统'], ['light', '浅色'], ['dark', '深色']].forEach(function (pair) {
        var b = document.createElement('button');
        b.type = 'button';
        b.dataset.theme = pair[0];
        b.textContent = pair[1];
        themeRow.appendChild(b);
      });
    }

    var actions = document.createElement('div');
    actions.className = 'zl-actions';
    var reset = document.createElement('button');
    reset.type = 'button';
    reset.id = 'zl-reset';
    reset.textContent = '恢复默认';
    var close = document.createElement('button');
    close.type = 'button';
    close.id = 'zl-close';
    close.textContent = '完成';
    actions.appendChild(reset);
    actions.appendChild(close);

    panel.appendChild(h);
    panel.appendChild(hint);
    panel.appendChild(la);
    panel.appendChild(gridA);
    panel.appendChild(lb);
    panel.appendChild(gridB);
    if (themeRow) {
      panel.appendChild(lt);
      panel.appendChild(themeRow);
    }
    panel.appendChild(actions);

    document.body.appendChild(btn);
    document.body.appendChild(mask);
    document.body.appendChild(panel);

    function refresh() {
      Array.prototype.forEach.call(panel.querySelectorAll('.zl-item'), function (el) {
        var on = el.dataset.kind === 'avatars' ? el.dataset.id === state.avatar
                                               : el.dataset.id === state.bg;
        el.classList.toggle('selected', on);
      });
      if (themeRow) {
        Array.prototype.forEach.call(themeRow.querySelectorAll('button'), function (el) {
          el.classList.toggle('selected', el.dataset.theme === state.theme);
        });
      }
    }
    function open() { panel.classList.add('open'); mask.classList.add('open'); refresh(); }
    function shut() { panel.classList.remove('open'); mask.classList.remove('open'); }

    btn.addEventListener('click', open);
    close.addEventListener('click', shut);
    mask.addEventListener('click', shut);
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') shut(); });

    panel.addEventListener('click', function (e) {
      var el = e.target.closest ? e.target.closest('.zl-item') : null;
      if (!el) return;
      if (el.dataset.kind === 'avatars') state.avatar = el.dataset.id;
      else state.bg = el.dataset.id;
      save();
      apply();
      refresh();
    });
    reset.addEventListener('click', function () {
      state = { avatar: '', bg: '', theme: 'auto' };
      save();
      apply();
      refresh();
    });
    if (themeRow) {
      themeRow.addEventListener('click', function (e) {
        var b = e.target.closest ? e.target.closest('button[data-theme]') : null;
        if (!b) return;
        state.theme = b.dataset.theme;
        save();
        apply();
        refresh();
      });
    }
  }

  function searchUi() {
    var triggers = document.querySelectorAll('.search-form-input');
    if (!triggers.length) return;
    var mask = document.createElement('div');
    mask.className = 'zl-search-mask';
    var box = document.createElement('form');
    box.className = 'zl-search-box';
    box.setAttribute('role', 'search');
    var input = document.createElement('input');
    input.type = 'search';
    input.placeholder = '输入关键词后回车';
    input.setAttribute('aria-label', '搜索博客');
    var go = document.createElement('button');
    go.type = 'submit';
    go.textContent = '搜索';
    box.appendChild(input);
    box.appendChild(go);
    document.body.appendChild(mask);
    document.body.appendChild(box);

    function open() { box.classList.add('open'); mask.classList.add('open'); input.focus(); }
    function shut() { box.classList.remove('open'); mask.classList.remove('open'); }
    Array.prototype.forEach.call(triggers, function (el) {
      el.addEventListener('click', function (e) { e.preventDefault(); open(); });
    });
    mask.addEventListener('click', shut);
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') shut();
    });
    box.addEventListener('submit', function (e) {
      e.preventDefault();
      var q = input.value.trim();
      if (!q) { input.focus(); return; }
      location.href = '/index.php/search/' + encodeURIComponent(q) + '/';
    });
  }

  function progressBar() {
    var post = document.getElementById('post');
    if (!post) return;
    var bar = document.createElement('div');
    bar.className = 'zl-progress';
    document.body.appendChild(bar);
    function update() {
      var content = document.querySelector('.post-content') || post;
      var rect = content.getBoundingClientRect();
      var total = rect.height - window.innerHeight;
      var pct = total > 0 ? (-rect.top / total) * 100 : 100;
      bar.style.width = Math.min(100, Math.max(0, pct)) + '%';
    }
    window.addEventListener('scroll', update, { passive: true });
    window.addEventListener('resize', update);
    update();
  }

  load();
  injectCss();
  apply();
  buildPanel();
  searchUi();
  progressBar();
})();
