# LADS Data

**API: https://dareart03.github.io/lads-data/** (формат ниже, «Публикуемый
формат»)

Игровые данные для приложения MemoryTracker (Love and Deepspace): памяти,
баннеры, достижения, события и еженедельные ротации. Публикуются как
статические JSON-файлы и WebP-картинки.

## Структура

- `data/generated/` — собирается скриптами из вики. Руками не редактировать.
- `data/manual/` — правки, дополнения и анонсы. Редактируй здесь (или через
  pull request); форматы описаны в `data/manual/README.md`.
- `data/static/` — постоянные игровые константы (характеристики карт
  мемории, ротации, затраты на апгрейд карт, манифест иконок).
- `images/` — уменьшенные WebP-картинки (иконки карт, портреты, баннеры
  событий, игровые иконки ресурсов).
- `schemas/` — JSON-схемы, задающие формат каждой записи.
- `tools/` — Python-скрипты пайплайна.

## Пайплайн

Запуск из корня репозитория, с активированным виртуальным окружением
(`pip install -r requirements.txt`):

```
python tools/fetch_raw.py                 # 1. сырые таблицы вики (Memories, Events)
python tools/update_memories.py           # 2. data/generated/memories.json
python tools/update_banners.py            # 3. data/generated/banners.json (виш-пулы)
python tools/update_events.py             # 3c. остальное из таблицы Events
python tools/update_stats.py              # 4. статы первого уровня с карточных страниц
python tools/update_achievements.py       # 5. data/generated/achievements.json
python tools/merge.py                     # 6. ручные файлы + характеристики → финальные файлы
python tools/validate.py                  #    проверка dist/data по схемам
python tools/update_images.py             # 7. images/cards + portraits + баннеры событий + icons (WebP)
python tools/pack_images.py               # 8. images.zip + манифесты (падает при отсутствии арта карт)
```

`tools/dist/` в репозиторий не коммитится; workflow публикации в GitHub
Actions собирает его с нуля и раздаёт как data API приложения.

Скрипты обновления никогда не трогают `data/manual/` — твои данные лежат
там и переживают каждый прогон. Каждый скрипт также печатает, какие названия
появились и какие исчезли на вики с прошлого прогона, — переименование
или удаление всегда видно в логе.

## Публикуемый формат (tools/dist/)

- `index.json` — `version` (короткий хеш опубликованного содержимого:
  меняется только когда данные или картинки реально изменились, поэтому
  клиенты качают только настоящие обновления), `generatedAt` (время
  последнего прогона пайплайна — меняется каждый запуск, по нему удобно
  проверять, что расписание работает) и точки входа:
  `data.memories|banners|achievements|events|rotations|upgradeCosts|icons`
  (файл и число записей) и `images` (zip, мета-файл, число файлов, папки).
- `data/memories.json` — массив записей Memory (см. `schemas/memory.schema.json`).
  `iconArt` и `portraitArt` — имена файлов в `images.zip` (папки `cards/`
  и `portraits/`).
- `data/banners.json`, `data/achievements.json` — то же самое, см.
  `schemas/banner.schema.json` и `schemas/achievement.schema.json`.
- `data/events.json` — всё из таблицы Events, что не виш-пул (логины,
  promise, распродажи, mini и т.д.), формат как у баннеров. Повторяющиеся
  события (Hunting Season, Illusio, ...) идут по строке на период, поэтому
  несколько строк могут делить одно имя — сопоставляй также по `startDate`.
  Поле `image` — имя баннера в папке `events/` (пустая строка, если на вики
  баннера нет). Вместе с `banners.json` это датасет для экранов «что сейчас
  активно / что начнётся следующим» с таймерами обратного отсчёта:
  `startDate`, `endDate` и `timeReference` (`UTC+8` / `Server Time`) дают
  приложению всё для расчёта оставшегося времени; `status: "announced"` —
  записи, у которых дат ещё нет.
- `data/rotations.json` — еженедельные ротации фарма: чьи стадии Orbit и какие
  цвета протокоров в Core Hunt открыты в каждый день недели. Ведётся вручную
  в `data/static/` — у вики нет машиночитаемого источника; сверяй с игрой
  при выходе нового лавера. Приложение считает день недели в поясе
  `timeReference` и смотрит нужную строку.
- `data/upgrade_costs.json` — затраты на прокачку памяти по редкостям
  (`"3"`, `"4"`, `"5"`, см. `schemas/upgrade_costs.schema.json`). Две части:
  `expPerLevel` — опыт перехода с каждого уровня на следующий (79 значений:
  индекс N-1 = переход с уровня N на N+1); `brackets` — по строке на десятку
  уровней: EXP за прохождение интервала и золото/кристаллы, payable когда
  карта достигает конца интервала; последняя строка (71–80) — пробуждение на
  80 уровне (`heart` — редкость Awakening Heart). Ведётся вручную в
  `data/static/`, значения сверены с игровым калькулятором сообщества (xlsx);
  вики-шаблон `Memory Upgrade Cost` местами расходится с игрой, поэтому
  источник истины — эта таблица.
- `data/icons.json` — манифест игровых иконок: стабильный ключ → файл
  `icons/<ключ>.webp`. Ключи: `rarity_3/4/5` (звёзды), `position_lunar/solar`,
  `stellactrum_<цвет>` (6 шт.), `talent_atk/def/hp`, `gold`, `diamond`,
  `stardust`, `lunar_emblem`, `title`, `crystal_<n|r|sr>_<цвет>` (18 шт.),
  `exp_bottle_<n|r|sr|ssr>`, `awakening_heart_sr/ssr`, `memory_rank_0–3`,
  `memory_pair_1–4/link` — плюс иконки наград достижений: `medal`,
  `empyrean_wish`, `home_coin`, `bgm`, `chest`, `decor_set` (у типов
  наград Badge/Avatar Frame/Tap Effect/Ring на вики джинерик-иконок нет —
  только у конкретных предметов). Список файлов для скачивания с вики — в
  `data/static/icons.json`.
- `images.zip` — все картинки в папках `cards/` (иконки 256×256),
  `portraits/` (арты карт, до 1080×1440, WebP q75), `events/` (баннеры
  826×280) и `icons/`
  (игровые иконки: звёзды, слоты, стеллактрумы, таланты, валюты, кристаллы,
  бутылки опыта, сердца — оригиналы с вики, без ресайза). Имена
  строятся от базового имени иконки вики с пробелами → подчёркивания,
  напр. `cards/Zayne_Shattered_Simulacrum_icon.webp`,
  `portraits/Zayne_Shattered_Simulacrum_portrait.webp`,
  `events/Illusio_banner.webp`, `icons/gold.webp`.
- `cards/`, `portraits/`, `events/`, `icons/` — те же картинки отдельными
  файлами. Приложению, которому нужно несколько картинок, проще дёргать их
  сразу по URL (`cards/<iconArt>`, `portraits/<portraitArt>`,
  `events/<image>`, `icons/<ключ из data/icons.json>.webp`),
  не распаковывая zip; архив — для тех, кто хочет всё одной загрузкой.
- `images_meta.json` — `version`, `generatedAt` и список `files` с `path`,
  `bytes` и `sha256` каждого файла для проверки целостности.

GitHub Pages отдаёт только конкретные файлы: URL папки (`/cards/`) вернёт
404 — это нормально, список файлов есть в `images_meta.json`.

## Публикация

Workflow `.github/workflows/publish.yml` запускается по пушу в `main`, по
расписанию (каждый день в 06:30 по Москве, 03:30 UTC — после утренних
обновлений в игре) и вручную (вкладка Actions). Он прогоняет весь пайплайн,
валидирует данные и публикует `tools/dist/` на GitHub Pages. Pages
включается один раз вручную: Settings → Pages → Source → GitHub Actions.

## Атрибуция

Текстовые данные взяты из вики Love and Deepspace
(https://loveanddeepspace.wiki.gg/), лицензия CC BY-SA 4.0.
Арты и имена принадлежат их правообладателям.
Это неофициальный фан-проект.
