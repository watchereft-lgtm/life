"""Проверки интерфейса game_of_life.py без установленного Streamlit.

Модуль `streamlit` подменяется минимальной заглушкой, а сам скрипт
выполняется через runpy — ровно так же, как его запускает Streamlit.
Так проверяются все ветки интерфейса: кнопки, смена правила, размер поля,
автозапуск, неверные входные данные.

Запуск без pytest:   python test_streamlit_ui.py
Запуск через pytest: pytest test_streamlit_ui.py -q

Настоящий Streamlit здесь не нужен — это быстрая проверка логики UI.
Проверка в живом Streamlit — в test_app_streamlit.py.
"""

from __future__ import annotations

import runpy
import sys
import time
import types
from pathlib import Path

import numpy as np

APP = Path(__file__).with_name("game_of_life.py")

MAX_HISTORY = 600  # должно совпадать с константой в game_of_life.py


class Rerun(Exception):
    """Аналог st.rerun(): прерывает выполнение скрипта."""


class SessionState(dict):
    """session_state с доступом через атрибуты, как в Streamlit."""

    def __getattr__(self, item):
        try:
            return self[item]
        except KeyError as exc:  # pragma: no cover — защита от опечаток
            raise AttributeError(item) from exc

    def __setattr__(self, key, value):
        self[key] = value


class _Ctx:
    """Контейнер Streamlit: контекстный менеджер и объект с виджетами."""

    def __init__(self, ui: "UI", name: str = "st"):
        self.ui = ui
        self.name = name

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def __getattr__(self, item):
        def call(*args, **kwargs):
            self.ui.log.append((self.name, item, args, kwargs))
            return None

        return call

    # --- виджеты, влияющие на ход выполнения -----------------------------

    def button(self, label, **kwargs):
        self.ui.log.append((self.name, "button", (label,), kwargs))
        return label == self.ui.press

    def columns(self, n, **kwargs):
        self.ui.log.append((self.name, "columns", (n,), kwargs))
        return tuple(_Ctx(self.ui, f"{self.name}.col{i}") for i in range(n))

    def empty(self):
        return _Ctx(self.ui, f"{self.name}.empty")

    def expander(self, label, **kwargs):
        return _Ctx(self.ui, f"expander[{label}]")

    def slider(self, label, lo, hi, value, *a, **kw):
        return self.ui.sliders.get(label, value)

    def toggle(self, label, value=False, **kw):
        return self.ui.toggles.get(label, value)

    def text_input(self, label, value="", **kw):
        return self.ui.texts.get(label, value)

    def text_area(self, label, value="", **kw):
        return self.ui.areas.get(label, value)

    def selectbox(self, label, options, **kw):
        return self.ui.selects.get(label, list(options)[0])

    def number_input(self, label, lo=None, hi=None, value=0, **kw):
        return self.ui.numbers.get(label, value)


class UI:
    def __init__(self, press=None, sliders=None, toggles=None, texts=None,
                 areas=None, selects=None, numbers=None):
        self.press = press
        self.sliders = sliders or {}
        self.toggles = toggles or {}
        self.texts = texts or {}
        self.areas = areas or {}
        self.selects = selects or {}
        self.numbers = numbers or {}
        self.log: list = []
        self.reran = False

    def images(self) -> list:
        return [entry for entry in self.log if entry[1] == "image"]

    def charts(self) -> list:
        return [entry for entry in self.log if entry[1] == "line_chart"]

    def errors(self) -> list:
        return [entry[2][0] for entry in self.log if entry[1] == "error"]


def build_streamlit_stub(ui: UI) -> types.ModuleType:
    st = types.ModuleType("streamlit")
    st.session_state = SessionState()
    root = _Ctx(ui, "st")
    for name in ("title", "caption", "subheader", "code", "error", "warning",
                 "info", "success", "markdown", "write", "set_page_config",
                 "metric", "image", "line_chart", "dataframe", "toast"):
        setattr(st, name, getattr(root, name))
    st.sidebar = _Ctx(ui, "sidebar")
    st.button = root.button
    st.columns = root.columns
    st.empty = root.empty
    st.expander = root.expander
    st.slider = root.slider
    st.toggle = root.toggle
    st.text_input = root.text_input
    st.text_area = root.text_area
    st.selectbox = root.selectbox
    st.number_input = root.number_input

    def rerun():
        raise Rerun()

    st.rerun = rerun
    return st


def run_app(expect_rerun: bool = False, session: dict | None = None,
            passes: int = 2, **kwargs):
    """Выполняет game_of_life.py на заглушке и возвращает (модуль, UI).

    `passes` — сколько раз разрешено выполнить скрипт: st.rerun() в Streamlit
    запускает скрипт заново, поэтому один клик по кнопке — это два прохода.
    Нажатие кнопки действует только на первом проходе, как в настоящем
    Streamlit: при перезапуске клик уже обработан.
    """
    ui = UI(**kwargs)
    module = build_streamlit_stub(ui)
    for key, value in (session or {}).items():
        module.session_state[key] = value
    sys.modules["streamlit"] = module

    for _ in range(max(passes, 1)):
        try:
            runpy.run_path(str(APP), run_name="__main__")
        except Rerun:
            ui.reran = True
            ui.press = None
            continue
        break

    assert ui.reran is expect_rerun, (
        f"перезапуск скрипта: получено {ui.reran}, ожидалось {expect_rerun}"
    )
    return module, ui


# --------------------------------------------------------------------------
# Отрисовка
# --------------------------------------------------------------------------


def test_start_renders_board_and_metrics():
    _, ui = run_app()
    images = ui.images()
    assert images, "поле должно отрисовываться"
    image = images[0][2][0]
    assert image.size == (70 * 8, 45 * 8), "поле 45x70 при клетке 8 px"
    metrics = [entry for entry in ui.log if entry[1] == "metric"]
    assert len(metrics) >= 4, "нужны метрики: поколение, клетки, размер, правило"
    assert ui.errors() == []


def test_tiny_cells_and_gridlines_off():
    _, ui = run_app(sliders={"Размер клетки, px": 3}, toggles={"Сетка": False})
    assert ui.images()[0][2][0].size == (70 * 3, 45 * 3)


def test_chart_appears_only_with_history():
    _, ui = run_app()
    assert ui.charts() == [], "на первом кадре истории ещё нет"
    _, ui = run_app(session={"history": [1, 2, 3], "generation": 2})
    assert ui.charts(), "с историей график популяции рисуется"


# --------------------------------------------------------------------------
# Кнопки
# --------------------------------------------------------------------------


def test_play_button_starts_autoplay():
    module, ui = run_app(press="▶ Пуск", expect_rerun=True)
    assert module.session_state["running"] is True
    assert module.session_state["generation"] == 1, "автозапуск делает шаг сразу"


def test_step_button_advances_one_generation():
    module, _ = run_app(press="⏭ Шаг", expect_rerun=True)
    assert module.session_state["generation"] == 1


def test_randomize_fills_and_pauses():
    module, _ = run_app(press="🎲 Случайно", expect_rerun=True)
    assert module.session_state["running"] is False
    assert np.count_nonzero(module.session_state["grid"]) > 0
    assert module.session_state["generation"] == 0, "после заполнения счётчик сбрасывается"


def test_clear_empties_board():
    module, _ = run_app(press="🧹 Очистить", expect_rerun=True,
                        session={"grid": np.ones((45, 70), dtype=np.uint8)})
    assert np.count_nonzero(module.session_state["grid"]) == 0


def test_reset_returns_defaults():
    module, _ = run_app(press="🔄 Сброс", expect_rerun=True,
                        session={"generation": 99, "running": True})
    assert module.session_state["generation"] == 0
    assert module.session_state["running"] is False
    assert module.session_state["grid"].shape == (45, 70)


def test_place_pattern_and_center():
    module, _ = run_app(press="➕ Поставить", expect_rerun=True)
    assert np.count_nonzero(module.session_state["grid"]) == 4, "блок — 4 клетки"

    module, _ = run_app(press="🎯 В центр", expect_rerun=True,
                        selects={"Готовая фигура": "Пушка Госпера (Gosper gun)"})
    assert np.count_nonzero(module.session_state["grid"]) == 36, "в пушке 36 клеток"
    grid = module.session_state["grid"]
    assert grid.shape == (45, 70), "пушка не должна вылезать за поле"


def test_place_pattern_on_torus_wraps():
    module, _ = run_app(press="➕ Поставить", expect_rerun=True,
                        numbers={"Строка": 44, "Столбец": 69})
    assert np.count_nonzero(module.session_state["grid"]) == 4


def test_custom_ascii_pattern():
    module, _ = run_app(press="Поставить свой узор", expect_rerun=True,
                        areas={"Точка/пробел — пусто, любой символ — жизнь": ".OO\nOO.\n.O."})
    assert np.count_nonzero(module.session_state["grid"]) == 5


def test_empty_custom_pattern_reports_error():
    _, ui = run_app(press="Поставить свой узор",
                    areas={"Точка/пробел — пусто, любой символ — жизнь": "   \n\n"})
    assert ui.errors(), "пустой узор должен показать ошибку"


# --------------------------------------------------------------------------
# Правило
# --------------------------------------------------------------------------


def test_rule_change_is_applied():
    module, _ = run_app(texts={"Нотация B/S": "B36/S23"}, expect_rerun=True)
    import life_core as life

    birth, survive = life.parse_rule("B36/S23")
    assert np.array_equal(module.session_state["birth"], birth)
    assert np.array_equal(module.session_state["survive"], survive)


def test_bad_rule_keeps_previous_and_shows_error():
    module, ui = run_app(texts={"Нотация B/S": "B3S23"})
    import life_core as life

    assert ui.errors()
    assert np.array_equal(
        module.session_state["birth"], life.parse_rule("B3/S23")[0]
    ), "неверное правило не должно применяться"


# --------------------------------------------------------------------------
# Размер поля и границы
# --------------------------------------------------------------------------


def test_resize_keeps_top_left_corner():
    grid = np.zeros((45, 70), dtype=np.uint8)
    grid[0, 0] = 7
    grid[10, 10] = 3
    module, _ = run_app(sliders={"Строк": 30, "Столбцов": 40}, session={"grid": grid})
    resized = module.session_state["grid"]
    assert resized.shape == (30, 40)
    assert resized[0, 0] == 7, "старые клетки должны переезжать в левый верхний угол"
    assert resized[10, 10] == 3


def test_wrap_toggle_is_stored():
    module, _ = run_app(toggles={"Тороидальное поле (края замкнуты)": False})
    assert module.session_state["wrap"] is False


# --------------------------------------------------------------------------
# Автозапуск
# --------------------------------------------------------------------------


def test_autoplay_step_and_rerun():
    module, ui = run_app(session={"running": True}, expect_rerun=True, passes=1)
    assert module.session_state["generation"] == 1
    assert len(ui.images()) >= 1


def test_autoplay_speed_sets_sleep():
    recorded: list[float] = []
    original = time.sleep
    time.sleep = recorded.append  # type: ignore[assignment]
    try:
        run_app(session={"running": True}, expect_rerun=True, passes=1,
                sliders={"Скорость, шагов/сек": 25})
    finally:
        time.sleep = original
    assert recorded and abs(recorded[-1] - 1 / 25) < 1e-9, (
        f"пауза между кадрами должна быть 1/25 c, получено {recorded}"
    )


def test_history_is_trimmed():
    module, _ = run_app(session={"running": True, "history": [1] * 700},
                        expect_rerun=True, passes=1)
    assert len(module.session_state["history"]) == MAX_HISTORY


def test_paused_app_does_not_sleep():
    recorded: list[float] = []
    original = time.sleep
    time.sleep = recorded.append  # type: ignore[assignment]
    try:
        run_app(session={"running": False})
    finally:
        time.sleep = original
    assert recorded == [], "на паузе скрипт не должен себя перезапускать"


# --------------------------------------------------------------------------
# Запуск без pytest
# --------------------------------------------------------------------------

_TESTS = [value for name, value in sorted(globals().items()) if name.startswith("test_")]


def main() -> int:
    failed: list[str] = []
    for func in _TESTS:
        try:
            func()
        except Exception as exc:  # noqa: BLE001 — в отчёте нужен любой сбой
            failed.append(f"{func.__name__}: {exc}")
            print(f"FAIL  {func.__name__}: {exc}")
        else:
            print(f"PASS  {func.__name__}")
    print(f"\nВсего проверок: {len(_TESTS)}, провалено: {len(failed)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
