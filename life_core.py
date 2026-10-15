"""Ядро игры «Жизнь» Конвея (только numpy + Pillow, без Streamlit).

Здесь нет ничего, что зависело бы от Streamlit, поэтому логику можно
тестировать и переиспользовать отдельно от интерфейса.
"""

from __future__ import annotations

import numpy as np

# --------------------------------------------------------------------------
# Правило
# --------------------------------------------------------------------------


def parse_rule(rule: str) -> tuple[np.ndarray, np.ndarray]:
    """Разбирает правило в нотации B/S, например "B3/S23" -> (birth, survive).

    birth[i] / survive[i] — булевы массивы длины 9: рождается ли клетка
    и выживает ли она при i живых соседях.
    """
    text = rule.upper().replace(" ", "")
    if "/" not in text:
        raise ValueError('Правило должно быть в формате "B3/S23".')
    left, right = text.split("/", 1)
    left = left.lstrip("B")
    right = right.lstrip("S")
    if not left.isdigit() and left != "":
        raise ValueError('После "B" должны идти цифры, например B3.')
    if not right.isdigit() and right != "":
        raise ValueError('После "S" должны идти цифры, например S23.')

    birth = np.zeros(9, dtype=bool)
    survive = np.zeros(9, dtype=bool)
    for ch in left:
        birth[int(ch)] = True
    for ch in right:
        survive[int(ch)] = True
    return birth, survive


def rule_to_text(birth: np.ndarray, survive: np.ndarray) -> str:
    b = "".join(str(i) for i in range(9) if birth[i])
    s = "".join(str(i) for i in range(9) if survive[i])
    return f"B{b}/S{s}"


# --------------------------------------------------------------------------
# Поле и шаг эволюции
# --------------------------------------------------------------------------


def empty_grid(rows: int, cols: int) -> np.ndarray:
    """Пустое поле. 0 — мёртвая клетка, >0 — возраст живой клетки."""
    return np.zeros((rows, cols), dtype=np.uint8)


def neighbor_count(alive: np.ndarray, wrap: bool = True) -> np.ndarray:
    """Число живых соседей у каждой клетки (8 направлений)."""
    if wrap:
        total = np.zeros(alive.shape, dtype=np.uint8)
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                if di == 0 and dj == 0:
                    continue
                total += np.roll(np.roll(alive, di, axis=0), dj, axis=1)
        return total

    padded = np.pad(alive, 1, mode="constant", constant_values=False)
    total = np.zeros(alive.shape, dtype=np.uint16)
    for di in (0, 1, 2):
        for dj in (0, 1, 2):
            if di == 1 and dj == 1:
                continue
            total += padded[di : di + alive.shape[0], dj : dj + alive.shape[1]]
    return total.astype(np.uint8)


def step(
    grid: np.ndarray,
    birth: np.ndarray,
    survive: np.ndarray,
    wrap: bool = True,
) -> np.ndarray:
    """Один шаг игры. Возвращает новую сетку с обновлённым возрастом клеток."""
    alive = grid > 0
    n = neighbor_count(alive, wrap=wrap)
    new_alive = np.where(alive, survive[n], birth[n])

    age = grid.astype(np.uint16)
    new_age = np.where(new_alive, np.where(alive, age + 1, 1), 0)
    return np.clip(new_age, 0, 255).astype(np.uint8)


def population(grid: np.ndarray) -> int:
    return int(np.count_nonzero(grid))


# --------------------------------------------------------------------------
# Шаблоны (фигуры)
# --------------------------------------------------------------------------


def from_text(text: str) -> np.ndarray:
    """Строит фигуру из ASCII-картинки: '.'/' ' — пусто, любой иной символ — жизнь.

    Пустые строки внутри картинки сохраняются (они значат пустой ряд клеток),
    а пустые строки по краям отбрасываются.
    """
    lines = text.strip("\n").splitlines()
    if not lines or not any(ch not in ". " for line in lines for ch in line):
        raise ValueError("Пустой шаблон: нет ни одной живой клетки.")
    width = max(len(line) for line in lines)
    out = np.zeros((len(lines), width), dtype=np.uint8)
    for i, line in enumerate(lines):
        for j, ch in enumerate(line):
            if ch not in ". ":
                out[i, j] = 1
    return out


PATTERNS: dict[str, str] = {
    "Блок (Still life)": """
OO
OO
""",
    "Мигалка (Blinker)": """
OOO
""",
    "Жаба (Toad)": """
.OOO
OOO.
""",
    "Планер (Glider)": """
.O.
..O
OOO
""",
    "Лёгкий корабль (LWSS)": """
.O..O
O....
O...O
OOOO.
""",
    "Пульсар (Pulsar)": """
..OOO...OOO..
.............
O....O.O....O
O....O.O....O
O....O.O....O
..OOO...OOO..
.............
..OOO...OOO..
O....O.O....O
O....O.O....O
O....O.O....O
.............
..OOO...OOO..
""",
    "Пушка Госпера (Gosper gun)": """
........................O...........
......................O.O...........
............OO......OO............OO
...........O...O....OO............OO
OO........O.....O...OO..............
OO........O...O.OO....O.O...........
..........O.....O.......O...........
...........O...O....................
............OO......................
""",
    "R-пентамино (хаос)": """
.OO
OO.
.O.
""",
    "Жёлудь (Acorn)": """
.O.....
...O...
OO..OOO
""",
}


def pattern(name: str) -> np.ndarray:
    if name not in PATTERNS:
        raise KeyError(f"Неизвестная фигура: {name}")
    return from_text(PATTERNS[name])


def place(
    grid: np.ndarray,
    pat: np.ndarray,
    top: int,
    left: int,
    wrap: bool = False,
) -> np.ndarray:
    """Помещает фигуру на поле (in-place) с обрезкой по краям либо с заворотом."""
    rows, cols = grid.shape
    pr, pc = pat.shape
    for i in range(pr):
        for j in range(pc):
            if pat[i, j] == 0:
                continue
            r, c = top + i, left + j
            if wrap:
                grid[r % rows, c % cols] = 1
            elif 0 <= r < rows and 0 <= c < cols:
                grid[r, c] = 1
    return grid


def random_grid(
    rows: int, cols: int, density: float = 0.25, rng: np.random.Generator | None = None
) -> np.ndarray:
    rng = rng or np.random.default_rng()
    return (rng.random((rows, cols)) < density).astype(np.uint8)


# --------------------------------------------------------------------------
# Отрисовка (Pillow)
# --------------------------------------------------------------------------

BACKGROUND = (13, 17, 23)
GRIDLINE = (30, 38, 48)
NEWBORN = np.array([80, 220, 140], dtype=np.float32)   # только что родилась
MATURE = np.array([255, 214, 102], dtype=np.float32)   # живёт давно
OLD = np.array([255, 120, 90], dtype=np.float32)       # совсем старая


def age_color(age: int) -> tuple[int, int, int]:
    """Цвет клетки по её возрасту: зелёный -> жёлтый -> красный."""
    if age <= 1:
        return tuple(NEWBORN.astype(int))
    if age <= 8:
        t = (age - 1) / 7.0
        rgb = NEWBORN * (1 - t) + MATURE * t
    else:
        t = min((age - 8) / 24.0, 1.0)
        rgb = MATURE * (1 - t) + OLD * t
    return tuple(rgb.astype(int))


def render(
    grid: np.ndarray,
    cell_px: int = 8,
    show_gridlines: bool = True,
):
    """Возвращает PIL.Image с полем. Требует Pillow."""
    from PIL import Image

    rows, cols = grid.shape
    cell_px = max(1, int(cell_px))

    rgb = np.empty((rows, cols, 3), dtype=np.uint8)
    rgb[:, :] = BACKGROUND
    for age in np.unique(grid[grid > 0]):
        rgb[grid == age] = age_color(int(age))

    img = np.repeat(np.repeat(rgb, cell_px, axis=0), cell_px, axis=1)

    if show_gridlines and cell_px >= 6:
        img[::cell_px, :, :] = GRIDLINE
        img[:, ::cell_px, :] = GRIDLINE

    return Image.fromarray(img, mode="RGB")
