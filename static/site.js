// site.js — маленькие «оживляющие» функции сайта: поиск в шапке и сортировка таблиц.
// Работает без интернета и без сервера: индекс поиска лежит в search-index.js.

(function () {
  // Корень сайта относительно текущей страницы, например "../../../"
  var root = document.body.getAttribute('data-root') || '';

  // ---------- ПОИСК ----------
  // Приводим текст к «простому виду»: строчные буквы, ё → е, без французских accents (é → e).
  function norm(s) {
    return (s || '').toLowerCase().replace(/ё/g, 'е')
      .normalize('NFD').replace(/[̀-ͯ]/g, '');
  }
  var input = document.getElementById('q');
  var box = document.getElementById('results');
  var index = (window.SEARCH_INDEX || []).map(function (it) {
    it._n = norm(it.t + ' ' + it.l + ' ' + it.w);   // заранее готовим текст для сравнения
    return it;
  });

  function search(q) {
    var words = norm(q).split(/\s+/).filter(Boolean);
    if (!words.length) return [];
    return index.filter(function (it) {
      // подходит, если КАЖДОЕ слово запроса встречается в тексте записи
      return words.every(function (w) { return it._n.indexOf(w) !== -1; });
    }).slice(0, 12);
  }

  function show(list, q) {
    if (!q) { box.hidden = true; return; }
    box.hidden = false;
    if (!list.length) { box.innerHTML = '<div class="r-empty">Ничего не нашлось</div>'; return; }
    box.innerHTML = list.map(function (it) {
      return '<a href="' + root + it.u + '"><b>' + it.t + '</b>' + (it.l ? ' <i>' + it.l + '</i>' : '') +
        '<span>' + it.k + (it.c ? ' · ' + it.c : '') + '</span></a>';
    }).join('');
  }

  if (input) {
    input.addEventListener('input', function () { show(search(input.value), input.value.trim()); });
    input.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') { var a = box.querySelector('a'); if (a) location.href = a.href; }
      if (e.key === 'Escape') { input.value = ''; box.hidden = true; }
    });
    document.addEventListener('click', function (e) {
      if (!e.target.closest('.search')) box.hidden = true;
    });
  }

  // ---------- ФИЛЬТР «ГДЕ + ПОИСК» (История, Статистика, Статьи) ----------
  // Элементы с атрибутом data-path внутри [data-items] показываются или прячутся.
  // Элемент подходит, если его место лежит ВНУТРИ выбранного (Франция → все её регионы и AOC).
  // У статей место может быть и ВЫШЕ выбранного: статья о Луаре видна, если выбран Бургёй.
  var bar = document.querySelector('[data-filter]');
  if (bar) {
    var sel = bar.querySelector('[data-place]');
    var q = bar.querySelector('[data-q]');
    var counter = bar.querySelector('[data-count]');
    var items = Array.prototype.slice.call(document.querySelectorAll('[data-items] [data-path]'));
    var groups = document.querySelectorAll('[data-group]');
    var empty = document.querySelector('[data-empty]');
    var isArticles = !!document.querySelector('[data-tags]');
    var tag = '';

    function inside(path, place) {
      if (!place) return true;
      return path.split(' ').some(function (p) {
        if (p === place || p.indexOf(place + '/') === 0) return true;          // ниже выбранного
        return isArticles && place.indexOf(p + '/') === 0;                    // выше (только статьи)
      });
    }

    function apply() {
      var place = sel ? sel.value : '';
      var words = norm(q.value).split(/\s+/).filter(Boolean);
      var shown = 0;
      items.forEach(function (el) {
        var text = norm(el.getAttribute('data-text') || el.textContent);
        var ok = inside(el.getAttribute('data-path'), place) &&
                 words.every(function (w) { return text.indexOf(w) !== -1; }) &&
                 (!tag || (el.getAttribute('data-tags') || '').split('|').indexOf(tag) !== -1);
        el.hidden = !ok;
        if (ok) shown++;
      });
      // века (группы), в которых не осталось событий, прячем целиком
      groups.forEach(function (g) { g.hidden = !g.querySelector('[data-path]:not([hidden])'); });
      if (empty) empty.hidden = shown > 0;
      if (counter) counter.textContent = 'показано: ' + shown + ' из ' + items.length;
      // запоминаем выбранное место в адресе (#france/loire), чтобы ссылкой можно было поделиться
      if (sel) history.replaceState(null, '', place ? '#' + place : location.pathname);
    }

    // место из адреса: history.html#france/loire → сразу выбрать «Долина Луары»
    var fromHash = decodeURIComponent(location.hash.slice(1));
    if (sel && fromHash && sel.querySelector('option[value="' + fromHash + '"]')) sel.value = fromHash;
    if (sel) sel.addEventListener('change', apply);
    q.addEventListener('input', apply);
    document.querySelectorAll('[data-tags] .chip').forEach(function (b) {
      b.addEventListener('click', function () {
        tag = b.getAttribute('data-tag');
        document.querySelectorAll('[data-tags] .chip').forEach(function (x) { x.classList.toggle('on', x === b); });
        apply();
      });
    });
    apply();
  }

  // ---------- ДЕРЕВО РЕГИОНОВ: поиск, «развернуть/свернуть всё» ----------
  var tree = document.getElementById('tree');
  if (tree) {
    var tq = document.getElementById('tree-q');
    var nodes = tree.querySelectorAll('details.node');
    document.querySelectorAll('[data-tree]').forEach(function (b) {
      b.addEventListener('click', function () {
        var open = b.getAttribute('data-tree') === 'open';
        nodes.forEach(function (d) { d.open = open; });
      });
    });
    tq.addEventListener('input', function () {
      var w = norm(tq.value.trim());
      var any = false;
      // сначала проверяем «листья» и узлы: подходит ли их собственное название
      tree.querySelectorAll('[data-name]').forEach(function (el) {
        el._hit = !w || norm(el.getAttribute('data-name')).indexOf(w) !== -1;
      });
      // узел показываем, если подходит он сам или кто-то внутри; при поиске — раскрываем
      function visit(el) {
        var kids = el.querySelectorAll(':scope > .node-kids > [data-name]');
        var inner = false;
        kids.forEach(function (k) { if (visit(k)) inner = true; });
        var show = el._hit || inner;
        // если совпал сам узел — показываем всех его детей
        if (el._hit && w) kids.forEach(function (k) { k.hidden = false; });
        el.hidden = !show;
        if (el.tagName === 'DETAILS') el.open = !!w && inner;
        return show;
      }
      tree.querySelectorAll(':scope > [data-name]').forEach(function (top) { if (visit(top)) any = true; });
      document.getElementById('tree-empty').hidden = any;
    });
  }

  // ---------- ОГЛАВЛЕНИЕ СБОКУ, КНОПКИ «РАЗДЕЛЫ» И «НАВЕРХ» ----------
  var toc = document.getElementById('side-toc');
  // кнопки появляются, когда страницу прокрутили ниже первого экрана
  window.addEventListener('scroll', function () {
    document.body.classList.toggle('scrolled', window.scrollY > window.innerHeight * 0.8);
  }, { passive: true });
  var tocBtn = document.getElementById('toc-btn');
  if (toc && tocBtn) {
    tocBtn.addEventListener('click', function () { toc.classList.toggle('open'); });
    toc.addEventListener('click', function (e) { if (e.target.tagName === 'A') toc.classList.remove('open'); });
  }
  // подсветка раздела, который сейчас на экране
  if (toc && 'IntersectionObserver' in window) {
    var links = {};
    toc.querySelectorAll('a').forEach(function (a) { links[a.getAttribute('href').slice(1)] = a; });
    var obs = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting && links[en.target.id]) {
          toc.querySelectorAll('a.on').forEach(function (a) { a.classList.remove('on'); });
          links[en.target.id].classList.add('on');
        }
      });
    }, { rootMargin: '-20% 0px -70% 0px' });
    document.querySelectorAll('section[id]').forEach(function (s) { obs.observe(s); });
  }
  // подсказка «прокрутите вбок» над широкими диаграммами на телефоне
  document.querySelectorAll('figure:not(.minimap) svg').forEach(function (svg) {
    var hint = document.createElement('span');
    hint.className = 'scroll-hint';
    hint.textContent = '← прокрутите картинку вбок →';
    svg.parentNode.insertBefore(hint, svg);
  });

  // ---------- СОРТИРОВКА ТАБЛИЦ (раздел «Статистика») ----------
  document.querySelectorAll('table.sortable').forEach(function (table) {
    // на телефоне заголовков столбцов не видно (таблица карточками) — даём выпадающий список «Сортировать по»
    var bar = document.createElement('label');
    bar.className = 'sort-m';
    var html = 'Сортировать по <select><option value="">—</option>';
    table.querySelectorAll('th').forEach(function (th, i) { html += '<option value="' + i + '">' + th.textContent + '</option>'; });
    bar.innerHTML = html + '</select>';
    (table.closest('.table-wrap') || table).before(bar);
    bar.querySelector('select').addEventListener('change', function (e) {
      if (e.target.value !== '') table.querySelectorAll('th')[e.target.value].click();
    });
    table.querySelectorAll('th').forEach(function (th, col) {
      th.style.cursor = 'pointer';
      th.title = 'Сортировать';
      var asc = false;
      th.addEventListener('click', function () {
        asc = !asc;
        var num = th.hasAttribute('data-num');
        var body = table.tBodies[0];
        var rows = Array.prototype.slice.call(body.rows);
        rows.sort(function (a, b) {
          var x = a.cells[col], y = b.cells[col];
          var vx = num ? parseFloat(x.getAttribute('data-v')) || 0 : x.textContent;
          var vy = num ? parseFloat(y.getAttribute('data-v')) || 0 : y.textContent;
          return (vx > vy ? 1 : vx < vy ? -1 : 0) * (asc ? 1 : -1);
        });
        rows.forEach(function (r) { body.appendChild(r); });
        // стрелка у заголовка показывает, по чему и в какую сторону отсортировано
        table.querySelectorAll('th').forEach(function (x) { x.removeAttribute('data-sort'); });
        th.setAttribute('data-sort', asc ? '▲' : '▼');
      });
    });
  });
})();
