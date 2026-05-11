// ===== Ray Research · Global Sidebar Renderer =====
// 工作流：
// 1. 优先用 manifest.site.base_url 推断 base path（fallback 到 URL 启发式）
// 2. fetch manifest.json 拿话题数据
// 3. 渲染 sidebar HTML 注入 body
// 4. 解析当前页面 section[id] 构建当前报告章节列表
// 5. IntersectionObserver 滚动跟随高亮章节
// 6. 任何失败都安全降级：移除 body.rs-active，恢复原有布局

(function() {
  'use strict';

  // ----- 路径推断 -----
  // 优先策略：从 <script src> 自身位置推断（最稳）
  function inferBase() {
    try {
      var scripts = document.getElementsByTagName('script');
      for (var i = scripts.length - 1; i >= 0; i--) {
        var src = scripts[i].src || '';
        if (/\/assets\/sidebar\.js(?:\?|$)/.test(src)) {
          var u = new URL(src, window.location.href);
          // 去掉 'assets/sidebar.js' 得到 base
          return u.pathname.replace(/assets\/sidebar\.js$/, '');
        }
      }
    } catch (e) {}
    // 兜底：URL 路径启发
    var path = window.location.pathname;
    var match = path.match(/^(\/[^\/]+\/)/);
    if (match && /ray-research/i.test(match[1])) return match[1];
    return '/';
  }
  var BASE = inferBase();
  var MANIFEST_URL = BASE + 'manifest.json';

  // 推断当前位置
  function inferCurrent() {
    var path = window.location.pathname;
    if (path.indexOf(BASE) === 0) path = path.substring(BASE.length);
    path = path.replace(/^\//, '');
    var parts = path.split('/').filter(Boolean);
    if (parts.length === 0) return { topic: null, file: null };
    if (parts.length === 1) return { topic: parts[0].replace(/\.html$/, ''), file: null };
    return { topic: parts[0], file: parts[parts.length - 1] };
  }

  // ----- DOM helpers -----
  function el(tag, attrs, children) {
    var node = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function(k) {
      if (k === 'html') node.innerHTML = attrs[k];
      else if (k === 'text') node.textContent = attrs[k];
      else node.setAttribute(k, attrs[k]);
    });
    if (children) children.forEach(function(c) { if (c) node.appendChild(c); });
    return node;
  }

  // ----- Manifest 容错：清洗 + 默认值 -----
  function sanitizeManifest(raw) {
    if (!raw || typeof raw !== 'object') throw new Error('manifest is not an object');
    var site = (raw.site && typeof raw.site === 'object') ? raw.site : {};
    var clean = {
      site: {
        name: typeof site.name === 'string' && site.name ? site.name : 'Ray Research',
        tagline: typeof site.tagline === 'string' ? site.tagline : '',
        base_url: typeof site.base_url === 'string' ? site.base_url : null,
        github: typeof site.github === 'string' ? site.github : ''
      },
      topics: []
    };
    var topics = Array.isArray(raw.topics) ? raw.topics : [];
    topics.forEach(function(t) {
      if (!t || typeof t !== 'object') return;
      if (typeof t.slug !== 'string' || !t.slug) return;
      var reports = Array.isArray(t.reports) ? t.reports : [];
      var cleanReports = [];
      reports.forEach(function(r) {
        if (!r || typeof r !== 'object') return;
        if (typeof r.file !== 'string' || !r.file) return;
        cleanReports.push({
          date: typeof r.date === 'string' ? r.date : '',
          file: r.file,
          title: typeof r.title === 'string' ? r.title : r.file
        });
      });
      clean.topics.push({
        slug: t.slug,
        name: typeof t.name === 'string' && t.name ? t.name : t.slug,
        tagline: typeof t.tagline === 'string' ? t.tagline : '',
        reports: cleanReports
      });
    });
    return clean;
  }

  // ----- Sidebar HTML 渲染 -----
  function render(manifest) {
    // 如 manifest 提供了 base_url 且与 inferBase 不同，以 manifest 为准
    if (manifest.site.base_url && typeof manifest.site.base_url === 'string') {
      BASE = manifest.site.base_url;
      if (BASE.charAt(BASE.length - 1) !== '/') BASE += '/';
    }

    var current = inferCurrent();
    var sidebar = el('aside', { id: 'ray-sidebar', 'aria-label': '调研报告导航' });

    // Brand
    var brand = el('a', { class: 'rs-brand', href: BASE }, [
      el('strong', { text: manifest.site.name }),
      manifest.site.tagline ? el('span', { text: manifest.site.tagline }) : null
    ].filter(Boolean));
    sidebar.appendChild(brand);

    // Section 1: All topics
    var topicsSection = el('div', { class: 'rs-section' });
    topicsSection.appendChild(el('div', { class: 'rs-section-label', text: '全部话题' }));

    var topicsList = el('ul', { class: 'rs-topics' });
    manifest.topics.forEach(function(topic) {
      var isActiveTopic = current.topic === topic.slug;
      var li = el('li', { class: 'rs-topic', 'data-active': isActiveTopic ? 'true' : 'false' });

      var topicLink = el('a', { class: 'rs-topic-name', href: BASE + topic.slug + '/' }, [
        document.createTextNode(topic.name),
        el('span', { class: 'rs-count', text: '(' + topic.reports.length + ')' })
      ]);
      li.appendChild(topicLink);

      var reportsUl = el('ul', { class: 'rs-reports' });
      topic.reports.forEach(function(r) {
        var isCurrentReport = isActiveTopic && current.file === r.file;
        var rLi = el('li');
        var rA = el('a', {
          href: BASE + topic.slug + '/' + r.file,
          'data-current': isCurrentReport ? 'true' : 'false',
          text: r.date || r.file
        });
        rLi.appendChild(rA);
        reportsUl.appendChild(rLi);
      });
      li.appendChild(reportsUl);
      topicsList.appendChild(li);
    });
    topicsSection.appendChild(topicsList);
    sidebar.appendChild(topicsSection);

    // Section 2: 本文章节（只在报告页面显示）
    var sections = document.querySelectorAll('article section[id], main section[id]');
    if (sections.length > 0) {
      var tocSection = el('div', { class: 'rs-section rs-current-toc' });
      tocSection.appendChild(el('div', { class: 'rs-section-label', text: '本文章节' }));

      var tocList = el('ul', { class: 'rs-toc-list' });
      sections.forEach(function(s, idx) {
        var h2 = s.querySelector('h2');
        var num = s.querySelector('.section-num');
        var title = h2 ? h2.textContent.trim() : (s.id || '#' + (idx + 1));
        var numText = num ? num.textContent.trim().split('/')[0].trim() : String(idx + 1).padStart(2, '0');

        var li = el('li');
        var a = el('a', { href: '#' + s.id }, [
          el('span', { class: 'rs-num', text: numText }),
          document.createTextNode(title.length > 18 ? title.substring(0, 18) + '…' : title)
        ]);
        a.dataset.targetId = s.id;
        li.appendChild(a);
        tocList.appendChild(li);
      });
      tocSection.appendChild(tocList);
      sidebar.appendChild(tocSection);
    }

    // Hamburger button (无障碍属性 + Esc 关闭)
    var hamburger = el('button', {
      id: 'ray-sidebar-toggle',
      'aria-label': '打开/关闭导航',
      'aria-expanded': 'false',
      'aria-controls': 'ray-sidebar',
      title: '打开/关闭导航',
      type: 'button',
      html: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><path d="M3 6h18M3 12h18M3 18h18"/></svg>'
    });

    function setDrawer(open) {
      sidebar.setAttribute('data-open', open ? 'true' : 'false');
      hamburger.setAttribute('aria-expanded', open ? 'true' : 'false');
      document.body.classList.toggle('rs-drawer-open', open);
      if (open) {
        // Focus first link for keyboard users
        var firstLink = sidebar.querySelector('a');
        if (firstLink) setTimeout(function() { firstLink.focus(); }, 100);
      }
    }

    hamburger.addEventListener('click', function() {
      setDrawer(sidebar.getAttribute('data-open') !== 'true');
    });

    // Backdrop（移动端遮罩）
    var backdrop = el('div', { id: 'ray-sidebar-backdrop' });
    backdrop.addEventListener('click', function() { setDrawer(false); });

    // 点击 sidebar 内的链接后自动关闭 drawer（移动端）
    sidebar.addEventListener('click', function(e) {
      if (e.target.tagName === 'A' && window.innerWidth <= 1100) setDrawer(false);
    });

    // Esc 关闭 drawer
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape' && sidebar.getAttribute('data-open') === 'true') {
        setDrawer(false);
        hamburger.focus();
      }
    });

    // 注入 DOM
    document.body.insertBefore(sidebar, document.body.firstChild);
    document.body.insertBefore(hamburger, document.body.firstChild);
    document.body.appendChild(backdrop);

    // 标记 body：让 sidebar.css 中受 body.rs-active 限定的规则生效
    document.body.classList.add('rs-active');

    // ----- 章节高亮（IntersectionObserver） -----
    if (sections.length > 0 && 'IntersectionObserver' in window) {
      var tocLinks = sidebar.querySelectorAll('.rs-toc-list a');
      var observer = new IntersectionObserver(function(entries) {
        entries.forEach(function(entry) {
          if (entry.isIntersecting) {
            tocLinks.forEach(function(link) {
              link.classList.toggle('rs-active', link.dataset.targetId === entry.target.id);
            });
          }
        });
      }, { rootMargin: '-30% 0px -60% 0px' });
      sections.forEach(function(s) { observer.observe(s); });
    }
  }

  // ----- Bootstrap -----
  function init() {
    fetch(MANIFEST_URL, { cache: 'no-cache' })
      .then(function(res) {
        if (!res.ok) throw new Error('manifest HTTP ' + res.status);
        return res.json();
      })
      .then(function(raw) {
        var clean = sanitizeManifest(raw);
        render(clean);
      })
      .catch(function(err) {
        // 加载失败：移除 rs-active class，让原有布局（含原 nav.toc）恢复
        document.body.classList.remove('rs-active');
        console.warn('[ray-sidebar] 加载失败：', err && err.message ? err.message : err,
          '— 已降级为原始报告布局（含原章节 TOC）');
      });
  }

  // 即使 fetch 失败，也要确保 body 没有残留 rs-active（HTML 静态写了 class 时）
  // 进入 init 之前先确保 class 存在（让 sidebar 布局立即生效避免 FOUC）
  if (document.body) {
    document.body.classList.add('rs-active');
  } else {
    document.addEventListener('DOMContentLoaded', function() {
      document.body.classList.add('rs-active');
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
