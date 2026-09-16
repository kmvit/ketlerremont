#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сборщик статического сайта «Ремонт спортивного оборудования на КМВ».

Запуск:      python3 build.py
Результат:   index.html, страницы городов, privacy.html, sitemap.xml, robots.txt

Правки контента — в config.json (контакты, цены, услуги, города, FAQ).
Правки вёрстки — в templates/*.html. Стили — assets/css/style.css.
Зависимостей нет, нужен только Python 3.8+.
"""

from __future__ import annotations

import html
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TEMPLATES = ROOT / "templates"

MONTHS = ("января", "февраля", "марта", "апреля", "мая", "июня",
          "июля", "августа", "сентября", "октября", "ноября", "декабря")


# --------------------------------------------------------------------------- #
#  Утилиты
# --------------------------------------------------------------------------- #

def esc(value: str) -> str:
    """Экранирование для вставки в HTML-текст и в значения атрибутов."""
    return html.escape(str(value), quote=True)


def read(name: str) -> str:
    return (TEMPLATES / name).read_text(encoding="utf-8")


def fill(template: str, values: dict) -> str:
    """Подстановка {{ключ}}. Два прохода — компоненты могут содержать токены."""
    for _ in range(2):
        for key, value in values.items():
            template = template.replace("{{%s}}" % key, str(value))
    return template


def check_leftovers(page: str, filename: str) -> None:
    left = sorted(set(re.findall(r"\{\{([a-z_0-9]+)\}\}", page)))
    if left:
        print("  ! %s: незаполненные токены: %s" % (filename, ", ".join(left)))


def icon(name: str, extra_class: str = "") -> str:
    cls = ("icon " + extra_class).strip()
    return '<svg class="%s" aria-hidden="true"><use href="#i-%s"></use></svg>' % (cls, name)


def city_page(slug: str) -> str:
    return "remont-trenazherov-%s.html" % slug


# --------------------------------------------------------------------------- #
#  Компоненты
# --------------------------------------------------------------------------- #

def render_stats(cfg: dict) -> str:
    out = []
    for s in cfg["stats"]:
        digits = re.sub(r"\D", "", s["value"])
        value = ('<span data-count="%s">0</span>' % digits) if digits == s["value"] else esc(s["value"])
        out.append(
            '<div class="stat">'
            '<div class="stat__value">%s<span class="stat__suffix">%s</span></div>'
            '<div class="stat__label">%s</div>'
            '</div>' % (value, esc(s["suffix"]), esc(s["label"]))
        )
    return "\n".join(out)


def render_usp(cfg: dict) -> str:
    out = []
    for u in cfg["usp"]:
        out.append(
            '<article class="card reveal">'
            '<span class="card__icon">%s</span>'
            '<h3>%s</h3><p>%s</p>'
            '</article>' % (icon(u["icon"]), esc(u["title"]), esc(u["text"]))
        )
    return "\n".join(out)


def render_services(cfg: dict, limit: int | None = None) -> str:
    out = []
    for s in cfg["services"][:limit]:
        points = "".join("<li>%s</li>" % esc(p) for p in s["points"])
        out.append(
            '<article class="card reveal" id="service-%s">'
            '<span class="card__icon">%s</span>'
            '<span class="card__price">%s</span>'
            '<h3>%s</h3><p>%s</p>'
            '<ul class="card__list">%s</ul>'
            '</article>' % (esc(s["slug"]), icon(s["icon"]), esc(s["price"]),
                            esc(s["title"]), esc(s["text"]), points)
        )
    return "\n".join(out)


def render_equipment(cfg: dict) -> str:
    out = []
    for e in cfg["equipment"]:
        out.append(
            '<article class="eq-card reveal">'
            '<span class="eq-card__icon">%s</span>'
            '<div><h3>%s</h3><p>%s</p></div>'
            '</article>' % (icon(e["icon"]), esc(e["title"]), esc(e["text"]))
        )
    return "\n".join(out)


def render_failures(cfg: dict, limit: int | None = None) -> str:
    return "\n".join(
        "<li>%s<span>%s</span></li>" % (icon("alert"), esc(f))
        for f in cfg["failures"][:limit]
    )


def render_steps(cfg: dict) -> str:
    return "\n".join(
        '<div class="step"><h3>%s</h3><p>%s</p></div>' % (esc(s["title"]), esc(s["text"]))
        for s in cfg["steps"]
    )


def render_clients(cfg: dict) -> str:
    return "\n".join(
        '<article class="card reveal">'
        '<span class="card__icon">%s</span><h3>%s</h3><p>%s</p></article>'
        % (icon(c["icon"]), esc(c["title"]), esc(c["text"]))
        for c in cfg["clients"]
    )


def render_brands(cfg: dict) -> str:
    return "\n".join("<li>%s</li>" % esc(b) for b in cfg["brands"])


def render_prices(cfg: dict) -> str:
    out = []
    for i, group in enumerate(cfg["price_groups"]):
        rows = "".join(
            "<tr><td>%s</td><td>%s</td></tr>" % (esc(name), esc(price))
            for name, price in group["rows"]
        )
        out.append(
            '<details class="price-group"%s>'
            '<summary>%s</summary>'
            '<table class="price-table">'
            '<caption class="visually-hidden">Цены: %s</caption>'
            '<thead class="visually-hidden"><tr><th scope="col">Работа</th><th scope="col">Стоимость</th></tr></thead>'
            '<tbody>%s</tbody></table></details>'
            % (" open" if i == 0 else "", esc(group["title"]), esc(group["title"]), rows)
        )
    return "\n".join(out)


def render_price_notes(cfg: dict) -> str:
    return "\n".join("<li>%s%s</li>" % (icon("info"), esc(n)) for n in cfg["price_notes"])


def render_city_cards(cfg: dict, exclude: str | None = None) -> str:
    out = []
    for c in cfg["cities"]:
        if c["slug"] == exclude:
            continue
        out.append(
            '<a class="city-card reveal" href="%s">'
            '<span class="city-card__pin">%s</span>'
            '<h3>Ремонт тренажёров<br>%s</h3>'
            '<p>%s</p>'
            '<span class="city-card__more">Подробнее %s</span>'
            '</a>' % (city_page(c["slug"]), icon("pin"), esc(c["in"]),
                      esc(c["lead"]), icon("arrow-right"))
        )
    return "\n".join(out)


def render_reviews(cfg: dict) -> str:
    out = []
    for r in cfg["reviews"]:
        stars = "".join(icon("star", "icon--fill") for _ in range(int(r["rating"])))
        initial = esc(r["name"].strip()[:1].upper() or "?")
        out.append(
            '<article class="review reveal">'
            '<div class="review__stars" role="img" aria-label="Оценка %s из 5">%s</div>'
            '<p class="review__text">%s</p>'
            '<div class="review__meta">'
            '<span class="review__avatar" aria-hidden="true">%s</span>'
            '<span><span class="review__name">%s</span><br>'
            '<span class="review__role">%s</span></span>'
            '</div></article>'
            % (r["rating"], stars, esc(r["text"]), initial, esc(r["name"]), esc(r["role"]))
        )
    return "\n".join(out)


def render_faq(cfg: dict, limit: int | None = None) -> str:
    out = []
    for item in cfg["faq"][:limit]:
        out.append(
            '<details class="faq__item">'
            '<summary><span>%s</span><span class="plus" aria-hidden="true"></span></summary>'
            '<div class="faq__answer"><p>%s</p></div>'
            '</details>' % (esc(item["q"]), esc(item["a"]))
        )
    return "\n".join(out)


def render_form(cfg: dict, uid: str, heading: str, note: str, city: str = "",
                reveal: bool = True) -> str:
    """Форма заявки. uid делает id полей уникальными на странице.

    reveal=False — для формы внутри <dialog>: анимация появления там не нужна
    и вредна, потому что IntersectionObserver не видит закрытое окно и форма
    навсегда остаётся прозрачной.
    """
    brand = cfg["brand"]
    endpoint = brand.get("form_endpoint", "")

    return f"""<div class="lead-card{' reveal' if reveal else ''}">
  <h2>{esc(heading)}</h2>
  <p class="lead-card__note">{esc(note)}</p>

  <form data-form data-endpoint="{esc(endpoint)}" method="post" action="{esc(endpoint) or '#'}" novalidate>
    <input type="hidden" name="source" value="{esc(city or 'Главная страница')}">
    <input type="text" name="company" tabindex="-1" autocomplete="off" class="visually-hidden" aria-hidden="true">

    <div class="field">
      <label for="{uid}-name">Ваше имя <span class="field__req" aria-hidden="true">*</span></label>
      <input class="input" id="{uid}-name" name="name" type="text" required
             autocomplete="name" placeholder="Как к вам обращаться">
      <span class="field__error" role="alert"></span>
    </div>

    <div class="field">
      <label for="{uid}-phone">Телефон <span class="field__req" aria-hidden="true">*</span></label>
      <input class="input" id="{uid}-phone" name="phone" type="tel" required
             autocomplete="tel" inputmode="tel" placeholder="+7 (___) ___-__-__">
      <span class="field__hint">Перезвоним в течение 15 минут в рабочее время</span>
      <span class="field__error" role="alert"></span>
    </div>

    <div class="field">
      <label class="check">
        <input type="checkbox" name="consent" required>
        <span>Согласен на обработку персональных данных в соответствии с
          <a href="privacy.html">политикой конфиденциальности</a></span>
      </label>
      <span class="field__error" role="alert"></span>
    </div>

    <button class="btn btn--primary btn--block" type="submit">Отправить заявку</button>

    <p class="form__status" role="status" aria-live="polite"></p>

    <div class="form__alt">
      <span>Или напишите сразу:</span>
      <a class="chip-link" href="https://wa.me/{esc(brand['whatsapp'])}" target="_blank" rel="noopener">
        {icon('chat')} WhatsApp
      </a>
      <a class="chip-link" href="https://t.me/{esc(brand['telegram'])}" target="_blank" rel="noopener">
        {icon('send')} Telegram
      </a>
    </div>
  </form>
</div>"""


# --------------------------------------------------------------------------- #
#  Structured data
# --------------------------------------------------------------------------- #

def jsonld_business(cfg: dict, city: dict | None = None) -> str:
    brand = cfg["brand"]
    areas = [{"@type": "City", "name": c["name"]} for c in cfg["cities"]]
    name = brand["name"] if city is None else "%s — ремонт тренажёров %s" % (brand["name"], city["in"])

    data = {
        "@context": "https://schema.org",
        "@type": ["LocalBusiness", "HomeAndConstructionBusiness"],
        "name": name,
        "description": brand["slogan"],
        "url": brand["site_url"] + ("/" if city is None else "/" + city_page(city["slug"])),
        "telephone": brand["phone_raw"],
        "email": brand["email"],
        "priceRange": "₽₽",
        "image": brand["site_url"] + "/assets/img/favicon.svg",
        "address": {
            "@type": "PostalAddress",
            "addressLocality": "Пятигорск",
            "addressRegion": "Ставропольский край",
            "addressCountry": "RU",
            "streetAddress": brand["address"],
        },
        "geo": {
            "@type": "GeoCoordinates",
            "latitude": brand["geo"]["lat"],
            "longitude": brand["geo"]["lon"],
        },
        "openingHours": brand["work_hours_iso"],
        "areaServed": areas,
        "makesOffer": [
            {
                "@type": "Offer",
                "itemOffered": {"@type": "Service", "name": s["title"], "description": s["text"]},
            }
            for s in cfg["services"]
        ],
    }
    return json.dumps(data, ensure_ascii=False, indent=None)


def jsonld_faq(cfg: dict) -> str:
    data = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": item["q"],
                "acceptedAnswer": {"@type": "Answer", "text": item["a"]},
            }
            for item in cfg["faq"]
        ],
    }
    return json.dumps(data, ensure_ascii=False)


def jsonld_breadcrumbs(cfg: dict, city: dict) -> str:
    base = cfg["brand"]["site_url"]
    data = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Главная", "item": base + "/"},
            {"@type": "ListItem", "position": 2,
             "name": "Ремонт тренажёров %s" % city["in"],
             "item": "%s/%s" % (base, city_page(city["slug"]))},
        ],
    }
    return json.dumps(data, ensure_ascii=False)


# --------------------------------------------------------------------------- #
#  Сборка страниц
# --------------------------------------------------------------------------- #

def base_values(cfg: dict) -> dict:
    brand = cfg["brand"]
    today = date.today()
    footer_cities = "\n".join(
        '<li><a href="%s">Ремонт тренажёров %s</a></li>' % (city_page(c["slug"]), esc(c["in"]))
        for c in cfg["cities"]
    )
    return {
        "brand_name": esc(brand["name"]),
        "legal_name": esc(brand["legal_name"]),
        "inn": esc(brand["inn"]),
        "phone_display": esc(brand["phone_display"]),
        "phone_raw": esc(brand["phone_raw"]),
        "phone2_display": esc(brand["phone2_display"]),
        "phone2_raw": esc(brand["phone2_raw"]),
        "email": esc(brand["email"]),
        "whatsapp": esc(brand["whatsapp"]),
        "telegram": esc(brand["telegram"]),
        "address": esc(brand["address"]),
        "work_hours": esc(brand["work_hours"]),
        "site_url": esc(brand["site_url"]),
        "year": today.year,
        "today": "%d %s %d г." % (today.day, MONTHS[today.month - 1], today.year),
        "footer_cities": footer_cities,
        "icons": read("icons.svg"),
        "root": "",
        "home": "index.html",
        "head_extra": metrika(cfg),
        "body_extra": "",
        # Переопределяется на страницах городов — чтобы в заявке был виден город.
        "modal_form": render_form(cfg, "modal", "Вызвать мастера",
                                  "Перезвоним в течение 15 минут. Диагностика бесплатно.",
                                  reveal=False),
    }


def metrika(cfg: dict) -> str:
    mid = cfg["brand"].get("metrika_id", "").strip()
    if not mid:
        return "<!-- Счётчик не подключён: укажите brand.metrika_id в config.json -->"
    return (
        '<script>\n'
        '(function(m,e,t,r,i,k,a){m[i]=m[i]||function(){(m[i].a=m[i].a||[]).push(arguments)};\n'
        'm[i].l=1*new Date();k=e.createElement(t),a=e.getElementsByTagName(t)[0],k.async=1,\n'
        'k.src=r,a.parentNode.insertBefore(k,a)})(window,document,"script",\n'
        '"https://mc.yandex.ru/metrika/tag.js","ym");\n'
        'ym(%s,"init",{clickmap:true,trackLinks:true,accurateTrackBounce:true,webvisor:true});\n'
        '</script>\n'
        '<noscript><div><img src="https://mc.yandex.ru/watch/%s" '
        'style="position:absolute;left:-9999px" alt=""></div></noscript>' % (mid, mid)
    )


def build_index(cfg: dict, base: str, shared: dict) -> str:
    brand = cfg["brand"]
    hero_links = ", ".join(
        '<a href="%s">%s</a>' % (city_page(c["slug"]), esc(c["name"])) for c in cfg["cities"]
    )

    content = fill(read("index.html"), {
        "hero_city_links": hero_links,
        "hero_form": render_form(cfg, "hero",
                                 "Вызвать мастера",
                                 "Ответим на заявку в течение 15 минут. Диагностика бесплатно."),
        "main_form": render_form(cfg, "lead",
                                 "Заявка на ремонт",
                                 "Заполните форму — мастер свяжется с вами и уточнит детали."),
        "stats": render_stats(cfg),
        "usp_cards": render_usp(cfg),
        "services_cards": render_services(cfg),
        "equipment_cards": render_equipment(cfg),
        "failures_list": render_failures(cfg),
        "price_groups": render_prices(cfg),
        "price_notes": render_price_notes(cfg),
        "steps": render_steps(cfg),
        "clients_cards": render_clients(cfg),
        "brands": render_brands(cfg),
        "city_cards": render_city_cards(cfg),
        "reviews": render_reviews(cfg),
        "faq": render_faq(cfg),
    })

    values = dict(shared)
    values.update({
        "title": "Ремонт спортивных тренажёров на КМВ — Пятигорск, Ессентуки, Кисловодск, "
                 "Железноводск, Минводы | %s" % brand["name"],
        "description": "Ремонт и обслуживание спортивного оборудования на Кавминводах. "
                       "Беговые дорожки, велотренажёры, эллипсоиды, силовые станции. "
                       "Выезд мастера бесплатно, ремонт в день обращения, гарантия 12 месяцев. "
                       "Телефон %s." % brand["phone_display"],
        "canonical": brand["site_url"] + "/",
        "jsonld": "[%s,%s]" % (jsonld_business(cfg), jsonld_faq(cfg)),
        "content": content,
    })
    return fill(base, values)


def build_city(cfg: dict, base: str, shared: dict, city: dict) -> str:
    brand = cfg["brand"]

    content = fill(read("city.html"), {
        "city_name": esc(city["name"]),
        "city_in": esc(city["in"]),
        "city_gen": esc(city["gen"]),
        "city_lead": esc(city["lead"]),
        "city_areas": esc(city["areas"]),
        "city_local": esc(city["local"]),
        "hero_form": render_form(cfg, "hero", "Вызвать мастера %s" % city["in"],
                                 "Перезвоним за 15 минут и назовём предварительную цену.",
                                 city=city["name"]),
        "main_form": render_form(cfg, "lead", "Заявка на ремонт %s" % city["in"],
                                 "Диагностика на месте — бесплатно при согласии на ремонт.",
                                 city=city["name"]),
        "stats": render_stats(cfg),
        "services_cards": render_services(cfg, limit=6),
        "failures_list": render_failures(cfg, limit=8),
        "steps": render_steps(cfg),
        "other_cities": render_city_cards(cfg, exclude=city["slug"]),
        "faq": render_faq(cfg, limit=5),
    })

    values = dict(shared)
    values.update({
        "title": "Ремонт тренажёров %s — выезд мастера, гарантия 12 месяцев | %s"
                 % (city["in"], brand["name"]),
        "description": "Ремонт спортивных тренажёров %s: беговые дорожки, велотренажёры, "
                       "эллипсоиды, силовые станции. Бесплатный выезд и диагностика, "
                       "ремонт на дому, гарантия 12 месяцев. Телефон %s."
                       % (city["in"], brand["phone_display"]),
        "canonical": "%s/%s" % (brand["site_url"], city_page(city["slug"])),
        "jsonld": "[%s,%s]" % (jsonld_business(cfg, city), jsonld_breadcrumbs(cfg, city)),
        "content": content,
        "modal_form": render_form(cfg, "modal", "Вызвать мастера %s" % city["in"],
                                  "Перезвоним в течение 15 минут. Диагностика бесплатно.",
                                  city=city["name"], reveal=False),
    })
    return fill(base, values)


def build_privacy(cfg: dict, base: str, shared: dict) -> str:
    brand = cfg["brand"]
    values = dict(shared)
    values.update({
        "title": "Политика конфиденциальности | %s" % brand["name"],
        "description": "Порядок обработки и защиты персональных данных пользователей сайта %s."
                       % brand["name"],
        "canonical": brand["site_url"] + "/privacy.html",
        "jsonld": jsonld_business(cfg),
        "content": fill(read("privacy.html"), shared),
        "head_extra": shared["head_extra"] + '\n<meta name="robots" content="noindex, follow">',
    })
    return fill(base, values)


def build_sitemap(cfg: dict) -> str:
    base = cfg["brand"]["site_url"]
    today = date.today().isoformat()
    urls = [(base + "/", "1.0")]
    urls += [("%s/%s" % (base, city_page(c["slug"])), "0.8") for c in cfg["cities"]]
    urls.append((base + "/privacy.html", "0.2"))

    body = "\n".join(
        "  <url><loc>%s</loc><lastmod>%s</lastmod><priority>%s</priority></url>" % (u, today, p)
        for u, p in urls
    )
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n%s\n</urlset>\n' % body)


def build_robots(cfg: dict) -> str:
    base = cfg["brand"]["site_url"]
    return ("User-agent: *\n"
            "Allow: /\n"
            "Disallow: /privacy.html\n\n"
            "Sitemap: %s/sitemap.xml\n" % base)


# --------------------------------------------------------------------------- #

def main() -> int:
    cfg_path = ROOT / "config.json"
    if not cfg_path.exists():
        print("Не найден config.json рядом с build.py")
        return 1

    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    base = read("base.html")
    shared = base_values(cfg)

    written = []

    def write(name: str, text: str) -> None:
        (ROOT / name).write_text(text, encoding="utf-8")
        check_leftovers(text, name)
        written.append((name, len(text.encode("utf-8"))))

    write("index.html", build_index(cfg, base, shared))
    for city in cfg["cities"]:
        write(city_page(city["slug"]), build_city(cfg, base, shared, city))
    write("privacy.html", build_privacy(cfg, base, shared))
    write("sitemap.xml", build_sitemap(cfg))
    write("robots.txt", build_robots(cfg))

    print("Сборка завершена — %d файлов:" % len(written))
    for name, size in written:
        print("  %-42s %7.1f КБ" % (name, size / 1024))

    brand = cfg["brand"]
    warnings = []
    if "000-00-00" in brand["phone_display"]:
        warnings.append("телефон (brand.phone_display / phone_raw)")
    if "example.ru" in brand["email"] or "example.ru" in brand["site_url"]:
        warnings.append("почта и домен (brand.email / brand.site_url)")
    if not brand.get("form_endpoint"):
        warnings.append("приёмник заявок (brand.form_endpoint) — форма пока не отправляется")
    if cfg["brand"].get("reviews_are_placeholders"):
        warnings.append("отзывы в блоке reviews — сейчас это заглушки, замените на реальные")

    if warnings:
        print("\nОсталось заполнить в config.json:")
        for w in warnings:
            print("  • %s" % w)

    return 0


if __name__ == "__main__":
    sys.exit(main())
