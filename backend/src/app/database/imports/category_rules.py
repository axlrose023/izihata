"""Maps a supplier product name onto a catalog category.

Suppliers ship flat stock files with no category column, so the leading noun of
the Ukrainian product name is the only signal available. Rules are ordered:
the first match wins, so put the specific patterns before the generic ones.

A row that matches nothing is still imported, but lands in ``FALLBACK_CATEGORY``
and stays hidden until staff classify it.
"""

import re

FALLBACK_CATEGORY = "other"

# (category slug, subcategory name or None, leading-name pattern)
CATEGORY_RULES: tuple[tuple[str, str | None, str], ...] = (
    ("lowvoltage", "Автомати захисту двигуна", r"Авт\.\s*захисту\s*двиг"),
    ("lowvoltage", "Автоматичні вимикачі (модульні / корпусні / повітряні)", r"Авт\."),
    ("lowvoltage", "Диференціальні автомати", r"Диф\."),
    ("lowvoltage", "ПЗВ (УЗО)", r"(ПЗВ|Пристрій захисн)"),
    ("lowvoltage", "Рубильники та перемикачі", r"(Роз'єднувач|Рубильник)"),
    (
        "lowvoltage",
        "Запобіжники та тримачі",
        r"(Запобіжник|Міні-запобіжник|Тримач|Цоколь|Патрон)",
    ),
    ("lowvoltage", "Контактори", r"(Контактор|Конденсаторна)"),
    ("lowvoltage", None, r"(Обмежувач|Теплове|Розчіплювач|Незалежний|Мінімальний)"),
    (
        "lowvoltage",
        "Додаткові пристрої до автоматів",
        r"(Блок-контакт|Шток|Полюс|Розділювальна|Ввідна|Лицьова|Мотор-привод)",
    ),
    ("lowvoltage", None, r"Вимикач"),
    (
        "switching",
        "Світлосигнальна арматура",
        r"(Лампа\s+сигнальна|Світлосигн|Індикатор)",
    ),
    ("switching", "Кінцеві вимикачі", r"Кінцевий"),
    ("switching", "Мікроперемикачі", r"(Мікроперемикач|Перемикач)"),
    ("switching", "Оповіщувачі та зумери", r"(Зумер|Оповіщ|Сирена)"),
    (
        "switching",
        "Кнопки та пости керування",
        r"(Кнопк|Пост|Рукоятк|Замикальна|Розмикальна|Модуль|Марковальна|Наклад)",
    ),
    ("relay", None, r"(Реле|Датчик|Таймер|Перетворювач|Трансформатор|Котушка)"),
    ("panels", "Модульні електрощити", r"(Щит|Бокс|Шафа)"),
    (
        "panels",
        None,
        r"(Монтажна|Кришка|Дверц|Панель|Металева|Пластиков|Профіль|Рама|Замок|Корпус)",
    ),
    (
        "installation",
        None,
        r"(Клема|Клемна|Перемичка|Шина|Наконечник|Маркер|З'єднув|Ізолятор|Гвинт"
        r"|Гайка|Блок|Хомут|Перехідник|Опорний|Адаптер|Заглушка|Комплект)",
    ),
    ("sockets", None, r"(Розетка|Вилка|Подовжувач)"),
    ("light", None, r"(Лампа|Світильник|Прожектор)"),
    ("cable", None, r"(Кабель|Провід|Гофра|Труба|Короб)"),
    ("hv", None, r"(Повітр\.|Високовольт)"),
)

_COMPILED = tuple(
    (category, subcategory, re.compile(rf"^\s*{pattern}", re.IGNORECASE))
    for category, subcategory, pattern in CATEGORY_RULES
)


def classify(name: str) -> tuple[str, str | None, bool]:
    """Return ``(category_slug, subcategory_name, matched)`` for a product name."""
    for category, subcategory, expression in _COMPILED:
        if expression.match(name):
            return category, subcategory, True
    return FALLBACK_CATEGORY, None, False
