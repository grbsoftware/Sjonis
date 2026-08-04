/* =============================================================================
   UI SUITE — BEHAVIOUR (layer 2)

   ui.css is a faceplate: it can show a menu, but nothing opens it. This file is
   the wiring. It adds no markup style and no colour — it only toggles state that
   ui.css already describes.

   Deliberate constraints, and why:

   • A CLASSIC SCRIPT, NOT AN ES MODULE. Modules are blocked on file:// by CORS,
     and half of this suite's value is that a single .html file opens by double-
     clicking it. <script src="../core/ui.js"></script> and you have UI.
   • NO DEPENDENCIES, NO BUILD, NO FRAMEWORK. Consumers of layer 1 paid nothing;
     layer 2 keeps that promise.
   • DECLARATIVE FIRST. Behaviour is attached by data-attributes in the markup,
     so a page can be written by hand or generated, with no init code to forget.
   • USE THE PLATFORM. <dialog> for modals, <details> for accordions, the
     constraint-validation API for forms. Every one of those is a focus trap or
     a state machine we would otherwise get subtly wrong.

   Everything degrades: with this file removed, dialogs stay closed, menus stay
   closed, all tab panels render stacked, and forms fall back to native validation.

   Usage:  UI.init()            — called for you on DOMContentLoaded
           UI.init(container)   — call again after you inject markup (idempotent)
   ============================================================================= */
(function (global) {
  'use strict';

  var UI = {};
  var STORE = 'ui-suite';

  /* ---------------------------------------------------------------------------
     Small helpers. Not a utility library — just the four things used everywhere.
     ------------------------------------------------------------------------ */
  function $(sel, root) { return (root || document).querySelector(sel); }
  function $$(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }
  function on(el, ev, fn, opts) { el.addEventListener(ev, fn, opts); }

  /* Marks an element as wired so UI.init() can be re-run over the same DOM
     after injecting markup without doubling every handler.

     Held in a WeakMap, NOT in a data-attribute. A flag like dataset.uiMenu is
     the same attribute as data-ui-menu — writing the flag overwrites the
     selector it was about to read. Off-DOM state cannot collide with markup,
     and it is collected with the node. */
  var wired = new WeakMap();
  function claim(el, key) {
    var keys = wired.get(el);
    if (!keys) { keys = {}; wired.set(el, keys); }
    if (keys[key]) return false;
    keys[key] = true;
    return true;
  }

  /* Focusable descendants, in tab order. Used for menus and the palette; the
     native <dialog> handles its own, which is exactly why we use it. */
  var FOCUSABLE = 'a[href],button:not([disabled]),input:not([disabled]),' +
                  'select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])';
  function focusables(root) {
    return $$(FOCUSABLE, root).filter(function (el) {
      return el.offsetWidth || el.offsetHeight || el.getClientRects().length;
    });
  }

  /* ---------------------------------------------------------------------------
     POSITIONING
     One anchored-element placer, shared by menus and tooltips. Flips rather than
     clamps: a menu shoved back on-screen overlaps its own trigger, which reads
     as a rendering bug. Coordinates are page-space because anchored elements are
     moved to <body> — inside a card with overflow:hidden they would be clipped.
     ------------------------------------------------------------------------ */
  function place(el, anchor, opts) {
    opts = opts || {};
    var gap = opts.gap == null ? 6 : opts.gap;
    var a = anchor.getBoundingClientRect();
    var vw = document.documentElement.clientWidth;
    var vh = document.documentElement.clientHeight;

    el.style.visibility = 'hidden';
    el.style.display = 'block';
    var w = el.offsetWidth, h = el.offsetHeight;
    el.style.display = '';
    el.style.visibility = '';

    var top = a.bottom + gap;
    if (top + h > vh - 4 && a.top - gap - h > 4) top = a.top - gap - h;

    var left = opts.align === 'end' ? a.right - w : a.left;
    if (opts.align === 'center') left = a.left + (a.width - w) / 2;
    if (left + w > vw - 4) left = vw - 4 - w;
    if (left < 4) left = 4;

    el.style.top = (top + window.scrollY) + 'px';
    el.style.left = (left + window.scrollX) + 'px';
  }

  /* ---------------------------------------------------------------------------
     DIALOG
       <button data-ui-open="#confirm">      opens it
       <dialog class="ui-dialog" id="confirm"> … <button data-ui-close>Cancel</button>

     showModal() gives us the focus trap, the inert background, Escape and the
     top layer for free. The only things left to add are click-outside-to-close
     and returning focus to whatever opened it.
     ------------------------------------------------------------------------ */
  function openDialog(dlg, opener) {
    if (!dlg) return;
    dlg._uiOpener = opener || document.activeElement;
    if (typeof dlg.showModal === 'function') dlg.showModal();
    else dlg.setAttribute('open', '');            /* ancient engines: no trap, but visible */
    var first = $('[data-ui-autofocus]', dlg) || focusables(dlg)[0];
    if (first) first.focus();
  }

  function closeDialog(dlg, value) {
    if (!dlg) return;
    if (typeof dlg.close === 'function') dlg.close(value == null ? '' : value);
    else dlg.removeAttribute('open');
  }

  function wireDialogs(root) {
    $$('[data-ui-open]', root).forEach(function (btn) {
      if (!claim(btn, 'Open')) return;
      on(btn, 'click', function (e) {
        e.preventDefault();
        openDialog($(btn.getAttribute('data-ui-open')), btn);
      });
    });

    $$('dialog.ui-dialog', root).forEach(function (dlg) {
      if (!claim(dlg, 'Dlg')) return;

      $$('[data-ui-close]', dlg).forEach(function (btn) {
        on(btn, 'click', function () { closeDialog(dlg, btn.getAttribute('data-ui-close') || 'close'); });
      });

      /* The backdrop is part of the dialog element, so a click that lands on the
         dialog itself — rather than on any child — landed outside the panel. */
      on(dlg, 'click', function (e) {
        if (e.target !== dlg || dlg.hasAttribute('data-ui-static')) return;
        var r = dlg.getBoundingClientRect();
        var inside = e.clientX >= r.left && e.clientX <= r.right &&
                     e.clientY >= r.top && e.clientY <= r.bottom;
        if (!inside) closeDialog(dlg, 'dismiss');
      });

      on(dlg, 'close', function () {
        if (dlg._uiOpener && document.contains(dlg._uiOpener)) dlg._uiOpener.focus();
      });
    });
  }

  UI.open = function (sel) { openDialog(typeof sel === 'string' ? $(sel) : sel); };
  UI.close = function (sel, v) { closeDialog(typeof sel === 'string' ? $(sel) : sel, v); };

  /* A promise-based confirm, because window.confirm cannot be themed and blocks
     the thread. Built on the same <dialog>, torn down after use. */
  UI.confirm = function (opts) {
    opts = opts || {};
    return new Promise(function (resolve) {
      var dlg = document.createElement('dialog');
      dlg.className = 'ui-dialog';
      dlg.innerHTML =
        '<div class="ui-dialog-head"><h2 class="ui-title"></h2></div>' +
        '<div class="ui-dialog-body"><p style="margin:0"></p></div>' +
        '<div class="ui-dialog-foot">' +
          '<button class="ui-btn-ghost" data-ui-close="cancel"></button>' +
          '<button data-ui-autofocus></button>' +
        '</div>';
      $('.ui-title', dlg).textContent = opts.title || 'Are you sure?';
      $('p', dlg).textContent = opts.body || '';
      $('[data-ui-close]', dlg).textContent = opts.cancelText || 'Cancel';
      var go = $('[data-ui-autofocus]', dlg);
      go.textContent = opts.confirmText || 'Confirm';
      go.className = opts.tone === 'danger' ? 'ui-btn-danger' : 'ui-btn';
      on(go, 'click', function () { closeDialog(dlg, 'confirm'); });

      on($('[data-ui-close]', dlg), 'click', function () { closeDialog(dlg, 'cancel'); });
      (($('.ui') || document.body)).appendChild(dlg);
      on(dlg, 'close', function () {
        var ok = dlg.returnValue === 'confirm';
        dlg.remove();
        resolve(ok);
      });
      openDialog(dlg);
    });
  };

  /* ---------------------------------------------------------------------------
     MENU
       <button data-ui-menu="#actions">Actions</button>
       <div class="ui-menu" id="actions" role="menu"> <button class="ui-menu-item" role="menuitem">…

     Arrow keys move, Home/End jump, Escape closes and returns focus, typing a
     letter jumps to the next item starting with it. That last one is the part
     everybody skips and keyboard users notice.
     ------------------------------------------------------------------------ */
  var openMenu = null;

  function closeMenu(refocus) {
    if (!openMenu) return;
    var m = openMenu, t = m._uiTrigger;
    openMenu = null;
    m.classList.remove('is-open');
    if (t) t.setAttribute('aria-expanded', 'false');
    if (refocus && t) t.focus();
  }

  function showMenu(menu, trigger) {
    closeMenu(false);
    menu._uiTrigger = trigger;
    menu.classList.add('is-open');
    trigger.setAttribute('aria-expanded', 'true');
    place(menu, trigger, { align: menu.getAttribute('data-ui-align') || 'start' });
    openMenu = menu;
    var first = $('.ui-menu-item:not([disabled])', menu);
    if (first) first.focus();
  }

  function menuKeys(menu, e) {
    var items = $$('.ui-menu-item:not([disabled])', menu);
    var i = items.indexOf(document.activeElement);
    var k = e.key;

    if (k === 'Escape') { e.preventDefault(); closeMenu(true); return; }
    if (k === 'Tab') { closeMenu(false); return; }
    if (k === 'ArrowDown' || k === 'ArrowUp' || k === 'Home' || k === 'End') {
      e.preventDefault();
      var n = k === 'Home' ? 0
            : k === 'End' ? items.length - 1
            : k === 'ArrowDown' ? (i + 1) % items.length
            : (i - 1 + items.length) % items.length;
      if (items[n]) items[n].focus();
      return;
    }
    if (k.length === 1 && /\S/.test(k)) {
      var c = k.toLowerCase(), start = i + 1;
      for (var n2 = 0; n2 < items.length; n2++) {
        var it = items[(start + n2) % items.length];
        if (it.textContent.trim().toLowerCase().indexOf(c) === 0) { it.focus(); return; }
      }
    }
  }

  function wireMenus(root) {
    $$('[data-ui-menu]', root).forEach(function (trigger) {
      if (!claim(trigger, 'Menu')) return;
      var menu = $(trigger.getAttribute('data-ui-menu'));
      if (!menu) return;

      trigger.setAttribute('aria-haspopup', 'menu');
      trigger.setAttribute('aria-expanded', 'false');
      if (!menu.getAttribute('role')) menu.setAttribute('role', 'menu');
      $$('.ui-menu-item', menu).forEach(function (it) {
        if (!it.getAttribute('role')) it.setAttribute('role', 'menuitem');
      });
      /* Escape the nearest overflow:hidden ancestor — but land on the .ui root,
         not <body>, or the menu is re-parented out of its own theme. */
      var host = trigger.closest('.ui') || document.body;
      if (menu.parentNode !== host) host.appendChild(menu);

      on(trigger, 'click', function (e) {
        e.preventDefault(); e.stopPropagation();
        if (openMenu === menu) closeMenu(true); else showMenu(menu, trigger);
      });
      on(trigger, 'keydown', function (e) {
        if (e.key === 'ArrowDown' || e.key === 'Enter' || e.key === ' ') {
          e.preventDefault(); showMenu(menu, trigger);
        }
      });
      on(menu, 'keydown', function (e) { menuKeys(menu, e); });
      on(menu, 'click', function (e) {
        if (e.target.closest('.ui-menu-item')) closeMenu(true);
      });
    });
  }

  /* One document-level listener for all menus, rather than one per menu. */
  on(document, 'click', function (e) {
    if (openMenu && !openMenu.contains(e.target) && e.target !== openMenu._uiTrigger) closeMenu(false);
  });
  on(window, 'resize', function () { closeMenu(false); });
  on(window, 'scroll', function () { closeMenu(false); }, true);

  /* ---------------------------------------------------------------------------
     TABS
       <div data-ui-tabs>
         <div class="ui-tablist" role="tablist">
           <button class="ui-tab" aria-controls="p1">…
         <section class="ui-tabpanel" id="p1">…

     Roles and hidden state are applied here, not asked of the author, so hand-
     written markup cannot get the ARIA half-right. With JS off nothing is hidden.
     ------------------------------------------------------------------------ */
  function selectTab(tabs, tab) {
    $$('.ui-tab', tabs).forEach(function (t) {
      var sel = t === tab;
      t.setAttribute('aria-selected', sel ? 'true' : 'false');
      t.tabIndex = sel ? 0 : -1;
      var panel = document.getElementById(t.getAttribute('aria-controls'));
      if (panel) panel.hidden = !sel;
    });
  }

  function wireTabs(root) {
    $$('[data-ui-tabs]', root).forEach(function (tabs) {
      if (!claim(tabs, 'Tabs')) return;
      var list = $('.ui-tablist', tabs) || tabs;
      list.setAttribute('role', 'tablist');
      var all = $$('.ui-tab', tabs);

      all.forEach(function (t, i) {
        t.setAttribute('role', 'tab');
        var panel = document.getElementById(t.getAttribute('aria-controls'));
        if (panel) { panel.setAttribute('role', 'tabpanel'); panel.tabIndex = 0; }
        on(t, 'click', function () { selectTab(tabs, t); });
        on(t, 'keydown', function (e) {
          var d = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1
                : e.key === 'Home' ? -Infinity : e.key === 'End' ? Infinity : 0;
          if (!d) return;
          e.preventDefault();
          var n = d === -Infinity ? 0 : d === Infinity ? all.length - 1
                : (i + d + all.length) % all.length;
          all[n].focus(); selectTab(tabs, all[n]);
        });
      });

      selectTab(tabs, $('.ui-tab[aria-selected="true"]', tabs) || all[0]);
    });
  }

  /* ---------------------------------------------------------------------------
     ACCORDION — native <details> already works. Script adds only the
     one-open-at-a-time variant: <div class="ui-accordion" data-ui-accordion="single">
     ------------------------------------------------------------------------ */
  function wireAccordions(root) {
    $$('[data-ui-accordion="single"]', root).forEach(function (acc) {
      if (!claim(acc, 'Acc')) return;
      $$('details', acc).forEach(function (d) {
        on(d, 'toggle', function () {
          if (!d.open) return;
          $$('details', acc).forEach(function (o) { if (o !== d) o.open = false; });
        });
      });
    });
  }

  /* ---------------------------------------------------------------------------
     TOAST
       UI.toast('Saved', { tone:'good', timeout:4000 })

     role="status" (polite) rather than alert, so a save confirmation does not
     interrupt a screen-reader user mid-sentence. Pass tone:'crit' for alert.
     ------------------------------------------------------------------------ */
  UI.toast = function (msg, opts) {
    opts = opts || {};
    var host = $('.ui-toasts');
    if (!host) {
      host = document.createElement('div');
      host.className = 'ui-toasts';
      /* .ui carries the theme; a toast on <body> would render unthemed. */
      (($('.ui') || document.body)).appendChild(host);
    }
    var t = document.createElement('div');
    t.className = 'ui-toast' + (opts.tone ? ' ui-toast-' + opts.tone : '');
    t.setAttribute('role', opts.tone === 'crit' ? 'alert' : 'status');
    t.textContent = msg;
    host.appendChild(t);

    var life = opts.timeout == null ? 3600 : opts.timeout;
    if (life > 0) setTimeout(function () {
      t.classList.add('is-leaving');
      setTimeout(function () { t.remove(); }, 200);
    }, life);
    return t;
  };

  /* ---------------------------------------------------------------------------
     TOOLTIP —  <button data-ui-tip="Copy to clipboard">
     Shown on hover AND focus; a hover-only tooltip does not exist for keyboards.
     ------------------------------------------------------------------------ */
  var tipEl = null;
  function hideTip() { if (tipEl) { tipEl.remove(); tipEl = null; } }
  function showTip(el) {
    hideTip();
    tipEl = document.createElement('div');
    tipEl.className = 'ui-tip';
    tipEl.setAttribute('role', 'tooltip');
    tipEl.textContent = el.getAttribute('data-ui-tip');
    (($('.ui') || document.body)).appendChild(tipEl);
    place(tipEl, el, { gap: 5, align: 'center' });
  }

  function wireTips(root) {
    $$('[data-ui-tip]', root).forEach(function (el) {
      if (!claim(el, 'Tip')) return;
      if (!el.getAttribute('aria-label') && !el.textContent.trim()) {
        el.setAttribute('aria-label', el.getAttribute('data-ui-tip'));
      }
      on(el, 'pointerenter', function () { showTip(el); });
      on(el, 'pointerleave', hideTip);
      on(el, 'focus', function () { showTip(el); });
      on(el, 'blur', hideTip);
    });
  }
  on(document, 'keydown', function (e) { if (e.key === 'Escape') hideTip(); });

  /* ---------------------------------------------------------------------------
     TABLE SORT —  <table class="ui-table" data-ui-sort>
     Cells may carry data-sort-value to sort by something other than what they
     show ("2 min ago" → a timestamp). Otherwise numbers sort numerically and
     text sorts with localeCompare, so "item 10" lands after "item 9".
     ------------------------------------------------------------------------ */
  function cellValue(row, i) {
    var td = row.cells[i];
    if (!td) return '';
    var v = td.getAttribute('data-sort-value');
    return v == null ? td.textContent.trim() : v;
  }

  /* Real table cells carry units and separators: "12 ms", "1 240 ms", "99.98%",
     "$1,204". A plain Number() on those yields NaN, the column silently falls
     back to text collation, and "1 240 ms" sorts before "9 ms" — which looks
     like the sort is simply broken. So: strip group separators and a leading
     currency mark, then take the number off the front and ignore any trailing
     unit. Anything not STARTING with a number ("edge-01") stays text. */
  function asNumber(v) {
    var m = String(v).replace(/[\s, ]/g, '').replace(/^[$€£]/, '').match(/^[-+]?\d*\.?\d+/);
    return m ? parseFloat(m[0]) : NaN;
  }

  function wireSort(root) {
    $$('table[data-ui-sort]', root).forEach(function (table) {
      if (!claim(table, 'Sort')) return;
      var body = table.tBodies[0];
      if (!body) return;

      $$('thead th', table).forEach(function (th, i) {
        if (th.hasAttribute('data-sort-none')) return;
        th.setAttribute('aria-sort', 'none');
        th.tabIndex = 0;

        function run() {
          var dir = th.getAttribute('aria-sort') === 'ascending' ? -1 : 1;
          $$('thead th', table).forEach(function (o) {
            if (o.hasAttribute('aria-sort')) o.setAttribute('aria-sort', 'none');
          });
          th.setAttribute('aria-sort', dir === 1 ? 'ascending' : 'descending');

          var rows = $$('tr', body);
          var numeric = rows.every(function (r) {
            var v = cellValue(r, i);
            return v === '' || !isNaN(asNumber(v));
          });
          rows.sort(function (a, b) {
            var x = cellValue(a, i), y = cellValue(b, i);
            if (numeric) return dir * ((asNumber(x) || 0) - (asNumber(y) || 0));
            return dir * x.localeCompare(y, undefined, { numeric: true, sensitivity: 'base' });
          });
          rows.forEach(function (r) { body.appendChild(r); });
        }

        on(th, 'click', run);
        on(th, 'keydown', function (e) {
          if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); run(); }
        });
      });
    });
  }

  /* ---------------------------------------------------------------------------
     FILTER —  <input data-ui-filter="#hosts">  hides non-matching rows or list
     items in the target. Announces the count, because a list that silently
     shrinks is a list that looks broken.
     ------------------------------------------------------------------------ */
  function wireFilter(root) {
    $$('[data-ui-filter]', root).forEach(function (input) {
      if (!claim(input, 'Filter')) return;
      var target = $(input.getAttribute('data-ui-filter'));
      if (!target) return;
      var status = input.getAttribute('data-ui-filter-status')
        ? $(input.getAttribute('data-ui-filter-status')) : null;

      on(input, 'input', function () {
        var q = input.value.trim().toLowerCase();
        var items = target.tBodies && target.tBodies[0]
          ? $$('tr', target.tBodies[0]) : $$('.ui-list-item,.ui-row', target);
        var shown = 0;
        items.forEach(function (el) {
          var hit = !q || el.textContent.toLowerCase().indexOf(q) !== -1;
          el.hidden = !hit;
          if (hit) shown++;
        });
        if (status) status.textContent = shown + ' of ' + items.length;
      });
    });
  }

  /* ---------------------------------------------------------------------------
     COPY —  <button data-ui-copy="#snippet">  or  data-ui-copy-text="…"
     ------------------------------------------------------------------------ */
  function wireCopy(root) {
    $$('[data-ui-copy],[data-ui-copy-text]', root).forEach(function (btn) {
      if (!claim(btn, 'Copy')) return;
      on(btn, 'click', function () {
        var text = btn.getAttribute('data-ui-copy-text');
        if (text == null) {
          var src = $(btn.getAttribute('data-ui-copy'));
          text = src ? (src.value != null && src.value !== '' ? src.value : src.textContent) : '';
        }
        var done = function () { UI.toast('Copied', { tone: 'good', timeout: 1800 }); };
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(text).then(done, function () {
            UI.toast('Copy blocked by the browser', { tone: 'warn' });
          });
        } else {
          /* file:// and older engines have no async clipboard. */
          var ta = document.createElement('textarea');
          ta.value = text; ta.style.position = 'fixed'; ta.style.opacity = '0';
          document.body.appendChild(ta); ta.select();
          try { document.execCommand('copy'); done(); } catch (e) { UI.toast('Copy failed', { tone: 'warn' }); }
          ta.remove();
        }
      });
    });
  }

  /* ---------------------------------------------------------------------------
     MARQUEE —  <div class="ui-marquee" data-ui-marquee="60">
                  <div class="ui-marquee-track"> …items… </div>

     The attribute value is the seconds for one full cycle. The track's items are
     cloned once, here rather than in the markup, so the author writes each item
     exactly once and the seamless loop is not their problem. Clones are
     aria-hidden and taken out of the tab order — a screen reader hearing every
     caption twice is the usual cost of this effect, and it is avoidable.

     Click pauses for a while and then resumes, which is what you want when
     something catches your eye mid-scroll. Hover and focus pause too, but in
     CSS, because those must not fight the timer.
     ------------------------------------------------------------------------ */
  var MARQUEE_RESUME = 10000;

  function wireMarquee(root) {
    $$('[data-ui-marquee]', root).forEach(function (box) {
      if (!claim(box, 'Marq')) return;
      var track = $('.ui-marquee-track', box);
      if (!track) return;

      var secs = parseFloat(box.getAttribute('data-ui-marquee')) || 60;
      box.style.setProperty('--ui-marquee-dur', secs + 's');

      /* Duplicate once. Any element that could take focus or be read is muted
         in the copy, so the clone is decoration only. */
      var copy = document.createDocumentFragment();
      $$(':scope > *', track).forEach(function (item) {
        var c = item.cloneNode(true);
        c.setAttribute('aria-hidden', 'true');
        $$('a,button,input,[tabindex]', c).concat(c.matches('a,button') ? [c] : [])
          .forEach(function (f) { f.tabIndex = -1; });
        copy.appendChild(c);
      });
      track.appendChild(copy);

      /* Lazy frames inside the marquee never intersect predictably while they
         are translating, so load them up front — there are only a handful. */
      $$('.ui-frame[data-ui-lazy]', track).forEach(loadLazy);

      var timer = null;
      function resumeLater() {
        clearTimeout(timer);
        timer = setTimeout(function () { box.classList.remove('is-paused'); }, MARQUEE_RESUME);
      }
      on(box, 'click', function (e) {
        /* A click on a real link should follow it, not just pause. */
        if (e.target.closest('a[href]:not([href="#"])')) return;
        e.preventDefault();
        if (box.classList.contains('is-paused')) {
          clearTimeout(timer);
          box.classList.remove('is-paused');
        } else {
          box.classList.add('is-paused');
          resumeLater();
        }
      });

      /* An off-screen tab animating forever is a laptop-battery bug. */
      on(document, 'visibilitychange', function () {
        track.style.animationPlayState = document.hidden ? 'paused' : '';
      });
    });
  }

  UI.pauseMarquee = function (sel) {
    var el = $(sel || '[data-ui-marquee]');
    if (el) el.classList.add('is-paused');
  };

  /* ---------------------------------------------------------------------------
     LAZY IMAGES —  <div class="ui-frame" data-ui-lazy><img data-src="…" alt="…">

     The download deferral itself is free: loading="lazy" is native, and this
     function sets it for you. What is NOT free, and what this adds, is the
     part around it — a reserved box, a placeholder, a fade that only plays for
     images that actually made the user wait, and an error state that stops the
     shimmer instead of animating forever.

     Two levels, and the choice matters:

       <img src="…">        already in the HTML. Native lazy applies, the image
                            still works with JS off, and search engines and
                            reader modes see it. THIS IS THE DEFAULT — use it.

       <img data-src="…">   deferred until the frame nears the viewport. Saves
                            more on a long wall, but the image does not exist
                            without JS, so it is opt-in rather than automatic.
                            If IntersectionObserver is missing we load them all
                            immediately: a slow page beats an empty one.

     rootMargin pre-loads a screen ahead, so a normal scroll never actually sees
     the placeholder — the point is to save bandwidth on what is never reached,
     not to make scrolling feel slow.
     ------------------------------------------------------------------------ */
  function markLoaded(frame, img, instant) {
    frame.classList.add(instant ? 'is-instant' : 'is-loaded');
    if (instant) frame.classList.add('is-loaded');
    img.removeAttribute('data-pending');
  }

  function loadLazy(frame) {
    var img = $('img,video', frame);
    if (!img || img.dataset.uiLazyDone) return;
    img.dataset.uiLazyDone = '1';

    var src = img.getAttribute('data-src');
    var srcset = img.getAttribute('data-srcset');
    if (srcset) img.setAttribute('srcset', srcset);
    if (src) img.setAttribute('src', src);

    /* A cached image is already complete the moment src is set. Fading that in
       makes every scroll-back flicker, so skip the transition for it. */
    if (img.complete && img.naturalWidth) { markLoaded(frame, img, true); return; }

    on(img, 'load', function () { markLoaded(frame, img, false); });
    on(img, 'error', function () {
      frame.classList.add('is-failed', 'is-loaded');
      if (!img.alt) img.alt = 'Image failed to load';
    });
  }

  var lazyObserver = null;
  function wireLazy(root) {
    var frames = $$('.ui-frame[data-ui-lazy]', root).filter(function (f) { return claim(f, 'Lazy'); });
    if (!frames.length) return;

    frames.forEach(function (f) {
      var img = $('img', f);
      if (!img) return;
      if (!img.hasAttribute('loading')) img.setAttribute('loading', 'lazy');
      /* Decoding off the main thread; without it a big image can still jank the
         scroll at the moment it appears, which reads as a slow page. */
      if (!img.hasAttribute('decoding')) img.setAttribute('decoding', 'async');
    });

    if (!('IntersectionObserver' in window)) {
      frames.forEach(loadLazy);            /* slow beats empty */
      return;
    }
    if (!lazyObserver) {
      lazyObserver = new IntersectionObserver(function (entries) {
        entries.forEach(function (e) {
          if (!e.isIntersecting) return;
          lazyObserver.unobserve(e.target); /* one shot — never re-fire */
          loadLazy(e.target);
        });
      }, { rootMargin: '100% 0px', threshold: 0 });
    }
    frames.forEach(function (f) {
      /* Nothing to defer (plain src, native lazy already handling it): just
         wire the fade so it matches the deferred ones. */
      var img = $('img', f);
      if (img && !img.getAttribute('data-src')) {
        if (img.complete && img.naturalWidth) markLoaded(f, img, true);
        else { on(img, 'load', function () { markLoaded(f, img, false); }); }
        return;
      }
      lazyObserver.observe(f);
    });
  }

  /* ---------------------------------------------------------------------------
     FORM VALIDATION —  <form data-ui-validate>

     The browser already knows whether a field is valid; what it does badly is
     say so in your design language. So: suppress the native bubble, keep the
     native rules, render into .ui-error and wire aria-invalid/aria-describedby.

     Fields are validated on blur, then live once they have been wrong — never
     while first typing, which is the behaviour that makes forms feel hostile.
     A custom rule goes in data-ui-rule as an expression over `value`.
     ------------------------------------------------------------------------ */
  function fieldError(field, msg) {
    var wrap = field.closest('.ui-field') || field.parentNode;
    var slot = $('.ui-error', wrap);
    if (msg) {
      if (!slot) {
        slot = document.createElement('div');
        slot.className = 'ui-error';
        slot.id = (field.id || 'f' + Math.random().toString(36).slice(2)) + '-err';
        wrap.appendChild(slot);
      }
      slot.textContent = msg;
      field.setAttribute('aria-invalid', 'true');
      field.setAttribute('aria-describedby', slot.id);
    } else if (slot) {
      slot.remove();
      field.removeAttribute('aria-invalid');
      field.removeAttribute('aria-describedby');
    }
  }

  /* The pattern attribute is compiled with the `v` regex flag. In v-mode a
     class like [a-z0-9-] is a syntax error (the trailing "-" must be escaped),
     and the spec says an uncompilable pattern is IGNORED — so the field goes on
     silently accepting everything, which is the worst way for validation to
     fail. Detect it at wire time, say so loudly, and keep enforcing the rule by
     recompiling under `u`, which is what the author almost certainly meant. */
  function patternFallback(field) {
    var p = field.getAttribute('pattern');
    if (!p) return;
    var src = '^(?:' + p + ')$';
    try { new RegExp(src, 'v'); return; } catch (e) {}
    try {
      field._uiPattern = new RegExp(src, 'u');
      console.warn('[ui] pattern "' + p + '" is invalid under the v flag, so the browser ' +
                   'ignores it. Escape the "-" or "[" inside your character class. ' +
                   'Enforcing it with the u flag meanwhile.', field);
    } catch (e2) {
      console.warn('[ui] pattern "' + p + '" does not compile at all; it is not enforced.', field);
    }
  }

  function checkField(field) {
    var msg = '';
    if (field._uiPattern && field.value && !field._uiPattern.test(field.value)) {
      msg = field.getAttribute('data-ui-message') || 'That value is not in the expected format.';
    } else if (field.willValidate && !field.checkValidity()) {
      msg = field.getAttribute('data-ui-message') || field.validationMessage;
    } else if (field.getAttribute('data-ui-rule') && field.value) {
      var ok = true;
      try { ok = Function('value', 'return (' + field.getAttribute('data-ui-rule') + ')')(field.value); }
      catch (e) { ok = true; }
      if (!ok) msg = field.getAttribute('data-ui-message') || 'That value is not accepted.';
    }
    fieldError(field, msg);
    return !msg;
  }

  function wireForms(root) {
    $$('form[data-ui-validate]', root).forEach(function (form) {
      if (!claim(form, 'Form')) return;
      form.noValidate = true;                     /* keep the rules, drop the bubbles */

      $$('input,select,textarea', form).forEach(function (f) {
        patternFallback(f);
        on(f, 'blur', function () { f._uiTouched = true; checkField(f); });
        on(f, 'input', function () { if (f._uiTouched) checkField(f); });
      });

      on(form, 'submit', function (e) {
        var bad = $$('input,select,textarea', form).filter(function (f) {
          f._uiTouched = true;
          return !checkField(f);
        });
        if (bad.length) {
          e.preventDefault();
          bad[0].focus();
          UI.toast(bad.length + (bad.length === 1 ? ' field needs' : ' fields need') + ' attention',
                   { tone: 'crit' });
        }
      });
    });
  }

  /* ---------------------------------------------------------------------------
     COMMAND PALETTE —  <div class="ui-scrim" id="palette" hidden> … </div>
     Items are whatever .ui-palette-item elements exist; each may carry
     data-ui-action (dispatched as a `ui:command` event) or href.
     ------------------------------------------------------------------------ */
  function wirePalette(root) {
    $$('[data-ui-palette]', root).forEach(function (scrim) {
      if (!claim(scrim, 'Pal')) return;
      var input = $('.ui-palette-input', scrim);
      var list = $('.ui-palette-list', scrim);
      var opener = null;

      function items() { return $$('.ui-palette-item', list).filter(function (i) { return !i.hidden; }); }
      function mark(el) {
        $$('.ui-palette-item', list).forEach(function (i) { i.setAttribute('aria-selected', String(i === el)); });
        if (el) el.scrollIntoView({ block: 'nearest' });
      }
      function show() {
        opener = document.activeElement;
        scrim.hidden = false;
        input.value = ''; filter();
        input.focus();
      }
      function hide() {
        scrim.hidden = true;
        if (opener && document.contains(opener)) opener.focus();
      }
      function filter() {
        var q = input.value.trim().toLowerCase();
        $$('.ui-palette-item', list).forEach(function (i) {
          i.hidden = !!q && i.textContent.toLowerCase().indexOf(q) === -1;
        });
        mark(items()[0]);
      }
      function choose(el) {
        if (!el) return;
        hide();
        if (el.getAttribute('href')) { window.location.href = el.getAttribute('href'); return; }
        var action = el.getAttribute('data-ui-action') || el.textContent.trim();
        document.dispatchEvent(new CustomEvent('ui:command', { detail: { action: action, item: el } }));
      }

      scrim.hidden = true;
      on(input, 'input', filter);
      on(scrim, 'click', function (e) { if (e.target === scrim) hide(); });
      on(list, 'click', function (e) {
        var it = e.target.closest('.ui-palette-item');
        if (it) choose(it);
      });
      on(scrim, 'keydown', function (e) {
        var all = items(), cur = all.indexOf($('.ui-palette-item[aria-selected="true"]', list));
        if (e.key === 'Escape') { e.preventDefault(); hide(); }
        else if (e.key === 'ArrowDown') { e.preventDefault(); mark(all[(cur + 1) % all.length]); }
        else if (e.key === 'ArrowUp') { e.preventDefault(); mark(all[(cur - 1 + all.length) % all.length]); }
        else if (e.key === 'Enter') { e.preventDefault(); choose(all[cur] || all[0]); }
      });

      var key = (scrim.getAttribute('data-ui-palette') || 'mod+k').toLowerCase();
      on(document, 'keydown', function (e) {
        var mod = e.metaKey || e.ctrlKey;
        if (key.indexOf('mod+') === 0 && mod && e.key.toLowerCase() === key.slice(4)) {
          e.preventDefault();
          if (scrim.hidden) show(); else hide();
        }
      });
      scrim._uiShow = show;
    });
  }

  UI.palette = function (sel) {
    var el = $(sel || '[data-ui-palette]');
    if (el && el._uiShow) el._uiShow();
  };

  /* ---------------------------------------------------------------------------
     THEME + DENSITY
     The two axes from layer 1, made switchable at runtime and remembered.
     Written to the .ui root rather than <html> so a page can host two themes
     side by side — which is exactly what the gallery does.
     ------------------------------------------------------------------------ */
  function prefs() {
    try { return JSON.parse(localStorage.getItem(STORE) || '{}'); } catch (e) { return {}; }
  }
  function save(p) {
    try { localStorage.setItem(STORE, JSON.stringify(p)); } catch (e) {}
  }
  function uiRoots() { return $$('.ui'); }

  UI.setTheme = function (name, mode) {
    uiRoots().forEach(function (el) {
      if (name) el.setAttribute('data-theme', name);
      if (mode) el.setAttribute('data-mode', mode);
    });
    var p = prefs();
    if (name) p.theme = name;
    if (mode) p.mode = mode;
    save(p);
    /* A switch that does not show the current value is a switch that lies —
       the next change then fires from a stale reading. */
    if (name) $$('select[data-ui-theme]').forEach(function (s) { s.value = name; });
    syncModeLabels();
    document.dispatchEvent(new CustomEvent('ui:theme', { detail: { theme: p.theme, mode: p.mode } }));
  };

  UI.setDensity = function (n) {
    uiRoots().forEach(function (el) { el.style.setProperty('--ui-density', n); });
    var p = prefs(); p.density = n; save(p);
    $$('[data-ui-density]').forEach(function (s) { if (s.value !== String(n)) s.value = n; });
  };

  /* The current mode is not always in data-mode: omit the attribute and the
     theme's own preferred mode applies. --ui-scheme is set by every theme in
     both cases, so ask the computed style rather than the markup. */
  function currentMode(el) {
    el = el || $('.ui');
    if (!el) return 'light';
    var s = getComputedStyle(el).getPropertyValue('--ui-scheme').trim();
    return s === 'dark' ? 'dark' : 'light';
  }
  UI.mode = currentMode;

  UI.toggleMode = function () {
    var next = currentMode() === 'dark' ? 'light' : 'dark';
    UI.setTheme(null, next);
    return next;
  };

  /* <span data-ui-mode-label> names the mode you would GET by clicking, not the
     one you are in — a toggle should say where it goes. Override the wording
     with data-ui-mode-label="Night/Day" (dark word first). */
  function syncModeLabels() {
    var dark = currentMode() === 'dark';
    $$('[data-ui-mode-label]').forEach(function (el) {
      var words = (el.getAttribute('data-ui-mode-label') || 'Night/Day').split('/');
      el.textContent = dark ? (words[1] || 'Day') : (words[0] || 'Night');
    });
  }

  /* Density by wheel and keyboard.

     OPT-IN, via data-ui-density-keys on the .ui root — and deliberately so.
     Ctrl+plus / Ctrl+minus is browser zoom, which is a real accessibility
     feature; a component library has no business taking it from every page that
     loads the file. A page that asks for it has made that trade knowingly.

     Ctrl+= is bound alongside Ctrl+plus because "+" is Shift+= on most layouts
     and nobody presses the shift deliberately. Ctrl+0 resets, matching zoom.  */
  var DENSITY_MIN = 0.75, DENSITY_MAX = 1.4, DENSITY_STEP = 0.05;

  function nudgeDensity(delta) {
    var el = $('.ui');
    if (!el) return;
    var now = parseFloat(getComputedStyle(el).getPropertyValue('--ui-density')) || 1;
    var next = Math.min(DENSITY_MAX, Math.max(DENSITY_MIN, now + delta));
    UI.setDensity(Math.round(next * 100) / 100);
  }

  function wireDensityShortcuts(root) {
    $$('[data-ui-density-keys]', root).forEach(function (host) {
      if (!claim(host, 'DKeys')) return;

      on(host, 'wheel', function (e) {
        if (!e.shiftKey) return;             /* plain wheel must still scroll */
        e.preventDefault();
        nudgeDensity(e.deltaY > 0 ? -DENSITY_STEP : DENSITY_STEP);
      }, { passive: false });                /* preventDefault needs this */

      if (claim(document, 'DKeysDoc')) {
        on(document, 'keydown', function (e) {
          if (!(e.ctrlKey || e.metaKey) || e.altKey) return;
          var k = e.key;
          if (k === '+' || k === '=') { e.preventDefault(); nudgeDensity(DENSITY_STEP); }
          else if (k === '-' || k === '_') { e.preventDefault(); nudgeDensity(-DENSITY_STEP); }
          else if (k === '0') { e.preventDefault(); UI.setDensity(1); }
        });
      }
    });
  }

  function wireThemeControls(root) {
    $$('[data-ui-theme]', root).forEach(function (el) {
      if (!claim(el, 'Th')) return;
      var ev = el.tagName === 'SELECT' ? 'change' : 'click';
      on(el, ev, function () {
        UI.setTheme(el.tagName === 'SELECT' ? el.value : el.getAttribute('data-ui-theme'));
      });
    });
    $$('[data-ui-mode]', root).forEach(function (el) {
      if (!claim(el, 'Md')) return;
      on(el, 'click', function () {
        var m = el.getAttribute('data-ui-mode');
        if (m === 'toggle') UI.toggleMode(); else UI.setTheme(null, m);
      });
    });
    $$('[data-ui-density]', root).forEach(function (el) {
      if (!claim(el, 'De')) return;
      on(el, 'input', function () { UI.setDensity(el.value); });
    });
  }

  /* Restore once, at first init. A page that hard-codes data-theme still wins
     until the user has expressed a preference. */
  var restored = false;
  function restore() {
    if (restored) return;
    restored = true;
    var p = prefs();
    if (p.theme || p.mode) UI.setTheme(p.theme, p.mode);
    if (p.density) UI.setDensity(p.density);
  }

  /* ---------------------------------------------------------------------------
     INIT
     ------------------------------------------------------------------------ */
  UI.init = function (root) {
    root = root || document;
    wireDialogs(root);
    wireMenus(root);
    wireTabs(root);
    wireAccordions(root);
    wireTips(root);
    wireSort(root);
    wireFilter(root);
    wireCopy(root);
    wireMarquee(root);      /* before wireLazy: it creates frames to wire */
    wireLazy(root);
    wireForms(root);
    wirePalette(root);
    wireThemeControls(root);
    wireDensityShortcuts(root);
    restore();
    syncModeLabels();
    return UI;
  };

  UI.version = '0.1.0';
  global.UI = UI;

  if (document.readyState === 'loading') {
    on(document, 'DOMContentLoaded', function () { UI.init(); });
  } else {
    UI.init();
  }
})(window);
