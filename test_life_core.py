"""Проверки ядра игры «Жизнь» (life_core.py).

Запуск без pytest:   python test_life_core.py
Запуск через pytest: pytest test_life_core.py -q

Здесь проверяется именно математика автомата: правила, шаг эволюции,
известные фигуры, тор и границы, разбор нотации B/S, отрисовка.
Streamlit для этих проверок не нужен.
"""

from __future__ import annotations

import numpy as np

import life_core as life

BIRTH, SURVIVE = life.parse_rule("B3/S23")


# --------------------------------------------------------------------------
# Правило
# --------------------------------------------------------------------------


def test_parse_classic_rule():
    birth, survive = life.parse_rule("B3/S23")
    assert birth[3] and not birth[2]
    assert survive[2] and survive[3]
    assert not survive[1] and not survive[0]


def test_rule_round_trip():
    for text in ("B3/S23", "B36/S23", "B3/S12345", "B2/S"):
        assert life.rule_to_text(*life.parse_rule(text)) == text


def test_rule_ignores_spaces_and_case():
    assert np.array_equal(
        life.parse_rule("b3 / s23")[0], life.parse_rule("B3/S23")[0]
    )


def test_bad_rules_raise():
    for bad in ("B3S23", "Bx/S2", "S23", "", "B3/S2x"):
        try:
            life.parse_rule(bad)
        except ValueError:
            continue
        raise AssertionError(f"правило {bad!r} должно было вызвать ValueError")


# --------------------------------------------------------------------------
# Шаг эволюции
# --------------------------------------------------------------------------


def test_block_is_stable():
    grid = life.empty_grid(10, 10)
    life.place(grid, life.from_text("OO\nOO"), 4, 4)
    after = life.step(grid, BIRTH, SURVIVE)
    assert np.array_equal(after > 0, grid > 0)


def test_age_grows_for_survivors():
    grid = life.empty_grid(10, 10)
    life.place(grid, life.from_text("OO\nOO"), 4, 4)
    after = life.step(grid, BIRTH, SURVIVE)
    assert after[4, 4] == 2, "клетка, пережившая шаг, должна постареть"


def test_blinker_has_period_two():
    grid = life.empty_grid(10, 10)
    life.place(grid, life.from_text("OOO"), 5, 4)
    step1 = life.step(grid, BIRTH, SURVIVE)
    step2 = life.step(step1, BIRTH, SURVIVE)
    assert not np.array_equal(step1 > 0, grid > 0), "мигалка обязана измениться"
    assert np.array_equal(step2 > 0, grid > 0), "через два шага мигалка возвращается"
    assert step1[4, 5] and step1[5, 5] and step1[6, 5], "мигалка встаёт вертикально"


def test_glider_moves_diagonally():
    glider = life.from_text(".O.\n..O\nOOO")
    grid = life.empty_grid(20, 20)
    life.place(grid, glider, 2, 2)
    cur = grid
    for _ in range(4):
        cur = life.step(cur, BIRTH, SURVIVE)
    expected = life.empty_grid(20, 20)
    life.place(expected, glider, 3, 3)
    assert np.array_equal(cur > 0, expected > 0), "за 4 шага планер уходит на (1, 1)"
    assert life.population(cur) == 5


def test_lwss_moves_two_cells_left():
    lwss = life.pattern("Лёгкий корабль (LWSS)")
    grid = life.empty_grid(20, 20)
    life.place(grid, lwss, 5, 5)
    cur = grid
    for _ in range(4):
        cur = life.step(cur, BIRTH, SURVIVE)
    expected = life.empty_grid(20, 20)
    life.place(expected, lwss, 5, 3)
    assert np.array_equal(cur > 0, expected > 0)
    assert life.population(cur) == 9


def test_gosper_gun_grows():
    grid = life.empty_grid(40, 60)
    life.place(grid, life.pattern("Пушка Госпера (Gosper gun)"), 2, 2)
    for _ in range(60):
        grid = life.step(grid, BIRTH, SURVIVE)
    assert life.population(grid) > 40, "пушка должна выпускать планеры"


def test_highlife_rule_differs_from_classic():
    # Клетка с шестью живыми соседями: в B3/S23 не рождается, в B36/S23 рождается.
    grid = life.empty_grid(7, 7)
    life.place(grid, life.from_text("OOO\n\nOOO"), 2, 2)
    classic = life.step(grid, *life.parse_rule("B3/S23"))
    highlife = life.step(grid, *life.parse_rule("B36/S23"))
    assert not np.array_equal(classic > 0, highlife > 0), "B36/S23 и B3/S23 дают разное"


# --------------------------------------------------------------------------
# Границы и тор
# --------------------------------------------------------------------------


def test_wrap_and_walls_differ():
    grid = life.empty_grid(6, 6)
    life.place(grid, life.from_text("OOO"), 0, 0)
    assert not np.array_equal(
        life.step(grid, BIRTH, SURVIVE, wrap=True),
        life.step(grid, BIRTH, SURVIVE, wrap=False),
    )


def test_neighbor_count_on_torus_wraps():
    alive = np.zeros((5, 5), dtype=bool)
    alive[0, 0] = True
    assert life.neighbor_count(alive, wrap=True)[4, 4] == 1
    assert life.neighbor_count(alive, wrap=False)[4, 4] == 0


def test_neighbor_count_basics():
    alive = np.zeros((3, 3), dtype=bool)
    alive[1, 1] = True
    assert life.neighbor_count(alive, wrap=False)[0, 0] == 1
    assert life.neighbor_count(alive, wrap=False)[1, 1] == 0


def test_place_clips_and_wraps():
    block = life.from_text("OO\nOO")
    clipped = life.empty_grid(6, 6)
    life.place(clipped, block, 5, 5, wrap=False)
    assert life.population(clipped) == 1, "при обрезке остаётся одна клетка"

    wrapped = life.empty_grid(6, 6)
    life.place(wrapped, block, 5, 5, wrap=True)
    assert life.population(wrapped) == 4, "на торе фигура заворачивается целиком"


# --------------------------------------------------------------------------
# Шаблоны
# --------------------------------------------------------------------------


def test_all_patterns_are_usable():
    for name in life.PATTERNS:
        pat = life.pattern(name)
        assert pat.ndim == 2 and pat.size > 0, name
        assert life.population(pat) > 0, f"{name}: в фигуре нет ни одной живой клетки"


def test_preset_blinker_is_three_cells_and_oscillates():
    grid = life.empty_grid(10, 10)
    life.place(grid, life.pattern("Мигалка (Blinker)"), 5, 4)
    assert life.population(grid) == 3, "мигалка — три клетки в ряд"
    step1 = life.step(grid, BIRTH, SURVIVE)
    assert life.population(step1) == 3
    assert not np.array_equal(step1 > 0, grid > 0)


def test_from_text_ignores_dots_and_spaces():
    pat = life.from_text(".O.\n O \n...")
    assert pat.shape == (3, 3)
    assert life.population(pat) == 2


def test_from_text_keeps_inner_blank_lines():
    pat = life.from_text("OOO\n\nOOO")
    assert pat.shape == (3, 3), "пустой ряд внутри картинки должен сохраняться"
    assert life.population(pat) == 6


def test_from_text_rejects_empty():
    try:
        life.from_text("   \n\n")
    except ValueError:
        return
    raise AssertionError("пустой шаблон должен вызывать ValueError")


def test_random_grid_density():
    rng = np.random.default_rng(0)
    grid = life.random_grid(50, 50, 0.3, rng)
    assert 0.25 < life.population(grid) / 2500 < 0.35


# --------------------------------------------------------------------------
# Отрисовка
# --------------------------------------------------------------------------


def test_render_size_matches_cell_pixels():
    grid = life.empty_grid(6, 6)
    assert life.render(grid, cell_px=5, show_gridlines=True).size == (30, 30)


def test_render_one_pixel_cells():
    grid = life.empty_grid(6, 6)
    assert life.render(grid, cell_px=1, show_gridlines=False).size == (6, 6)


def test_age_color_goes_from_green_to_red():
    newborn = life.age_color(1)
    mature = life.age_color(8)
    old = life.age_color(40)
    assert newborn[1] > newborn[0], "новорождённая клетка зеленоватая"
    assert old[0] > old[1], "старая клетка красноватая"
    assert mature != newborn and mature != old


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
