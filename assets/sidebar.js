// ===== Ray Research · Global Sidebar Renderer =====
// 工作流：
// 1. 从当前 URL 推断 base path 和当前位置（哪个话题/报告打开）
// 2. fetch manifest.json 拿话题数据
// 3. 渲染 sidebar HTML 注入 body
// 4. 解析当前页面 section[id] 构建当前报告章节列表
// 5. IntersectionObserver 滚动跟随高亮章节

(function() {
  'use strict';

  // ----- 路径推断 -----
  function inferBase() {
    // GitHub Pages 上 /ray-research/... ；本地 / ；Cloudflare /
    var path = window.location.pathname;
    var match = path.match(/^(\/[^\/]+\/)/);
    if (match && /ray-research/i.test(match[1])) return match[1];
    return '/';
  }
  var BASE = inferBase();
  var MANIFEST_URL = BASE + 'manifest.json';

  // 推断当前位置
  function inferCurrent() {
    var path = window.location.pathname.replace(BASE, '/').replace(/^\//, '');
    var parts = path.split('/').filter(Boolean);
    if (parts.length === 0) return { topic: null, file: null }; // 主页
    if (parts.length === 1) {
      // 可能是 typeless/ 或 typeless/index.html
      return { topic: parts[0].replace(/\.html$/, ''), file: null };
    }
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

  // ----- Sidebar HTML 渲染 -----
  function render(manifest) {
    var current = inferCurrent();

    var sidebar = el('aside', { id: 'ray-sidebar' });

    // Brand
    var brand = el('a', { class: 'rs-brand', href: BASE }, [
      el('strong', { text: manifest.site.name }),
      el('span', { text: manifest.site.tagline })
    ]);
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
          text: r.date
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

    // Hamburger button
    var hamburger = el('button', {
      id: 'ray-sidebar-toggle',
      'aria-label': '打开/关闭导航',
      title: '打开/关闭导航',
      html: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M3 6h18M3 12h18M3 18h18"/></svg>'
    });
    hamburger.addEventListener('click', function() {
      var open = sidebar.getAttribute('data-open') === 'true';
      sidebar.setAttribute('data-open', open ? 'false' : 'true');
    });

    // Backdrop（移动端遮罩）
    var backdrop = el('div', { id: 'ray-sidebar-backdrop' });
    backdrop.addEventListener('click', function() {
      sidebar.setAttribute('data-open', 'false');
    });

    // 点击 sidebar 内的链接后自动关闭 drawer（移动端）
    sidebar.addEventListener('click', function(e) {
      if (e.target.tagName === 'A' && window.innerWidth <= 1100) {
        sidebar.setAttribute('data-open', 'false');
      }
    });

    // 注入到 body 开头
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
        if (!res.ok) throw new Error('manifest 404');
        return res.json();
      })
      .then(render)
      .catch(function(err) {
        console.warn('[ray-sidebar] 加载失败：', err.message, '— 可能是本地 file:// 模式或 manifest 缺失');
      });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
