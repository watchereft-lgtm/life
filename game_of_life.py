"""Игра «Жизнь» Джона Конвея в Streamlit.

Запуск:
    pip install streamlit numpy pillow
    streamlit run game_of_life.py
"""

from __future__ import annotations

import time

import numpy as np
import streamlit as st

import life_core as life

st.set_page_config(page_title="Жизнь Конвея", page_icon="🧬", layout="wide")

MAX_HISTORY = 600


# --------------------------------------------------------------------------
# Состояние
# --------------------------------------------------------------------------


def init_state() -> None:
    ss = st.session_state
    ss.setdefault("rows", 45)
    ss.setdefault("cols", 70)
    ss.setdefault("wrap", True)
    ss.setdefault("birth", life.parse_rule("B3/S23")[0])
    ss.setdefault("survive", life.parse_rule("B3/S23")[1])
    ss.setdefault("grid", life.empty_grid(ss["rows"], ss["cols"]))
    ss.setdefault("generation", 0)
    ss.setdefault("history", [])
    ss.setdefault("running", False)
    ss.setdefault("dirty_rule", False)


def resize(rows: int, cols: int) -> None:
    """Пересоздаёт поле под новый размер, сохраняя старые клетки в левом верхнем углу."""
    old = st.session_state["grid"]
    new = life.empty_grid(rows, cols)
    r = min(rows, old.shape[0])
    c = min(cols, old.shape[1])
    new[:r, :c] = old[:r, :c]
    st.session_state["grid"] = new
    st.session_state["rows"], st.session_state["cols"] = rows, cols


def reset_history() -> None:
    st.session_state["history"] = [life.population(st.session_state["grid"])]
    st.session_state["generation"] = 0


def advance() -> None:
    """Один шаг эволюции + запись в историю."""
    ss = st.session_state
    ss["grid"] = life.step(ss["grid"], ss["birth"], ss["survive"], wrap=ss["wrap"])
    ss["generation"] += 1
    ss["history"].append(life.population(ss["grid"]))
    if len(ss["history"]) > MAX_HISTORY:
        del ss["history"][: len(ss["history"]) - MAX_HISTORY]


init_state()
ss = st.session_state

# --------------------------------------------------------------------------
# Панель управления
# --------------------------------------------------------------------------

with st.sidebar:
    st.title("🧬 Жизнь Конвея")
    st.caption("Клеточный автомат, придуманный Джоном Хортоном Конвеем в 1970 году.")

    st.subheader("Эволюция")
    c1, c2 = st.columns(2)
    if c1.button("▶ Пуск" if not ss["running"] else "⏸ Пауза", use_container_width=True):
        ss["running"] = not ss["running"]
        st.rerun()
    if c2.button("⏭ Шаг", use_container_width=True, disabled=ss["running"]):
        advance()
        st.rerun()

    speed = st.slider("Скорость, шагов/сек", 1, 30, 8)

    st.subheader("Поле")
    rows = st.slider("Строк", 10, 120, ss["rows"])
    cols = st.slider("Столбцов", 10, 160, ss["cols"])
    if (rows, cols) != (ss["rows"], ss["cols"]):
        resize(rows, cols)

    wrap = st.toggle("Тороидальное поле (края замкнуты)", value=ss["wrap"])
    ss["wrap"] = wrap

    cell_px = st.slider("Размер клетки, px", 3, 20, 8)
    gridlines = st.toggle("Сетка", value=True)

    st.subheader("Правило")
    rule_text = st.text_input("Нотация B/S", value=life.rule_to_text(ss["birth"], ss["survive"]))
    try:
        birth, survive = life.parse_rule(rule_text)
        if not np.array_equal(birth, ss["birth"]) or not np.array_equal(survive, ss["survive"]):
            ss["birth"], ss["survive"] = birth, survive
            st.rerun()
    except ValueError as exc:
        st.error(str(exc))
    st.caption("B3/S23 — классика. B36/S23 — HighLife. B3/S12345 — «День и ночь».")

    st.subheader("Заполнение")
    density = st.slider("Плотность случайного заполнения", 0.02, 0.9, 0.25, 0.01)
    b1, b2, b3 = st.columns(3)
    if b1.button("🎲 Случайно", use_container_width=True):
        ss["grid"] = life.random_grid(ss["rows"], ss["cols"], density)
        ss["running"] = False
        reset_history()
        st.rerun()
    if b2.button("🧹 Очистить", use_container_width=True):
        ss["grid"] = life.empty_grid(ss["rows"], ss["cols"])
        ss["running"] = False
        reset_history()
        st.rerun()
    if b3.button("🔄 Сброс", use_container_width=True):
        for key in ("grid", "generation", "history", "running"):
            ss.pop(key, None)
        st.rerun()

    st.subheader("Фигуры")
    name = st.selectbox("Готовая фигура", list(life.PATTERNS))
    pat = life.pattern(name)
    st.code("\n".join(
        "".join("■" if v else "·" for v in row) for row in pat
    ), language=None)
    p1, p2 = st.columns(2)
    top = p1.number_input("Строка", 0, max(ss["rows"] - 1, 0), max(ss["rows"] // 2 - pat.shape[0] // 2, 0))
    left = p2.number_input("Столбец", 0, max(ss["cols"] - 1, 0), max(ss["cols"] // 2 - pat.shape[1] // 2, 0))
    s1, s2 = st.columns(2)
    if s1.button("➕ Поставить", use_container_width=True):
        life.place(ss["grid"], pat, int(top), int(left), wrap=ss["wrap"])
        reset_history()
        st.rerun()
    if s2.button("🎯 В центр", use_container_width=True):
        r0 = max((ss["rows"] - pat.shape[0]) // 2, 0)
        c0 = max((ss["cols"] - pat.shape[1]) // 2, 0)
        life.place(ss["grid"], pat, r0, c0, wrap=False)
        reset_history()
        st.rerun()

    with st.expander("Свой узор (ASCII)"):
        custom = st.text_area(
            "Точка/пробел — пусто, любой символ — жизнь",
            value=".OO\nOO.\n.O.",
            height=120,
        )
        if st.button("Поставить свой узор", use_container_width=True):
            try:
                life.place(ss["grid"], life.from_text(custom), int(top), int(left), wrap=ss["wrap"])
                reset_history()
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))

# --------------------------------------------------------------------------
# Основная область
# --------------------------------------------------------------------------

m1, m2, m3, m4 = st.columns(4)
m1.metric("Поколение", ss["generation"])
m2.metric("Живых клеток", life.population(ss["grid"]))
m3.metric("Поле", f"{ss['rows']} × {ss['cols']}")
m4.metric("Правило", life.rule_to_text(ss["birth"], ss["survive"]))

board = st.empty()
chart = st.empty()

board.image(
    life.render(ss["grid"], cell_px=cell_px, show_gridlines=gridlines),
    use_container_width=True,
)
if len(ss["history"]) > 1:
    chart.line_chart({"Живых клеток": ss["history"]}, height=180)

# Автозапуск: один шаг за перезапуск скрипта — так кнопки остаются отзывчивыми.
if ss["running"]:
    advance()
    board.image(
        life.render(ss["grid"], cell_px=cell_px, show_gridlines=gridlines),
        use_container_width=True,
    )
    if len(ss["history"]) > 1:
        chart.line_chart({"Живых клеток": ss["history"]}, height=180)
    time.sleep(1.0 / max(speed, 1))
    st.rerun()

st.caption(
    "Правила: живая клетка выживает при 2–3 соседях, мёртвая оживает при 3. "
    "Цвет клетки показывает её возраст: зелёный — только что родилась, жёлтый — живёт долго, "
    "красный — очень старая."
)
