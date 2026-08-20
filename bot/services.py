"""Каталог экспертов и тарифов для записи через бота."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Tariff:
    id: str
    title: str
    price: str
    meta: str = ""


@dataclass(frozen=True)
class Expert:
    id: str
    name: str
    short: str
    telegram: str
    tariffs: tuple[Tariff, ...]


EXPERTS: dict[str, Expert] = {
    "nastya": Expert(
        id="nastya",
        name="Настя Нерадовских",
        short="Настя",
        telegram="neradana",
        tariffs=(
            Tariff("qa", "Q&A", "5 000 ₽", "1 час · онлайн"),
            Tariff("strategy", "Стратегия и план", "8 000 ₽", "1 час · онлайн"),
            Tariff("resume", "Разбор резюме", "5 000 ₽", "30 минут · онлайн"),
            Tariff("mentor_1m", "Менторство · 1 месяц", "20 000 ₽", "онлайн"),
            Tariff("mentor_2m", "Менторство · 2 месяца", "30 000 ₽", "онлайн"),
        ),
    ),
    "danya": Expert(
        id="danya",
        name="Даня Колесниченко",
        short="Даня",
        telegram="koolesoo",
        tariffs=(
            Tariff("qa", "Q&A", "2 000 ₽", "1 час · онлайн"),
            Tariff("strategy", "Стратегия и план", "3 000 ₽", "1 час · онлайн"),
            Tariff("resume", "Разбор резюме", "2 000 ₽", "30 минут · онлайн"),
            Tariff("mentor", "Менторство", "10 000 ₽ / месяц", "онлайн"),
        ),
    ),
}


def get_expert(expert_id: str) -> Expert | None:
    return EXPERTS.get(expert_id)


def get_tariff(expert_id: str, tariff_id: str) -> Tariff | None:
    expert = get_expert(expert_id)
    if not expert:
        return None
    for tariff in expert.tariffs:
        if tariff.id == tariff_id:
            return tariff
    return None
