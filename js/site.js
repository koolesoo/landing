(function () {
  "use strict";

  var doc = document.documentElement;
  var themeBtn = document.querySelector("[data-theme-toggle]");

  function setTheme(dark) {
    if (dark) {
      doc.setAttribute("data-theme", "dark");
      try {
        localStorage.setItem("theme", "dark");
      } catch (e) {}
    } else {
      doc.removeAttribute("data-theme");
      try {
        localStorage.removeItem("theme");
      } catch (e) {}
    }
    if (themeBtn) {
      themeBtn.setAttribute("aria-pressed", dark ? "true" : "false");
      themeBtn.setAttribute(
        "aria-label",
        dark ? "Включить светлую тему" : "Включить тёмную тему"
      );
    }
  }

  if (themeBtn) {
    try {
      if (localStorage.getItem("theme") === "dark") {
        setTheme(true);
      }
    } catch (e) {}
    themeBtn.addEventListener("click", function () {
      setTheme(doc.getAttribute("data-theme") !== "dark");
    });
  }

  var pathSection = document.getElementById("path");
  var pathPickCards = document.querySelectorAll(".services__list .services__card--path-pick");
  var PATH_STORAGE = "pathFormat";

  var pathRailStep = document.querySelector("[data-rail-path-step]");

  function applyPathState(state, markCards) {
    if (!pathSection) return;
    if (markCards === undefined) markCards = true;
    var s = state === "coaching" || state === "interview" ? state : "idle";
    pathSection.setAttribute("data-path-state", s);
    pathSection.hidden = s === "idle";
    if (pathRailStep) pathRailStep.hidden = s === "idle";
    try {
      if (s === "idle") {
        localStorage.removeItem(PATH_STORAGE);
      } else {
        localStorage.setItem(PATH_STORAGE, s);
      }
    } catch (e) {}

    pathPickCards.forEach(function (card) {
      var v = card.getAttribute("data-path-pick") || "idle";
      if (!markCards) {
        card.classList.remove("is-path-selected");
      } else {
        card.classList.toggle("is-path-selected", v === s);
      }
    });

    pathSection.querySelectorAll("[data-path-intro]").forEach(function (p) {
      var when = p.getAttribute("data-path-intro");
      p.hidden = when !== s;
    });

    pathSection.querySelectorAll("[data-path-heading]").forEach(function (el) {
      var when = el.getAttribute("data-path-heading");
      el.hidden = when !== s;
    });

    var idleEl = pathSection.querySelector("[data-path-idle]");
    if (idleEl) idleEl.hidden = s !== "idle";

    pathSection.querySelectorAll("[data-path-panel]").forEach(function (panel) {
      panel.hidden = panel.getAttribute("data-path-panel") !== s;
    });

    window.dispatchEvent(new Event("scroll"));
    window.dispatchEvent(new Event("resize"));
  }

  if (pathSection && pathPickCards.length) {
    var initialPath = "idle";
    var storedPath = null;
    try {
      storedPath = localStorage.getItem(PATH_STORAGE);
      if (storedPath === "coaching" || storedPath === "interview") initialPath = storedPath;
    } catch (e) {}
    applyPathState(initialPath, true);

    pathPickCards.forEach(function (card) {
      card.addEventListener("click", function () {
        var st = card.getAttribute("data-path-pick") || "idle";
        applyPathState(st, true);
      });
      card.addEventListener("keydown", function (e) {
        if (e.key !== "Enter" && e.key !== " ") return;
        e.preventDefault();
        card.click();
      });
    });
  }

  var rail = document.querySelector("[data-site-rail]");
  var heroBoundary = document.querySelector(".hero");
  var railCache = null;

  function updateSiteRailReveal() {
    if (!rail) return;
    var past = true;
    if (heroBoundary) {
      past = heroBoundary.getBoundingClientRect().bottom < 1;
    }
    var next = past ? "true" : "false";
    document.body.setAttribute("data-site-rail-revealed", next);
    rail.setAttribute("aria-hidden", past ? "false" : "true");
  }

  if (rail) {
    function getVisibleRailLinks() {
      return [].slice.call(rail.querySelectorAll("[data-rail-link]")).filter(function (a) {
        var step = a.closest("[data-rail-step]");
        return step && !step.hidden;
      });
    }

    function buildRailTargets(visibleLinks) {
      return visibleLinks.map(function (a) {
        var href = a.getAttribute("href") || "";
        if (!href || href === "#" || href === "#top") {
          return { link: a, el: null, top: 0 };
        }
        var id = href.replace(/^#/, "");
        return { link: a, el: document.getElementById(id), top: 0 };
      });
    }

    function connectorsForLinks(visibleLinks) {
      var out = [];
      for (var i = 0; i < visibleLinks.length - 1; i++) {
        var step = visibleLinks[i].closest("[data-rail-step]");
        var conn = step ? step.querySelector("[data-rail-connector]") : null;
        if (conn) out.push(conn);
      }
      return out;
    }

    function measureTops(targets) {
      targets.forEach(function (t) {
        t.top = t.el ? t.el.getBoundingClientRect().top + window.scrollY : 0;
      });
    }

    function updateRail(railTargets, visibleLinks, steps, connectors) {
      var vh = window.innerHeight || 1;
      var probe = window.scrollY + vh * 0.35;
      var n = railTargets.length;
      var active = 0;
      for (var i = 0; i < n; i++) {
        var nextTop = i + 1 < n ? railTargets[i + 1].top : Infinity;
        if (probe >= railTargets[i].top - 4 && probe < nextTop - 4) {
          active = i;
          break;
        }
        if (i === n - 1 && probe >= railTargets[i].top) active = i;
      }

      if (window.scrollY + vh >= document.documentElement.scrollHeight - 4) {
        active = n - 1;
      }

      steps.forEach(function (step, idx) {
        step.classList.toggle("is-active", idx === active);
        step.classList.toggle("is-passed", idx < active);
      });

      visibleLinks.forEach(function (link, idx) {
        if (idx === active) link.setAttribute("aria-current", "location");
        else link.removeAttribute("aria-current");
      });

      connectors.forEach(function (conn, idx) {
        var a = railTargets[idx].top;
        var b = idx + 1 < n ? railTargets[idx + 1].top : a;
        var span = b - a;
        var fill = 0;
        if (span > 0) {
          if (probe <= a) fill = 0;
          else if (probe >= b) fill = 1;
          else fill = (probe - a) / span;
        }
        conn.style.setProperty("--fill", String(fill));
      });
    }

    var railRaf = false;
    function scheduleRail() {
      if (railRaf) return;
      railRaf = true;
      window.requestAnimationFrame(function () {
        railRaf = false;
        updateSiteRailReveal();
        if (!railCache) {
          remeasureAndUpdate();
          return;
        }
        updateRail(
          railCache.targets,
          railCache.links,
          railCache.steps,
          railCache.connectors
        );
      });
    }

    function remeasureAndUpdate() {
      updateSiteRailReveal();
      var visibleLinks = getVisibleRailLinks();
      var railTargets = buildRailTargets(visibleLinks);
      var steps = visibleLinks.map(function (a) {
        return a.closest("[data-rail-step]");
      });
      var connectors = connectorsForLinks(visibleLinks);
      measureTops(railTargets);
      railCache = {
        targets: railTargets,
        links: visibleLinks,
        steps: steps,
        connectors: connectors
      };
      updateRail(railTargets, visibleLinks, steps, connectors);
    }

    window.addEventListener("scroll", scheduleRail, { passive: true });
    window.addEventListener("resize", remeasureAndUpdate);
    window.addEventListener("load", remeasureAndUpdate);
    if ("ResizeObserver" in window) {
      var ro = new ResizeObserver(remeasureAndUpdate);
      document.querySelectorAll("main section[id]").forEach(function (sec) {
        ro.observe(sec);
      });
    }
    remeasureAndUpdate();
  }

  var guideForm = document.getElementById("guide-form");
  if (guideForm) {
    var nameInput = document.getElementById("guide-name");
    var tgInput = document.getElementById("guide-telegram");
    var statusEl = document.getElementById("guide-status");
    var tgRe = /^[a-zA-Z][a-zA-Z0-9_]{3,31}$/;

    guideForm.addEventListener("submit", function (e) {
      e.preventDefault();
      if (nameInput) {
        var nm = (nameInput.value || "").trim();
        nameInput.value = nm;
        if (nm.length < 2) {
          nameInput.focus();
          nameInput.setCustomValidity("Укажите, как к вам обращаться.");
          guideForm.reportValidity();
          nameInput.setCustomValidity("");
          return;
        }
      }
      if (!tgInput) return;
      var raw = (tgInput.value || "").trim();
      if (raw.charAt(0) === "@") raw = raw.slice(1);
      tgInput.value = raw;
      if (!tgRe.test(raw)) {
        tgInput.focus();
        tgInput.setCustomValidity(
          "Ник в Telegram: латиница, цифры и _, от 4 до 32 символов, без @."
        );
        guideForm.reportValidity();
        tgInput.setCustomValidity("");
        return;
      }
      if (statusEl) {
        statusEl.textContent =
          "Спасибо! Напишу вам в Telegram в ближайшее время с материалом.";
        statusEl.hidden = false;
      }
      guideForm.reset();
    });
  }

  var hero = document.querySelector(".hero[data-hero-persona]");
  var personaTabs = hero ? hero.querySelectorAll("[data-hero-persona-set]") : null;
  var personaPanel = document.getElementById("hero-persona-panel");
  /* Включая панели спикера в #about (единая шторка «Об эксперте»), не только .hero */
  var personaCopyEls = document.querySelectorAll("[data-persona-copy]");
  var proSharp = hero ? hero.querySelector(".hero__media-img--pro") : null;
  var internSharp = hero ? hero.querySelector(".hero__media-img--intern") : null;
  var proPortraitActiveSrc = "assets/hero-portrait-active.png";
  var proPortraitInactiveSrc = "assets/hero-portrait.png";
  var internPortraitActiveSrc = "assets/hero-portrait-intern-active.png";
  var internPortraitInactiveSrc = "assets/hero-portrait-intern.png";
  var speakerPro = hero ? hero.querySelector('[data-hero-speaker="pro"]') : null;
  var speakerIntern = hero ? hero.querySelector('[data-hero-speaker="intern"]') : null;
  var heroMediaDual = hero ? hero.querySelector(".hero__media-dual") : null;
  var heroSwapVideo = document.getElementById("hero-persona-swap-video");
  /** 1× вперёд/назад — ускорение снимаем, чтобы не грузить систему. */
  var HERO_SWAP_PLAYBACK_RATE = 1;
  /** Увеличивается при каждом старте смены; устаревшие ended/timeupdate не трогают DOM. */
  var heroSwapEpoch = 0;

  function detachHeroSwapMediaListeners() {
    if (!heroSwapVideo) return;
    if (heroSwapVideo._swapEnded) {
      heroSwapVideo.removeEventListener("ended", heroSwapVideo._swapEnded);
      heroSwapVideo._swapEnded = null;
    }
    if (heroSwapVideo._swapRevTick) {
      heroSwapVideo.removeEventListener("timeupdate", heroSwapVideo._swapRevTick);
      heroSwapVideo._swapRevTick = null;
    }
    heroSwapVideo.removeEventListener("ended", endHeroPersonaSwapVideo);
  }

  /**
   * @param {number} [fromEpoch] — если передан и не совпадает с heroSwapEpoch, вызов от старого ролика (игнор).
   * Без аргументов — принудительное завершение (например, не используется).
   */
  function endHeroPersonaSwapVideo(fromEpoch) {
    if (arguments.length > 0 && fromEpoch !== heroSwapEpoch) return;
    if (heroSwapVideo) {
      detachHeroSwapMediaListeners();
      heroSwapVideo.playbackRate = 1;
      heroSwapVideo.pause();
    }
    if (heroMediaDual) {
      heroMediaDual.classList.remove("hero__media-dual--swap-playing");
      var personaNow = hero ? hero.getAttribute("data-hero-persona") : null;
      if (personaNow === "intern") {
        /* Только стоп-кадр конца ролика (PNG в разметке скрыты в CSS). */
        heroMediaDual.classList.add("hero__media-dual--video-poster");
        if (heroSwapVideo) {
          try {
            var dEnd = heroSwapVideo.duration;
            if (isFinite(dEnd) && dEnd > 0) {
              heroSwapVideo.currentTime = Math.min(dEnd, Math.max(dEnd - 0.08, 0));
            }
          } catch (e) {}
        }
      } else if (personaNow === "pro") {
        /* Последний кадр ролика (конец анимации), без initHeroVideoPosterFrame — иначе load() и сброс на первый кадр */
        heroMediaDual.classList.add("hero__media-dual--video-poster");
        if (heroSwapVideo) {
          try {
            if (heroSwapVideo.currentTime < 0.06) {
              heroSwapVideo.currentTime = 0;
            }
          } catch (e) {}
        }
      }
    }
  }

  /**
   * @param {string} targetPersona — «pro» = реверс к «Для всех», «intern» = вперёд к «Для студентов».
   * @param {{ fromCurrent?: boolean }} [opts] — если true: не сбрасывать currentTime (прерывание анимации кликом — разворот от текущего кадра).
   */
  function playHeroPersonaSwapVideo(targetPersona, opts) {
    opts = opts || {};
    if (!heroSwapVideo || !heroMediaDual) return;
    if (!heroSwapVideo.getAttribute("src") && !heroSwapVideo.querySelector("source")) return;

    heroSwapEpoch++;
    var epoch = heroSwapEpoch;

    detachHeroSwapMediaListeners();
    try {
      heroSwapVideo.pause();
    } catch (e) {}

    var reverse = targetPersona === "pro";
    var fromCurrent = !!opts.fromCurrent;
    heroMediaDual.classList.add("hero__media-dual--video-poster");
    heroMediaDual.classList.add("hero__media-dual--swap-playing");

    /* После ended повторный play() часто «молчит», пока не сбросить currentTime (особенно Safari). */
    if (!fromCurrent) {
      try {
        if (heroSwapVideo.ended) {
          var dFix = heroSwapVideo.duration;
          if (reverse && isFinite(dFix) && dFix > 0) {
            heroSwapVideo.currentTime = Math.min(dFix, Math.max(dFix - 0.06, 0));
          } else {
            heroSwapVideo.currentTime = 0;
          }
        }
      } catch (eFix) {}
    }

    function playForward() {
      heroSwapVideo.playbackRate = HERO_SWAP_PLAYBACK_RATE;
      if (!fromCurrent) {
        try {
          heroSwapVideo.currentTime = 0;
        } catch (e) {}
      }
      var d = heroSwapVideo.duration;
      if (fromCurrent && isFinite(d) && d > 0 && heroSwapVideo.currentTime >= d - 0.12) {
        endHeroPersonaSwapVideo(epoch);
        return;
      }
      function onSwapEnded() {
        heroSwapVideo.removeEventListener("ended", onSwapEnded);
        heroSwapVideo._swapEnded = null;
        endHeroPersonaSwapVideo(epoch);
      }
      heroSwapVideo._swapEnded = onSwapEnded;
      heroSwapVideo.addEventListener("ended", onSwapEnded);
      var p = heroSwapVideo.play();
      if (p && typeof p.catch === "function") {
        p.catch(function () {
          endHeroPersonaSwapVideo(epoch);
        });
      }
    }

    function playReverse() {
      heroSwapVideo.playbackRate = -HERO_SWAP_PLAYBACK_RATE;
      if (heroSwapVideo.playbackRate >= 0) {
        playForward();
        return;
      }
      function seekEndAndPlay() {
        if (epoch !== heroSwapEpoch) return;
        var d = heroSwapVideo.duration;
        if (!isFinite(d) || d <= 0) {
          endHeroPersonaSwapVideo(epoch);
          return;
        }
        if (!fromCurrent) {
          try {
            heroSwapVideo.currentTime = Math.min(d, Math.max(d - 0.04, 0));
          } catch (err) {
            playForward();
            return;
          }
        } else if (heroSwapVideo.currentTime <= 0.1) {
          endHeroPersonaSwapVideo(epoch);
          return;
        }
        function onRevTick() {
          if (epoch !== heroSwapEpoch) {
            heroSwapVideo.removeEventListener("timeupdate", onRevTick);
            heroSwapVideo._swapRevTick = null;
            return;
          }
          if (!heroSwapVideo || heroSwapVideo.playbackRate >= 0) return;
          if (heroSwapVideo.currentTime <= 0.08) {
            heroSwapVideo.removeEventListener("timeupdate", onRevTick);
            heroSwapVideo._swapRevTick = null;
            endHeroPersonaSwapVideo(epoch);
          }
        }
        heroSwapVideo._swapRevTick = onRevTick;
        heroSwapVideo.addEventListener("timeupdate", onRevTick);
        var p = heroSwapVideo.play();
        if (p && typeof p.catch === "function") {
          p.catch(function () {
            endHeroPersonaSwapVideo(epoch);
          });
        }
      }
      if (heroSwapVideo.readyState >= 1 && isFinite(heroSwapVideo.duration) && heroSwapVideo.duration > 0) {
        seekEndAndPlay();
      } else {
        heroSwapVideo.addEventListener(
          "loadedmetadata",
          function onMeta() {
            heroSwapVideo.removeEventListener("loadedmetadata", onMeta);
            if (epoch !== heroSwapEpoch) return;
            seekEndAndPlay();
          },
          { once: true }
        );
      }
    }

    if (reverse) {
      playReverse();
    } else {
      playForward();
    }
  }

  /**
   * По умолчанию для сценария «Для всех» (pro): стоп-кадр = первый кадр MP4, PNG скрыты.
   * Класс video-poster вешается сразу, чтобы не мелькали PNG до декодирования кадра.
   */
  function initHeroVideoPosterFrame() {
    if (!heroSwapVideo || !heroMediaDual || !hero) return;
    if (!heroSwapVideo.getAttribute("src") && !heroSwapVideo.querySelector("source")) return;
    if (hero.getAttribute("data-hero-persona") !== "pro") return;
    if (heroMediaDual.classList.contains("hero__media-dual--swap-playing")) return;

    heroMediaDual.classList.add("hero__media-dual--video-poster");

    function applyStopFrame() {
      if (heroMediaDual.classList.contains("hero__media-dual--swap-playing")) return;
      heroSwapVideo.muted = true;
      heroSwapVideo.playbackRate = 1;
      try {
        heroSwapVideo.currentTime = 0;
      } catch (e) {}
      var p = heroSwapVideo.play();
      function freezeFirstFrame() {
        if (heroMediaDual.classList.contains("hero__media-dual--swap-playing")) return;
        try {
          heroSwapVideo.pause();
          heroSwapVideo.currentTime = 0;
        } catch (err) {}
      }
      if (p !== undefined && p !== null && typeof p.then === "function") {
        p.then(function () {
          window.requestAnimationFrame(function () {
            window.requestAnimationFrame(freezeFirstFrame);
          });
        }).catch(function () {
          freezeFirstFrame();
        });
      } else {
        freezeFirstFrame();
      }
    }

    try {
      heroSwapVideo.load();
    } catch (e) {}

    var applyScheduled = false;
    function scheduleApplyStopFrame() {
      if (applyScheduled) return;
      if (heroMediaDual.classList.contains("hero__media-dual--swap-playing")) {
        applyScheduled = true;
        return;
      }
      if (heroSwapVideo.readyState >= 2) {
        applyScheduled = true;
        applyStopFrame();
        return;
      }
      function onLoaded() {
        if (applyScheduled) return;
        if (heroMediaDual.classList.contains("hero__media-dual--swap-playing")) {
          applyScheduled = true;
          return;
        }
        applyScheduled = true;
        heroSwapVideo.removeEventListener("loadeddata", onLoaded);
        heroSwapVideo.removeEventListener("canplay", onLoaded);
        applyStopFrame();
      }
      heroSwapVideo.addEventListener("loadeddata", onLoaded, { once: true });
      heroSwapVideo.addEventListener("canplay", onLoaded, { once: true });
      window.requestAnimationFrame(function () {
        if (heroSwapVideo.readyState >= 2) onLoaded();
      });
    }
    scheduleApplyStopFrame();
  }

  /** Сценарий «студенты»: стоп-кадр = конец ролика (PNG скрыты в CSS). */
  function initHeroVideoEndFrame() {
    if (!heroSwapVideo || !heroMediaDual || !hero) return;
    if (!heroSwapVideo.getAttribute("src") && !heroSwapVideo.querySelector("source")) return;
    if (hero.getAttribute("data-hero-persona") !== "intern") return;
    if (heroMediaDual.classList.contains("hero__media-dual--swap-playing")) return;

    heroMediaDual.classList.add("hero__media-dual--video-poster");

    function applyEndFrame() {
      if (heroMediaDual.classList.contains("hero__media-dual--swap-playing")) return;
      heroSwapVideo.muted = true;
      heroSwapVideo.playbackRate = 1;
      var d = heroSwapVideo.duration;
      if (!isFinite(d) || d <= 0) return;
      var tEnd = Math.min(d, Math.max(d - 0.1, 0));
      try {
        heroSwapVideo.currentTime = tEnd;
      } catch (e) {}
      var p = heroSwapVideo.play();
      function freezeEndFrame() {
        if (heroMediaDual.classList.contains("hero__media-dual--swap-playing")) return;
        try {
          heroSwapVideo.pause();
          heroSwapVideo.currentTime = tEnd;
        } catch (err) {}
      }
      if (p !== undefined && p !== null && typeof p.then === "function") {
        p.then(function () {
          window.requestAnimationFrame(function () {
            window.requestAnimationFrame(freezeEndFrame);
          });
        }).catch(function () {
          freezeEndFrame();
        });
      } else {
        freezeEndFrame();
      }
    }

    try {
      heroSwapVideo.load();
    } catch (e) {}

    var applyScheduled = false;
    function scheduleApplyEndFrame() {
      if (applyScheduled) return;
      if (heroMediaDual.classList.contains("hero__media-dual--swap-playing")) {
        applyScheduled = true;
        return;
      }
      if (
        heroSwapVideo.readyState >= 2 &&
        isFinite(heroSwapVideo.duration) &&
        heroSwapVideo.duration > 0
      ) {
        applyScheduled = true;
        applyEndFrame();
        return;
      }
      function onLoaded() {
        if (applyScheduled) return;
        if (heroMediaDual.classList.contains("hero__media-dual--swap-playing")) {
          applyScheduled = true;
          return;
        }
        applyScheduled = true;
        heroSwapVideo.removeEventListener("loadeddata", onLoaded);
        heroSwapVideo.removeEventListener("canplay", onLoaded);
        applyEndFrame();
      }
      heroSwapVideo.addEventListener("loadeddata", onLoaded, { once: true });
      heroSwapVideo.addEventListener("canplay", onLoaded, { once: true });
      window.requestAnimationFrame(function () {
        if (
          heroSwapVideo.readyState >= 2 &&
          isFinite(heroSwapVideo.duration) &&
          heroSwapVideo.duration > 0
        ) {
          onLoaded();
        }
      });
    }
    scheduleApplyEndFrame();
  }

  function setHeroPersona(persona, options) {
    options = options || {};
    if (!hero || (persona !== "pro" && persona !== "intern")) return;
    var previous = hero.getAttribute("data-hero-persona");
    hero.setAttribute("data-hero-persona", persona);
    if (speakerPro && speakerIntern) {
      var proActive = persona === "pro";
      speakerPro.classList.toggle("hero__speaker--active", proActive);
      speakerPro.classList.toggle("hero__speaker--inactive", !proActive);
      speakerIntern.classList.toggle("hero__speaker--active", !proActive);
      speakerIntern.classList.toggle("hero__speaker--inactive", proActive);
    }
    if (personaTabs) {
      personaTabs.forEach(function (tab) {
        var active = tab.getAttribute("data-hero-persona-set") === persona;
        tab.setAttribute("aria-selected", active ? "true" : "false");
        tab.tabIndex = active ? 0 : -1;
      });
    }
    if (personaPanel) {
      personaPanel.setAttribute(
        "aria-labelledby",
        persona === "intern" ? "hero-persona-tab-intern" : "hero-persona-tab-pro"
      );
    }
    if (personaCopyEls) {
      personaCopyEls.forEach(function (el) {
        if (el.getAttribute("data-persona-copy") === persona) {
          el.removeAttribute("hidden");
        } else {
          el.setAttribute("hidden", "");
        }
      });
    }
    if (proSharp && internSharp) {
      if (persona === "intern") {
        proSharp.src = proPortraitInactiveSrc;
        proSharp.setAttribute("aria-hidden", "true");
        proSharp.setAttribute("alt", "");
        internSharp.src = internPortraitActiveSrc;
        internSharp.removeAttribute("aria-hidden");
        internSharp.setAttribute("alt", "Фото для сценария стажировки");
      } else {
        proSharp.src = proPortraitActiveSrc;
        internSharp.src = internPortraitInactiveSrc;
        internSharp.setAttribute("aria-hidden", "true");
        internSharp.setAttribute("alt", "");
        proSharp.removeAttribute("aria-hidden");
        proSharp.setAttribute("alt", "Фото для первого экрана");
      }
    }
    try {
      localStorage.setItem("heroPersona", persona);
    } catch (e) {}

    if (
      !options.skipVideo &&
      heroSwapVideo &&
      heroMediaDual &&
      previous &&
      previous !== persona &&
      (persona === "pro" || persona === "intern")
    ) {
      /* Сразу скрыть PNG под видео до старта ролика — меньше мигания при быстрых кликах */
      heroMediaDual.classList.add("hero__media-dual--video-poster");
      var midSwap = heroMediaDual.classList.contains("hero__media-dual--swap-playing");
      playHeroPersonaSwapVideo(persona, midSwap ? { fromCurrent: true } : null);
    }
  }

  if (hero && personaTabs && personaTabs.length) {
    var initial = "pro";
    try {
      var params = new URLSearchParams(window.location.search);
      if (params.get("persona") === "intern" || params.get("hero") === "intern") {
        initial = "intern";
      } else if (localStorage.getItem("heroPersona") === "intern") {
        initial = "intern";
      }
    } catch (e) {}
    setHeroPersona(initial, { skipVideo: true });

    if (initial === "intern") {
      initHeroVideoEndFrame();
    } else {
      initHeroVideoPosterFrame();
    }

    if (heroSwapVideo) {
      heroSwapVideo.addEventListener("error", function () {
        heroSwapEpoch++;
        detachHeroSwapMediaListeners();
        if (heroMediaDual) {
          heroMediaDual.classList.remove("hero__media-dual--video-poster");
          heroMediaDual.classList.remove("hero__media-dual--swap-playing");
        }
      });
    }

    personaTabs.forEach(function (tab) {
      tab.addEventListener("click", function () {
        setHeroPersona(tab.getAttribute("data-hero-persona-set") || "pro");
      });
    });

    var tablist = hero.querySelector(".hero__persona");
    if (tablist) {
      tablist.addEventListener("keydown", function (e) {
        if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
        e.preventDefault();
        var next = e.key === "ArrowRight" ? "intern" : "pro";
        setHeroPersona(next);
        var t = hero.querySelector('[data-hero-persona-set="' + next + '"]');
        if (t) t.focus();
      });
    }

    // Клик / Enter / Space по спикеру (в т.ч. неактивному) → переключение персоны
    var heroSpeakers = hero.querySelectorAll("[data-hero-speaker]");
    function syncInactiveSpeakerPortraitFile(sp) {
      if (!sp.classList.contains("hero__speaker--inactive")) return;
      var id = sp.getAttribute("data-hero-speaker");
      if (!id || (id !== "pro" && id !== "intern") || !proSharp || !internSharp) return;
      var img = id === "pro" ? proSharp : internSharp;
      var useActive = sp.matches(":hover") || document.activeElement === sp;
      img.src =
        id === "pro"
          ? useActive
            ? proPortraitActiveSrc
            : proPortraitInactiveSrc
          : useActive
            ? internPortraitActiveSrc
            : internPortraitInactiveSrc;
    }
    heroSpeakers.forEach(function (sp) {
      sp.addEventListener("click", function () {
        var target = sp.getAttribute("data-hero-speaker");
        if (target) setHeroPersona(target);
      });
      sp.addEventListener("keydown", function (e) {
        if (e.key !== "Enter" && e.key !== " ") return;
        e.preventDefault();
        var target = sp.getAttribute("data-hero-speaker");
        if (target) setHeroPersona(target);
      });
      sp.addEventListener("pointerenter", function () {
        syncInactiveSpeakerPortraitFile(sp);
      });
      sp.addEventListener("pointerleave", function () {
        syncInactiveSpeakerPortraitFile(sp);
      });
      sp.addEventListener("focusin", function () {
        syncInactiveSpeakerPortraitFile(sp);
      });
      sp.addEventListener("focusout", function () {
        syncInactiveSpeakerPortraitFile(sp);
      });
    });

  }

  // -----------------------------------------------------------
  // Reveal-on-scroll микроанимации (IntersectionObserver)
  // -----------------------------------------------------------
  var revealEls = document.querySelectorAll("[data-reveal]");
  if (revealEls.length && "IntersectionObserver" in window) {
    var reveal = function (el) {
      el.classList.add("is-revealed");
    };
    var io = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            var delay = entry.target.getAttribute("data-reveal-delay") || "0";
            entry.target.style.setProperty("--reveal-delay", delay + "ms");
            reveal(entry.target);
            io.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -8% 0px" }
    );
    revealEls.forEach(function (el) {
      io.observe(el);
    });
  } else if (revealEls.length) {
    revealEls.forEach(function (el) {
      el.classList.add("is-revealed");
    });
  }
})();
