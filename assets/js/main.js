/* =========================================================================
   КетлерСпорт — клиентская логика
   Без зависимостей. Работает при отключённом JS: формы деградируют
   в обычный POST/mailto, навигация остаётся доступной.
   ========================================================================= */

(function () {
  'use strict';

  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---- 1. Мобильное меню ------------------------------------------------ */

  var burger = document.querySelector('[data-burger]');
  var nav = document.querySelector('[data-nav]');

  if (burger && nav) {
    var closeNav = function () {
      nav.classList.remove('is-open');
      burger.setAttribute('aria-expanded', 'false');
      document.body.style.overflow = '';
    };

    burger.addEventListener('click', function () {
      var open = nav.classList.toggle('is-open');
      burger.setAttribute('aria-expanded', String(open));
      document.body.style.overflow = open ? 'hidden' : '';
    });

    nav.addEventListener('click', function (e) {
      if (e.target.closest('a')) closeNav();
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && nav.classList.contains('is-open')) {
        closeNav();
        burger.focus();
      }
    });

    window.addEventListener('resize', function () {
      if (window.innerWidth >= 1024) closeNav();
    });
  }

  /* ---- 2. Плавающие элементы: панель звонка и «наверх» ------------------ */

  var callbar = document.querySelector('[data-callbar]');
  var toTop = document.querySelector('[data-to-top]');

  var onScroll = function () {
    var shown = window.scrollY > 500;
    if (callbar) callbar.classList.toggle('is-visible', shown);
    if (toTop) toTop.classList.toggle('is-visible', shown);
  };

  var ticking = false;
  window.addEventListener('scroll', function () {
    if (ticking) return;
    ticking = true;
    window.requestAnimationFrame(function () {
      onScroll();
      ticking = false;
    });
  }, { passive: true });
  onScroll();

  if (toTop) {
    toTop.addEventListener('click', function () {
      window.scrollTo({ top: 0, behavior: reduceMotion ? 'auto' : 'smooth' });
    });
  }

  /* ---- 3. Появление блоков при прокрутке -------------------------------- */

  var revealables = document.querySelectorAll('.reveal');

  if (reduceMotion || !('IntersectionObserver' in window)) {
    revealables.forEach(function (el) { el.classList.add('is-in'); });
  } else {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry, i) {
        if (!entry.isIntersecting) return;
        var delay = Math.min(i * 40, 200);
        setTimeout(function () { entry.target.classList.add('is-in'); }, delay);
        io.unobserve(entry.target);
      });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });

    revealables.forEach(function (el) { io.observe(el); });
  }

  /* ---- 4. Счётчики в блоке статистики ----------------------------------- */

  var counters = document.querySelectorAll('[data-count]');

  if (counters.length) {
    var animate = function (el) {
      var target = parseInt(el.getAttribute('data-count'), 10);
      if (isNaN(target) || reduceMotion) { el.textContent = el.getAttribute('data-count'); return; }
      var start = performance.now();
      var dur = 1200;
      var tick = function (now) {
        var p = Math.min((now - start) / dur, 1);
        var eased = 1 - Math.pow(1 - p, 3);
        el.textContent = Math.round(target * eased).toLocaleString('ru-RU');
        if (p < 1) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    };

    if ('IntersectionObserver' in window) {
      var cio = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          animate(entry.target);
          cio.unobserve(entry.target);
        });
      }, { threshold: 0.5 });
      counters.forEach(function (el) { cio.observe(el); });
    } else {
      counters.forEach(animate);
    }
  }

  /* ---- 5. Маска телефона ------------------------------------------------ */

  var formatPhone = function (value) {
    var digits = value.replace(/\D/g, '');
    if (!digits) return '';
    if (digits[0] === '8') digits = '7' + digits.slice(1);
    if (digits[0] !== '7') digits = '7' + digits;
    digits = digits.slice(0, 11);

    var out = '+7';
    if (digits.length > 1) out += ' (' + digits.slice(1, 4);
    if (digits.length >= 5) out += ') ' + digits.slice(4, 7);
    if (digits.length >= 8) out += '-' + digits.slice(7, 9);
    if (digits.length >= 10) out += '-' + digits.slice(9, 11);
    return out;
  };

  document.querySelectorAll('input[type="tel"]').forEach(function (input) {
    input.addEventListener('input', function () {
      var pos = input.selectionStart === input.value.length;
      input.value = formatPhone(input.value);
      if (pos) input.setSelectionRange(input.value.length, input.value.length);
    });
    input.addEventListener('focus', function () {
      if (!input.value) input.value = '+7 (';
    });
    input.addEventListener('blur', function () {
      if (input.value.replace(/\D/g, '').length < 2) input.value = '';
    });
  });

  /* ---- 6. Валидация и отправка форм ------------------------------------- */

  var setError = function (input, message) {
    var field = input.closest('.field');
    if (!field) return;
    var box = field.querySelector('.field__error');
    field.classList.toggle('has-error', Boolean(message));
    input.setAttribute('aria-invalid', message ? 'true' : 'false');
    if (box) box.textContent = message || '';
  };

  var validate = function (input) {
    var value = input.value.trim();

    if (input.type === 'checkbox') {
      if (input.required && !input.checked) { setError(input, 'Требуется согласие'); return false; }
      setError(input, ''); return true;
    }
    if (input.required && !value) {
      setError(input, 'Заполните это поле'); return false;
    }
    if (input.type === 'tel' && value) {
      if (value.replace(/\D/g, '').length !== 11) {
        setError(input, 'Введите номер полностью: +7 (999) 123-45-67'); return false;
      }
    }
    if (input.type === 'email' && value && !/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(value)) {
      setError(input, 'Проверьте адрес электронной почты'); return false;
    }
    setError(input, '');
    return true;
  };

  document.querySelectorAll('form[data-form]').forEach(function (form) {
    var fields = form.querySelectorAll('input, select, textarea');
    var status = form.querySelector('.form__status');
    var submit = form.querySelector('[type="submit"]');

    fields.forEach(function (input) {
      input.addEventListener('blur', function () { validate(input); });
      input.addEventListener('input', function () {
        if (input.closest('.field') && input.closest('.field').classList.contains('has-error')) validate(input);
      });
    });

    form.addEventListener('submit', function (e) {
      e.preventDefault();

      var firstInvalid = null;
      fields.forEach(function (input) {
        if (!validate(input) && !firstInvalid) firstInvalid = input;
      });

      if (firstInvalid) {
        firstInvalid.focus();
        if (status) {
          status.className = 'form__status is-error';
          status.textContent = 'Проверьте отмеченные поля — что-то заполнено не полностью.';
        }
        return;
      }

      // Ловушка для ботов: поле скрыто от людей, заполнено — значит это робот.
      var honeypot = form.querySelector('input[name="company"]');
      if (honeypot && honeypot.value) {
        if (status) {
          status.className = 'form__status is-ok';
          status.textContent = 'Заявка принята.';
        }
        form.reset();
        return;
      }

      var endpoint = form.getAttribute('data-endpoint');
      var done = function (ok) {
        if (submit) { submit.removeAttribute('aria-busy'); submit.textContent = submit.dataset.label; }
        if (!status) return;
        if (ok) {
          status.className = 'form__status is-ok';
          status.textContent = 'Заявка принята. Перезвоним в течение 15 минут в рабочее время.';
          form.reset();
        } else {
          status.className = 'form__status is-error';
          status.textContent = 'Не удалось отправить заявку. Позвоните нам или напишите в WhatsApp — ответим сразу.';
        }
      };

      if (submit) {
        submit.dataset.label = submit.textContent;
        submit.setAttribute('aria-busy', 'true');
        submit.textContent = 'Отправляем…';
      }

      if (!endpoint) {
        // Приёмник заявок не настроен: честно сообщаем и уводим на телефон,
        // вместо того чтобы молча потерять заявку.
        console.warn('[форма] Не задан brand.form_endpoint в config.json — заявки никуда не отправляются.');
        setTimeout(function () {
          if (submit) { submit.removeAttribute('aria-busy'); submit.textContent = submit.dataset.label; }
          if (status) {
            status.className = 'form__status is-error';
            status.textContent = 'Отправка заявок с сайта временно недоступна. ' +
              'Позвоните нам или напишите в WhatsApp — ответим сразу.';
          }
        }, 300);
        return;
      }

      fetch(endpoint, {
        method: 'POST',
        body: new FormData(form),
        headers: { 'Accept': 'application/json' }
      })
        .then(function (r) { done(r.ok); })
        .catch(function () { done(false); });
    });
  });

  /* ---- 6б. Всплывающее окно с формой ------------------------------------ */

  var modal = document.getElementById('lead-modal');

  if (modal && typeof modal.showModal === 'function') {
    var narrow = window.matchMedia('(max-width: 1023px)');

    document.querySelectorAll('[data-lead-cta]').forEach(function (trigger) {
      trigger.addEventListener('click', function (e) {
        // На широких экранах форма и так видна в первом экране — не мешаем
        // штатному переходу по якорю на блок «Заявка».
        if (!narrow.matches) return;
        e.preventDefault();
        modal.showModal();
        var first = modal.querySelector('input[name="name"]');
        if (first) setTimeout(function () { first.focus(); }, 60);
      });
    });

    modal.querySelectorAll('[data-modal-close]').forEach(function (btn) {
      btn.addEventListener('click', function () { modal.close(); });
    });

    // Клик по затемнённому фону закрывает окно.
    modal.addEventListener('click', function (e) {
      if (e.target === modal) modal.close();
    });

    // После успешной отправки окно можно закрыть — но не сразу,
    // чтобы человек успел прочитать подтверждение.
    var modalForm = modal.querySelector('form[data-form]');
    if (modalForm) {
      modalForm.addEventListener('submit', function () {
        var status = modalForm.querySelector('.form__status');
        if (!status) return;
        setTimeout(function () {
          if (status.classList.contains('is-ok') && modal.open) modal.close();
        }, 4000);
      });
    }
  }

  /* ---- 7. Аккордеоны: закрываем соседей в одной группе ------------------ */

  document.querySelectorAll('[data-accordion]').forEach(function (group) {
    var items = group.querySelectorAll('details');
    items.forEach(function (item) {
      item.addEventListener('toggle', function () {
        if (!item.open) return;
        items.forEach(function (other) { if (other !== item) other.open = false; });
      });
    });
  });

  /* ---- 8. Подсветка активного раздела в навигации ----------------------- */

  var sections = document.querySelectorAll('main section[id]');
  var navLinks = document.querySelectorAll('.nav__link[href^="#"]');

  if (sections.length && navLinks.length && 'IntersectionObserver' in window) {
    var sio = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        navLinks.forEach(function (link) {
          var match = link.getAttribute('href') === '#' + entry.target.id;
          if (match) link.setAttribute('aria-current', 'page');
          else if (link.getAttribute('aria-current') === 'page') link.removeAttribute('aria-current');
        });
      });
    }, { rootMargin: '-40% 0px -55% 0px' });

    sections.forEach(function (s) { sio.observe(s); });
  }

})();
