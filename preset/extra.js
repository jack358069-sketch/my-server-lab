/* Zero Lab 增强：文章页目录（如主题未启用）与上下篇兜底 */
(function () {
  'use strict';
  var article = document.querySelector('.post-content');
  if (!article) return;

  /* 1. 目录：主题自带 tocbot 时跳过，否则手工生成 */
  var tocBox = document.getElementById('toc-content');
  var hasTocbot = typeof window.tocbot !== 'undefined';
  if (tocBox && !hasTocbot) {
    var heads = article.querySelectorAll('h2, h3');
    if (heads.length >= 3) {
      var list = document.createElement('ul');
      list.style.cssText = 'list-style:none;padding-left:0;margin:0;line-height:1.9';
      Array.prototype.forEach.call(heads, function (h, i) {
        if (!h.id) h.id = 'zl-h-' + i;
        var li = document.createElement('li');
        var a = document.createElement('a');
        a.href = '#' + h.id;
        a.textContent = h.textContent;
        a.style.cssText = (h.tagName === 'H3' ? 'padding-left:16px;' : '') +
          'color:inherit;text-decoration:none;font-size:.9em;opacity:.85';
        li.appendChild(a);
        list.appendChild(li);
      });
      tocBox.appendChild(list);
      var toc = document.getElementById('toc');
      if (toc) toc.style.display = 'block';
    }
  }

  /* 2. 上下篇兜底：服务端未输出时，用 RSS 里的文章顺序补上 */
  if (document.getElementById('post-nav')) return;
  var permalink = (document.querySelector('link[rel=canonical]') || {}).href || location.href;
  fetch('/index.php/feed/', { credentials: 'omit' })
    .then(function (r) { return r.text(); })
    .then(function (xml) {
      var doc = new DOMParser().parseFromString(xml, 'text/xml');
      var items = Array.prototype.slice.call(doc.querySelectorAll('item'));
      var cur = -1;
      items.forEach(function (it, i) {
        var link = (it.querySelector('link') || {}).textContent || '';
        if (link.indexOf(permalink.replace(/\/$/, '')) !== -1) cur = i;
      });
      if (cur < 0) return;
      var box = document.createElement('div');
      box.id = 'post-nav';
      box.style.cssText = 'display:flex;flex-direction:column;gap:8px;margin:26px 0 10px;padding:16px 18px;' +
        'border-radius:14px;background:rgba(255,255,255,.55);border:1px solid rgba(0,0,0,.06);font-size:14px';
      function add(label, it) {
        if (!it) return;
        var p = document.createElement('p');
        p.style.margin = '0';
        var a = document.createElement('a');
        a.href = it.querySelector('link').textContent;
        a.textContent = label + '：' + it.querySelector('title').textContent;
        a.style.cssText = 'color:inherit;text-decoration:none;border-bottom:1px dashed rgba(0,0,0,.18)';
        p.appendChild(a);
        box.appendChild(p);
      }
      add('上一篇', items[cur + 1]);
      add('下一篇', items[cur - 1]);
      var tags = document.getElementById('post-footer');
      if (tags && tags.parentNode) tags.parentNode.insertBefore(box, tags.nextSibling);
    })
    .catch(function () {});
})();
