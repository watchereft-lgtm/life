"""Проверка приложения в НАСТОЯЩЕМ Streamlit (в отличие от test_streamlit_ui.py).

Использует штатный Streamlit AppTest: приложение запускается по-настоящему,
проверяются отрисовка, состояние сессии и реакция на нажатия кнопок.

Требуется установленный Streamlit:  pip install -r requirements.txt
Запуск:                             python test_app_streamlit.py

В обязательные проверки CI (.github/workflows/checks.yml) этот файл вынесен
отдельной необязательной задачей: он требует Streamlit, а его поведение
зависит от версии библиотеки.
"""

from __future__ import annotations

from pathlib import Path

APP = Path(__file__).with_name("game_of_life.py")


def _app_test():
    """Возвращает запущенный AppTest или None, если Streamlit не установлен."""
    try:
        from streamlit.testing.v1 import AppTest
    except ImportError:
        return None
    at = AppTest.from_file(str(APP), default_timeout=60)
    at.run()
    return at


def _click(at, label: str):
    for button in at.button:
        if getattr(button, "label", None) == label:
            button.click().run()
            return at
    labels = [getattr(b, "label", None) for b in at.button]
    raise AssertionError(f"кнопка {label!r} не найдена, на странице: {labels}")


def _errors(at) -> list:
    return [str(element.value) for element in at.exception]


# --------------------------------------------------------------------------
# Проверки
# --------------------------------------------------------------------------


def test_app_starts_without_exceptions():
    at = _app_test()
    if at is None:
        print("SKIP  Streamlit не установлен")
        return
    assert not at.exception, _errors(at)


def test_default_board_state():
    at = _app_test()
    if at is None:
        print("SKIP  Streamlit не установлен")
        return
    assert at.session_state["grid"].shape == (45, 70)
    assert at.session_state["generation"] == 0
    assert at.session_state["running"] is False


def test_step_button_advances_generation():
    at = _app_test()
    if at is None:
        print("SKIP  Streamlit не установлен")
        return
    _click(at, "⏭ Шаг")
    assert not at.exception, _errors(at)
    assert at.session_state["generation"] == 1


def test_randomize_button_fills_board():
    at = _app_test()
    if at is None:
        print("SKIP  Streamlit не установлен")
        return
    import numpy as np

    _click(at, "🎲 Случайно")
    assert not at.exception, _errors(at)
    assert np.count_nonzero(at.session_state["grid"]) > 0
    assert at.session_state["generation"] == 0


def test_clear_button_empties_board():
    at = _app_test()
    if at is None:
        print("SKIP  Streamlit не установлен")
        return
    import numpy as np

    _click(at, "🎲 Случайно")
    _click(at, "🧹 Очистить")
    assert not at.exception, _errors(at)
    assert np.count_nonzero(at.session_state["grid"]) == 0


def test_sidebar_is_present():
    at = _app_test()
    if at is None:
        print("SKIP  Streamlit не установлен")
        return
    assert len(at.sidebar.button) >= 6, "в панели должны быть кнопки управления"


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
