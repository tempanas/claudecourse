#!/usr/bin/env python3
"""Classify anonymized student claims with a local Ollama model."""

from __future__ import annotations

import argparse
import csv
import json
import os
import socket
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Tuple


PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT_PATH = PROJECT_ROOT / "data" / "2026-06-student-claims-demo-data.csv"
PROMPT_PATH = PROJECT_ROOT / "prompts" / "claims-analysis-prompt.md"
OUTPUT_PATH = (
    PROJECT_ROOT / "data" / "2026-06-student-claims-demo-data-analyzed.csv"
)
OLLAMA_URL = "http://localhost:11434/api/generate"

OUTPUT_COLUMNS = ["sentiment", "claim_type", "priority", "action"]
INPUT_COLUMNS = [
    "claim_id",
    "date",
    "student_alias",
    "tariff",
    "program",
    "message",
    "has_refund_request",
    "has_contact_permission",
]
ALLOWED_VALUES = {
    "sentiment": {"positive", "neutral", "negative"},
    "claim_type": {
        "жалоба",
        "возврат",
        "консультация",
        "техническая проблема",
        "вопрос по курсу",
        "смешанное обращение",
    },
    "priority": {"low", "medium", "high"},
    "action": {
        "ответить",
        "передать в претензионный сектор",
        "проверить возврат",
        "назначить консультацию",
        "уточнить данные",
        "проверить техническую проблему",
    },
}
CLAIM_TYPE_NORMALIZATION = {
    "technical problem": "техническая проблема",
    "tech problem": "техническая проблема",
    "refund": "возврат",
    "complaint": "жалоба",
    "consultation": "консультация",
    "course question": "вопрос по курсу",
    "mixed": "смешанное обращение",
    "mixed request": "смешанное обращение",
}
ACTION_NORMALIZATION = {
    "check technical problem": "проверить техническую проблему",
    "check refund": "проверить возврат",
    "assign consultation": "назначить консультацию",
    "reply": "ответить",
    "escalate claim": "передать в претензионный сектор",
    "clarify data": "уточнить данные",
}
FALLBACK_CLASSIFICATION = {
    "sentiment": "neutral",
    "claim_type": "вопрос по курсу",
    "priority": "medium",
    "action": "уточнить данные",
}


class OllamaError(RuntimeError):
    """Raised when the local Ollama request cannot be completed."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Анализ обезличенных претензий студентов через локальную Ollama."
    )
    parser.add_argument(
        "--model",
        required=True,
        help="Имя локальной модели Ollama, например llama3.2:3b.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Обработать только первые N строк, например --limit 5.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=120.0,
        help="Таймаут одного запроса к Ollama в секундах (по умолчанию: 120).",
    )
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit должен быть положительным целым числом")
    if args.timeout <= 0:
        parser.error("--timeout должен быть положительным числом")
    return args


def build_claim_prompt(base_prompt: str, row: Dict[str, str]) -> str:
    fields = [
        f"claim_id: {row['claim_id']}",
        f"date: {row['date']}",
        f"student_alias: {row['student_alias']}",
        f"tariff: {row['tariff']}",
        f"program: {row['program']}",
        f"message: {row['message']}",
        f"has_refund_request: {row['has_refund_request']}",
        f"has_contact_permission: {row['has_contact_permission']}",
    ]
    return f"{base_prompt.rstrip()}\n\n## Обращение для анализа\n\n" + "\n".join(fields)


def request_ollama(model: str, prompt: str, timeout: float) -> str:
    payload = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0},
        },
        ensure_ascii=False,
    ).encode("utf-8")
    request = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
        },
        method="POST",
    )
    # Do not inherit macOS/system proxy settings: this request must stay local.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    try:
        with opener.open(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        if exc.code == 404:
            raise OllamaError(
                f"Модель '{model}' не найдена в Ollama. "
                f"Проверьте имя модели и выполните: ollama pull {model}"
            ) from exc
        raise OllamaError(
            f"Ollama вернула HTTP {exc.code}: {details.strip()}"
        ) from exc
    except (TimeoutError, socket.timeout) as exc:
        raise OllamaError(
            f"Ollama не ответила за {timeout:g} секунд. "
            "Проверьте загрузку компьютера или увеличьте --timeout."
        ) from exc
    except (urllib.error.URLError, ConnectionError, OSError) as exc:
        reason = getattr(exc, "reason", exc)
        raise OllamaError(
            "Не удалось подключиться к Ollama по адресу "
            f"{OLLAMA_URL}. Проверьте, что Ollama установлена и запущена "
            "(команда: ollama serve), а модель скачана "
            f"(команда: ollama pull {model}). Причина: {reason}"
        ) from exc

    try:
        result = json.loads(body)
        if result.get("error"):
            raise OllamaError(f"Ollama сообщила об ошибке: {result['error']}")
        response_text = result.get("response")
        if not isinstance(response_text, str) or not response_text.strip():
            raise OllamaError("Ollama вернула пустой ответ.")
        return response_text.strip()
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise OllamaError(
            "Ollama вернула ответ в неожиданном формате."
        ) from exc


def normalize_value(value: str) -> str:
    normalized = value.strip().lower()
    quote_pairs = {
        '"': '"',
        "'": "'",
        "«": "»",
        "“": "”",
        "„": "“",
    }
    while len(normalized) >= 2:
        closing_quote = quote_pairs.get(normalized[0])
        if closing_quote is None or normalized[-1] != closing_quote:
            break
        normalized = normalized[1:-1].strip()
    return " ".join(normalized.split())


def normalize_classification(values: List[str]) -> Dict[str, str]:
    parsed = dict(
        zip(OUTPUT_COLUMNS, [normalize_value(value) for value in values])
    )
    parsed["claim_type"] = CLAIM_TYPE_NORMALIZATION.get(
        parsed["claim_type"],
        parsed["claim_type"],
    )
    parsed["action"] = ACTION_NORMALIZATION.get(
        parsed["action"],
        parsed["action"],
    )
    return parsed


def parse_csv_values(line: str) -> List[str]:
    try:
        values = next(csv.reader([line], skipinitialspace=True))
    except csv.Error as exc:
        raise ValueError(f"некорректная CSV-строка: {line!r}") from exc

    # Some models wrap the entire CSV row in one extra pair of quotes.
    if len(values) == 1:
        unquoted_line = normalize_value(line)
        if unquoted_line != line.strip().lower():
            try:
                values = next(
                    csv.reader([unquoted_line], skipinitialspace=True)
                )
            except csv.Error as exc:
                raise ValueError(
                    f"некорректная CSV-строка: {line!r}"
                ) from exc
    return values


def parse_model_response(response: str) -> Dict[str, str]:
    candidates = []
    for raw_line in response.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("```"):
            continue
        try:
            values = parse_csv_values(line)
        except ValueError:
            continue
        if len(values) != len(OUTPUT_COLUMNS):
            continue

        parsed = normalize_classification(values)
        if list(parsed.values()) == OUTPUT_COLUMNS:
            continue
        if all(
            value in ALLOWED_VALUES[column]
            for column, value in parsed.items()
        ):
            candidates.append(parsed)

    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) > 1 and all(item == candidates[0] for item in candidates):
        return candidates[0]

    allowed_description = "; ".join(
        f"{column}: {', '.join(sorted(values))}"
        for column, values in ALLOWED_VALUES.items()
    )
    raise ValueError(
        "не удалось найти одну корректную CSV-строку с четырьмя значениями. "
        f"Ответ модели: {response!r}. Допустимые значения: "
        f"{allowed_description}"
    )


def load_rows() -> Tuple[List[str], List[Dict[str, str]]]:
    try:
        with INPUT_PATH.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            if reader.fieldnames is None:
                raise ValueError("во входном CSV отсутствует строка заголовков")
            missing_columns = [
                column for column in INPUT_COLUMNS
                if column not in reader.fieldnames
            ]
            if missing_columns:
                raise ValueError(
                    "во входном CSV отсутствуют обязательные колонки: "
                    + ", ".join(missing_columns)
                )
            rows = list(reader)
            return list(reader.fieldnames), rows
    except FileNotFoundError as exc:
        raise RuntimeError(f"Не найден входной файл: {INPUT_PATH}") from exc


def write_rows(
    fieldnames: List[str],
    rows: List[Dict[str, str]],
) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Optional[Path] = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            newline="",
            dir=OUTPUT_PATH.parent,
            prefix=f".{OUTPUT_PATH.name}.",
            suffix=".tmp",
            delete=False,
        ) as file:
            temp_path = Path(file.name)
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        os.replace(temp_path, OUTPUT_PATH)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def main() -> int:
    args = parse_args()

    try:
        base_prompt = PROMPT_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"Ошибка: не найден файл промпта: {PROMPT_PATH}", file=sys.stderr)
        return 1

    try:
        input_fieldnames, rows = load_rows()
    except (RuntimeError, ValueError) as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 1

    selected_rows = rows[: args.limit] if args.limit is not None else rows
    analyzed_rows: List[Dict[str, str]] = []

    for index, row in enumerate(selected_rows, start=1):
        claim_id = row.get("claim_id", f"строка {index}")
        print(
            f"[{index}/{len(selected_rows)}] Анализ {claim_id}...",
            file=sys.stderr,
        )
        prompt = build_claim_prompt(base_prompt, row)
        try:
            response = request_ollama(args.model, prompt, args.timeout)
            classification = parse_model_response(response)
        except OllamaError as exc:
            print(f"Ошибка при обработке {claim_id}: {exc}", file=sys.stderr)
            print(
                "Результирующий файл не был перезаписан. "
                "Проверьте Ollama и доступность модели.",
                file=sys.stderr,
            )
            return 1
        except ValueError as exc:
            classification = dict(FALLBACK_CLASSIFICATION)
            print(
                f"Предупреждение для {claim_id}: {exc}",
                file=sys.stderr,
            )
            print(
                "Использованы fallback-значения: "
                "neutral,вопрос по курсу,medium,уточнить данные. "
                "Обработка продолжается.",
                file=sys.stderr,
            )

        analyzed_row = dict(row)
        analyzed_row.update(classification)
        analyzed_rows.append(analyzed_row)

    output_fieldnames = input_fieldnames + [
        column for column in OUTPUT_COLUMNS if column not in input_fieldnames
    ]
    write_rows(output_fieldnames, analyzed_rows)
    print(
        f"Готово: обработано строк — {len(analyzed_rows)}. "
        f"Результат: {OUTPUT_PATH}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
