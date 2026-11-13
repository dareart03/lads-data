# Ручные данные

Файлы в этой папке редактируются вручную (или через pull request).
Скрипты их никогда не меняют — они только сообщают, какие записи больше
не нужны. В JSON нет комментариев, поэтому форматы описаны здесь.

Ключи — **точные** названия с вики (для карт — `Персонаж: Название`).

## memories_overrides.json
Правки к карте, которая уже есть на вики. Любое поле здесь заменяет
вики-значение.

    { "Caleb: His Gravity": { "stellactrumType": "Amber" } }

## memories_additions.json
Карты, которых на вики ещё нет. Обязателен только `featuredCharacter`,
остальное можно дописать позже. Базовые статы — в `data/static/memory_stats.json`.

    { "Xavier: New Card": { "featuredCharacter": "Xavier", "rarity": "5" } }

Когда вики догонит, merge-отчёт попросит удалить запись.

## banners_overrides.json
Правки к баннеру, который уже есть на вики, например недостающий список
карт.

    { "Some Banner Rerun (2025)": { "featuredMemories": ["Xavier: Some Card"] } }

## banners_additions.json (необязательно)
Анонсированные баннеры, которых на вики ещё нет. Получают
`"status": "announced"`.

    { "Future Banner": { "kind": "limited", "startDate": "2026-12-01 05:00:00",
      "endDate": "2026-12-15 04:59:00", "featuredMemories": ["Xavier: Some Card"] } }

## banner_aliases.json (необязательно)
Старые названия баннера, чтобы сохранённые записи pulls его находили.

    { "Destined Reunion Rerun (2025)": ["Destined Reunion Rerun"] }

## events_additions.json (необязательно)
События, которых на вики ещё нет (анонсированные). Получают
`"status": "announced"`.

    { "Future Event": { "kind": "login", "startDate": "2026-12-01 05:00:00",
      "endDate": "2026-12-07 04:59:00" } }

## events_overrides.json (необязательно)
Правки к событию (применяются ко всем периодам повторяющегося события).

    { "Hunting Season (Core Hunt)": { "tags": ["farm"] } }

## achievements_additions.json
Достижения, которых страница вики не показывает (пока). Ключ — точный
текст достижения. `category` — одна из: Progress, Training, Home,
Spare Time, Kitty Cards, Plushies. Награды можно записать текстом в `reward`
("Diamond|20, Title: Lucky Paw") или, как в данных вики, списком `rewards`.

    { "Some Achievement": { "description": "Do something.", "category": "Spare Time",
      "hidden": false, "reward": "Diamond|20" } }

Когда вики догонит, merge-отчёт попросит удалить запись.

## achievements_overrides.json
Правки к достижению, которое вики уже показывает. Поле здесь заменяет
вики-значение. Сам текст достижения так не изменить — используй алиасы.

    { "Some Achievement": { "description": "Corrected text." } }

## achievement_aliases.json
Старые тексты достижений. Id достижений строится от текста, поэтому
приложение пересчитает старые id и сохранит уже выполненные достижения.

    { "Main Story Clear VIII": ["Under Deepspace Clear VIII / Clear VIII"] }
