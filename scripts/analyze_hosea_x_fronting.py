#!/usr/bin/env python3
"""Analyze capital-X clause types and information-structure candidates in Hosea.

The script uses ETCBC/BHSA through Text-Fabric and produces:
- one row per capital-X clause;
- one row per pre-predicate phrase;
- a manual coding sheet for discourse-pragmatic validation;
- aggregate JSON and a Markdown report.

Important: BHSA ``typ`` and phrase ``function`` are formal morphosyntactic
annotations. Labels such as "contrastive" below are deliberately marked as
candidates; they require contextual adjudication.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from bhs_hierarchy.tf_loader import load_bhsa


CAPITAL_X_TYPES = {
    "XQtl",
    "XYqt",
    "XImp",
    "WXQt",
    "WXYq",
    "WXIm",
}

PREDICATE_FUNCTIONS = {
    "Pred",
    "PreO",
    "PreS",
    "PrcS",
    "PtcO",
}

FRAME_FUNCTIONS = {
    "Cmpl",
    "Loca",
    "Time",
    "Adju",
    "Modi",
}

NONFINITE_VERB_TYPES = {"infa", "infc", "ptca"}

PARTICIPANT_LEMMAS = {
    "יהוה": "YHWH",
    "ישראל": "Israel",
    "אפרים": "Ephraim",
    "יהודה": "Judah",
    "כהן": "Priest",
    "מלך": "King",
    "אשור": "Assyria",
    "מצרים": "Egypt",
    "יעקב": "Jacob",
    "הושע": "Hosea",
    "בעל": "Baal",
}

PARTICIPANT_LABEL_KO = {
    "YHWH": "야훼",
    "Israel": "이스라엘",
    "Ephraim": "에브라임",
    "Judah": "유다",
    "Priest": "제사장",
    "King": "왕",
    "Assyria": "앗수르",
    "Egypt": "이집트",
    "Jacob": "야곱",
    "Hosea": "호세아",
    "Baal": "바알",
    "Speaker_P1": "1인칭 화자",
    "Addressee_P2": "2인칭 청자",
    "Pronoun_P3": "3인칭 대명사",
}


def feature_value(F: Any, name: str, node: int) -> str | None:
    """Return a feature value without failing on an unavailable feature."""
    try:
        return getattr(F, name).v(node)
    except Exception:
        return None


def text_of(T: Any, node: int) -> str:
    """Return normalized original-script text for a node."""
    try:
        value = T.text(node, fmt="text-orig-full")
    except Exception:
        value = T.text(node)
    return re.sub(r"\s+", " ", value or "").strip()


def unpoint(value: str | None) -> str:
    """Remove Hebrew vocalization/cantillation and punctuation."""
    if not value:
        return ""
    decomposed = unicodedata.normalize("NFD", value)
    no_marks = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return re.sub(r"[^א-ת]", "", no_marks)


def first_slot(L: Any, node: int) -> int:
    words = L.d(node, otype="word")
    return min(words) if words else 10**12


def phrase_has_finite_verb(F: Any, L: Any, phrase: int) -> bool:
    for word in L.d(phrase, otype="word"):
        if feature_value(F, "sp", word) != "verb":
            continue
        vt = feature_value(F, "vt", word)
        if vt not in NONFINITE_VERB_TYPES:
            return True
    return False


def predicate_index(F: Any, L: Any, phrase_rows: list[dict[str, Any]]) -> tuple[int | None, str]:
    for index, phrase in enumerate(phrase_rows):
        if phrase["function"] in PREDICATE_FUNCTIONS:
            return index, "function"
    for index, phrase in enumerate(phrase_rows):
        if phrase_has_finite_verb(F, L, phrase["node"]):
            return index, "finite_verb_fallback"
    return None, "not_found"


def phrase_content_lexemes(F: Any, L: Any, phrase: int) -> set[str]:
    """Get content-bearing lexical forms for coarse continuity tests."""
    excluded_pdp = {
        "art",
        "conj",
        "prep",
        "prps",
        "prde",
        "prin",
        "inrg",
        "intj",
        "nega",
    }
    result: set[str] = set()
    for word in L.d(phrase, otype="word"):
        pdp = feature_value(F, "pdp", word)
        lex = unpoint(feature_value(F, "lex_utf8", word))
        if lex and pdp not in excluded_pdp:
            result.add(lex)
    return result


def clause_content_lexemes(F: Any, L: Any, clause: int) -> set[str]:
    result: set[str] = set()
    for phrase in L.d(clause, otype="phrase"):
        result.update(phrase_content_lexemes(F, L, phrase))
    return result


def named_participants(F: Any, words: Iterable[int]) -> set[str]:
    result: set[str] = set()
    for word in words:
        lemma = unpoint(feature_value(F, "lex_utf8", word))
        tag = PARTICIPANT_LEMMAS.get(lemma)
        if tag:
            result.add(tag)
    return result


def pronominal_participant(F: Any, words: Iterable[int]) -> str | None:
    for word in words:
        pdp = feature_value(F, "pdp", word)
        if pdp not in {"prps", "prde", "prin"}:
            continue
        person = feature_value(F, "ps", word)
        if person == "p1":
            return "Speaker_P1"
        if person == "p2":
            return "Addressee_P2"
        if person == "p3":
            return "Pronoun_P3"
    return None


def phrase_participants(F: Any, L: Any, phrase: int, function: str | None) -> set[str]:
    words = L.d(phrase, otype="word")
    result = named_participants(F, words)
    if not result and function == "Subj":
        pronoun = pronominal_participant(F, words)
        if pronoun:
            result.add(pronoun)
    return result


def phrase_form_class(F: Any, L: Any, phrase: int, function: str | None, phrase_type: str | None) -> str:
    words = L.d(phrase, otype="word")
    pdp_values = {feature_value(F, "pdp", word) for word in words}
    named = named_participants(F, words)

    if function == "Nega":
        return "negation"
    if function == "Subj":
        if "prps" in pdp_values or phrase_type == "PPrP":
            return "subject_personal_pronoun"
        if "nmpr" in pdp_values or phrase_type == "PrNP":
            return "subject_proper_name"
        if named:
            return "subject_named_entity"
        return "subject_np"
    if function == "Objc":
        return "fronted_object"
    if function in FRAME_FUNCTIONS:
        return "frame_setting"
    return "other_fronted_constituent"


def tam_family(clause_type: str | None) -> str:
    value = clause_type or ""
    if "Qt" in value or "Qtl" in value:
        return "qatal"
    if "Yq" in value or "Yqt" in value:
        return "yiqtol"
    if "Im" in value or "Imp" in value:
        return "imperative"
    return "other"


def comparison_group(clause_type: str | None) -> str:
    value = clause_type or ""
    if value in CAPITAL_X_TYPES:
        return "capital_X"
    if value.startswith("x") or value.startswith("Wx"):
        return "lowercase_x"
    if value.startswith("Z") or value in {
        "WQt0",
        "WQtX",
        "WYq0",
        "WYqX",
        "WIm0",
        "WImX",
        "Way0",
        "WayX",
    }:
        return "predicate_initial_or_W0"
    return "other"


def participant_string(values: Iterable[str]) -> str:
    return "|".join(sorted(set(values)))


def list_string(values: Iterable[Any]) -> str:
    return "|".join("" if value is None else str(value) for value in values)


def heuristic_status(
    front_function: str | None,
    front_form: str,
    current_participants: set[str],
    previous_subject_participants: set[str],
    previous_clause_participants: set[str],
    previous_two_participants: set[str],
    current_lexemes: set[str],
    previous_lexemes: set[str],
    previous_two_lexemes: set[str],
) -> tuple[str, str]:
    """Assign a transparent, non-final discourse-pragmatic candidate label."""
    if front_function == "Nega":
        return "polarity_fronting_candidate", "high"
    if front_function == "Objc":
        return "object_focus_or_topic_candidate", "medium"
    if front_function in FRAME_FUNCTIONS:
        return "frame_setting_candidate", "medium"
    if front_function != "Subj":
        return "other_fronting_candidate", "low"

    if current_participants and previous_subject_participants:
        if current_participants & previous_subject_participants:
            return "maintained_subject_candidate", "medium"
        return "responsibility_shift_candidate", "medium"

    if current_participants & previous_clause_participants:
        return "reselected_participant_candidate", "medium"
    if current_participants & previous_two_participants:
        return "reactivated_participant_candidate", "medium"
    if current_lexemes & previous_lexemes:
        return "lexically_continuous_subject_candidate", "medium"
    if current_lexemes & previous_two_lexemes:
        return "lexically_reactivated_subject_candidate", "medium"
    if front_form == "subject_personal_pronoun":
        return "deictic_or_contrastive_subject_candidate", "low"
    if current_participants:
        return "newly_overt_named_subject_candidate", "low"
    return "overt_subject_fronting_candidate", "low"


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows and not fieldnames:
        path.write_text("", encoding="utf-8")
        return
    fields = fieldnames or list(rows[0].keys())
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def counter_dict(counter: Counter[Any]) -> dict[str, int]:
    return {str(key): int(value) for key, value in counter.most_common()}


def markdown_table(counter: Counter[Any], total: int, key_header: str) -> str:
    lines = [f"| {key_header} | 빈도 | 비율 |", "|---|---:|---:|"]
    for key, value in counter.most_common():
        label = "(없음)" if key in {None, ""} else str(key)
        ratio = value / total * 100 if total else 0
        lines.append(f"| `{label}` | {value} | {ratio:.1f}% |")
    return "\n".join(lines)


def cramers_v(rows: list[dict[str, Any]], row_key: str, col_key: str) -> float | None:
    row_values = sorted({str(row.get(row_key)) for row in rows})
    col_values = sorted({str(row.get(col_key)) for row in rows})
    if len(row_values) < 2 or len(col_values) < 2:
        return None

    table = [[0 for _ in col_values] for _ in row_values]
    row_index = {value: i for i, value in enumerate(row_values)}
    col_index = {value: i for i, value in enumerate(col_values)}
    for row in rows:
        table[row_index[str(row.get(row_key))]][col_index[str(row.get(col_key))]] += 1

    row_totals = [sum(line) for line in table]
    col_totals = [sum(table[i][j] for i in range(len(row_values))) for j in range(len(col_values))]
    n = sum(row_totals)
    if n == 0:
        return None

    chi_square = 0.0
    for i in range(len(row_values)):
        for j in range(len(col_values)):
            expected = row_totals[i] * col_totals[j] / n
            if expected:
                chi_square += (table[i][j] - expected) ** 2 / expected

    denominator = n * min(len(row_values) - 1, len(col_values) - 1)
    return math.sqrt(chi_square / denominator) if denominator else None


def _group_rows(
    rows: list[dict[str, Any]],
    first_key: str,
    second_key: str,
) -> list[tuple[tuple[str, str], list[dict[str, Any]]]]:
    grouped: defaultdict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row[first_key]), str(row[second_key]))].append(row)
    return sorted(grouped.items())


def build_report(
    *,
    summary: dict[str, Any],
    x_rows: list[dict[str, Any]],
    subject_x_rows: list[dict[str, Any]],
    x_type_counts: Counter[Any],
    front_function_counts: Counter[Any],
    front_phrase_type_counts: Counter[Any],
    front_form_counts: Counter[Any],
    chapter_counts: Counter[Any],
    participant_counts: Counter[Any],
    status_counts: Counter[Any],
    subject_status_counts: Counter[Any],
) -> str:
    examples_by_status: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in x_rows:
        if len(examples_by_status[row["responsibility_relation_candidate"]]) < 3:
            examples_by_status[row["responsibility_relation_candidate"]].append(row)

    examples: list[str] = []
    for status, rows in sorted(examples_by_status.items()):
        examples.append(f"### `{status}`")
        for row in rows:
            examples.append(
                f"- **{row['ref']}** `{row['typ']}` — "
                f"전치 `{row['front_function']}`: {row['front_text']}  \n"
                f"  절: {row['text']}"
            )

    participant_ko = Counter()
    for key, value in participant_counts.items():
        participant_ko[PARTICIPANT_LABEL_KO.get(str(key), str(key))] += value

    control_lines = [
        "| 비교군·동사군 | n | 명시적 주어 | 술어 전 주어 |",
        "|---|---:|---:|---:|",
    ]
    for key, values in summary["comparison_groups"].items():
        control_lines.append(
            f"| `{key}` | {values['n']} | "
            f"{values['overt_subject_n']} ({values['overt_subject_pct']:.1f}%) | "
            f"{values['pre_predicate_subject_n']} "
            f"({values['pre_predicate_subject_pct']:.1f}%) |"
        )

    return f"""# 호세아서 대문자 X 절과 책임 주체의 정보구조

## 1. 분석 범위

- 자료: ETCBC/BHSA {summary['version']}
- 분석 단위: 호세아서 `clause`
- 전체 절: **{summary['total_clauses']}**
- 대문자 X 절: **{summary['capital_x_clauses']}**
  ({summary['capital_x_share_pct']:.1f}%)
- 대문자 X 유형: `XQtl`, `XYqt`, `WXQt`, `WXYq`, `XImp`
  및 자료에 존재할 경우 `WXIm`

`typ`와 `function`은 형식통사 주석이다. 이 보고서의
'책임 이동', '대조', '재활성화'는 자동 판정 후보이며, 담화 문맥을
읽은 수동 코딩으로 확정해야 한다.

## 2. 유형별 분포

{markdown_table(x_type_counts, len(x_rows), '절 유형')}

## 3. 술어 전 핵심 성분의 기능

각 절에서 접속사(`Conj`)를 제외하고 술어 바로 앞에 놓인 마지막
phrase를 핵심 전치 성분으로 계산했다.

{markdown_table(front_function_counts, len(x_rows), 'Phrase function')}

대문자 X 절 중 전치 주어는 **{len(subject_x_rows)}/{len(x_rows)}**
(**{summary['subject_fronting_share_pct']:.1f}%**)이다. 따라서 대문자 X를
일률적으로 '강조'라 부르기보다, 먼저 **주어 전치**, **부정 극성 전치**,
**보어·목적어 전치**를 구별해야 한다.

## 4. 전치 성분의 형식

{markdown_table(front_form_counts, len(x_rows), '형식 범주')}

### Phrase type

{markdown_table(front_phrase_type_counts, len(x_rows), 'Phrase type')}

## 5. 전치 성분에 나타난 참여자

한 phrase에 둘 이상의 명명 참여자가 있을 수 있으므로 합계는 절 수를
넘을 수 있다.

{markdown_table(participant_ko, sum(participant_ko.values()), '참여자')}

## 6. 장별 분포

{markdown_table(chapter_counts, len(x_rows), '장')}

## 7. 책임 주체 관계의 자동 후보 분류

{markdown_table(status_counts, len(x_rows), '후보 범주')}

### 전치 주어만 별도 계산

{markdown_table(subject_status_counts, len(subject_x_rows), '주어 후보 범주')}

판정 논리는 다음과 같이 제한적으로 구성했다.

1. 현재 전치 주어와 직전 절의 명시적 주어 참여자가 다르면
   `responsibility_shift_candidate`.
2. 동일하면 `maintained_subject_candidate`.
3. 직전 또는 전전 절에 참여자·내용어가 나타나면
   `reselected/reactivated` 후보.
4. 인칭대명사이지만 자동적으로 대조 집합을 확정할 수 없으면
   `deictic_or_contrastive_subject_candidate`.

직전 절의 주어가 생략된 경우가 많기 때문에 이 분류는 책임 주체의
최종 판정이 아니라 **수동 검토 순서를 정하기 위한 검색 장치**다.

## 8. 소문자 x 및 술어 선두 절과의 비교

{chr(10).join(control_lines)}

이 표는 대문자 X가 단순히 명시적 주어의 존재를 뜻하는지, 또는
특히 **술어 이전의 명시적 주어 배치**와 결합하는지를 검토하기 위한
기초 비교다.

절 유형과 전치 phrase function의 연관도(Cramér's V)는
**{summary['cramers_v_type_by_front_function']}**이다. 표본이 작은 범주가
있으므로 효과크기만 탐색적으로 사용한다.

## 9. 대표 예문

{chr(10).join(examples)}

## 10. 수동 코딩 절차

`hosea_capital_x_manual_coding.csv`에서 다음 열을 판정한다.

- `manual_information_status`: maintained / reactivated / shifted /
  contrastive / focused / frame-setting
- `manual_contrast_set`: 야훼–이스라엘, 이스라엘–열방,
  에브라임–유다, 현재–과거 등
- `manual_responsibility_bearer`: 행위·실패·심판·회복의 책임 주체
- `manual_boundary_or_speaker_shift`: 화자·청자·단락 경계와의 일치 여부
- `manual_decision`: 자동 후보 수용·수정·기각

## 11. 잠정 가설

호세아서의 대문자 X 절은 하나의 화용 기능으로 환원되지 않는다.
그러나 전치 주어가 다수를 차지한다면, 핵심 기능은 일반적인
'강조'보다 다음의 조합으로 설명하는 편이 검증 가능하다.

> 호세아의 대문자 X 구조는 담화 참여자를 명시적으로 재선택하여
> 행위와 실패의 책임 주체를 지정하거나, 야훼와 이스라엘의 상반된
> 행위를 대조하는 형식통사적 기반을 제공한다.

이 가설은 자동 추출만으로 확정되지 않는다. 특히 영 주어, 인용 화자,
평행법, 수사 질문, 절 경계를 수동으로 검토해야 한다.
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="2021")
    parser.add_argument("--out-dir", type=Path, default=Path("out/hosea-x"))
    args = parser.parse_args()

    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    api = load_bhsa(version=args.version, silent=True)
    F, T, L = api.F, api.T, api.L

    clauses = [
        clause
        for clause in F.otype.s("clause")
        if T.sectionFromNode(clause)[0] == "Hosea"
    ]

    all_rows: list[dict[str, Any]] = []
    clause_participants: dict[int, set[str]] = {}
    clause_lexemes: dict[int, set[str]] = {}
    phrase_cache: dict[int, list[dict[str, Any]]] = {}

    for sequence, clause in enumerate(clauses):
        section = T.sectionFromNode(clause)
        book, chapter, verse = section[0], section[1], section[2]
        words = list(L.d(clause, otype="word"))
        clause_participants[clause] = named_participants(F, words)
        clause_lexemes[clause] = clause_content_lexemes(F, L, clause)

        phrases = sorted(L.d(clause, otype="phrase"), key=lambda node: first_slot(L, node))
        phrase_rows: list[dict[str, Any]] = []
        for phrase in phrases:
            phrase_words = list(L.d(phrase, otype="word"))
            function = feature_value(F, "function", phrase)
            phrase_type = feature_value(F, "typ", phrase)
            phrase_rows.append(
                {
                    "node": phrase,
                    "function": function,
                    "phrase_type": phrase_type,
                    "text": text_of(T, phrase),
                    "words": phrase_words,
                    "lexemes": phrase_content_lexemes(F, L, phrase),
                    "participants": phrase_participants(F, L, phrase, function),
                }
            )
        phrase_cache[clause] = phrase_rows

        subject_participants: set[str] = set()
        for phrase in phrase_rows:
            if phrase["function"] == "Subj":
                subject_participants.update(phrase["participants"])

        pred_index, pred_detection = predicate_index(F, L, phrase_rows)
        pre_predicate = phrase_rows[:pred_index] if pred_index is not None else []
        core_pre_predicate = [phrase for phrase in pre_predicate if phrase["function"] != "Conj"]
        front = core_pre_predicate[-1] if core_pre_predicate else None

        subject_indices = [
            index for index, phrase in enumerate(phrase_rows) if phrase["function"] == "Subj"
        ]
        if subject_indices and pred_index is not None:
            subject_position = "pre_predicate" if min(subject_indices) < pred_index else "post_predicate"
        elif subject_indices:
            subject_position = "predicate_not_found"
        else:
            subject_position = "no_overt_subject"

        clause_type = feature_value(F, "typ", clause)
        all_rows.append(
            {
                "sequence": sequence,
                "node": clause,
                "book": book,
                "chapter": chapter,
                "verse": verse,
                "ref": f"Hosea {chapter}:{verse}",
                "typ": clause_type,
                "tam_family": tam_family(clause_type),
                "comparison_group": comparison_group(clause_type),
                "txt": feature_value(F, "txt", clause),
                "domain": feature_value(F, "domain", clause),
                "rela": feature_value(F, "rela", clause),
                "text": text_of(T, clause),
                "predicate_index": pred_index,
                "predicate_detection": pred_detection,
                "phrase_functions": list_string(phrase["function"] for phrase in phrase_rows),
                "phrase_types": list_string(phrase["phrase_type"] for phrase in phrase_rows),
                "pre_predicate_functions": list_string(phrase["function"] for phrase in core_pre_predicate),
                "front_phrase_node": front["node"] if front else None,
                "front_function": front["function"] if front else None,
                "front_phrase_type": front["phrase_type"] if front else None,
                "front_text": front["text"] if front else "",
                "front_lexemes": participant_string(front["lexemes"]) if front else "",
                "front_participants": participant_string(front["participants"]) if front else "",
                "front_form_class": (
                    phrase_form_class(F, L, front["node"], front["function"], front["phrase_type"])
                    if front else ""
                ),
                "all_participants": participant_string(clause_participants[clause]),
                "overt_subject_participants": participant_string(subject_participants),
                "subject_position": subject_position,
                "has_overt_subject": bool(subject_indices),
            }
        )

    for index, row in enumerate(all_rows):
        previous = all_rows[index - 1] if index >= 1 else None
        previous_two = all_rows[index - 2] if index >= 2 else None
        following = all_rows[index + 1] if index + 1 < len(all_rows) else None

        current_front_lexemes = set(filter(None, row["front_lexemes"].split("|")))
        current_front_participants = set(filter(None, row["front_participants"].split("|")))
        previous_subject_participants = (
            set(filter(None, previous["overt_subject_participants"].split("|"))) if previous else set()
        )
        previous_clause_participants = (
            set(filter(None, previous["all_participants"].split("|"))) if previous else set()
        )
        previous_two_participants = (
            set(filter(None, previous_two["all_participants"].split("|"))) if previous_two else set()
        )
        previous_lexemes = clause_lexemes[previous["node"]] if previous else set()
        previous_two_lexemes = clause_lexemes[previous_two["node"]] if previous_two else set()

        status, confidence = heuristic_status(
            row["front_function"], row["front_form_class"], current_front_participants,
            previous_subject_participants, previous_clause_participants, previous_two_participants,
            current_front_lexemes, previous_lexemes, previous_two_lexemes,
        )

        row.update(
            {
                "front_mentioned_prev1": bool(
                    current_front_participants & previous_clause_participants
                    or current_front_lexemes & previous_lexemes
                ),
                "front_mentioned_prev2": bool(
                    current_front_participants & previous_two_participants
                    or current_front_lexemes & previous_two_lexemes
                ),
                "previous_subject_participants": participant_string(previous_subject_participants),
                "previous_clause_participants": participant_string(previous_clause_participants),
                "responsibility_relation_candidate": status,
                "heuristic_confidence": confidence,
                "previous_ref": previous["ref"] if previous else "",
                "previous_text": previous["text"] if previous else "",
                "previous_two_ref": previous_two["ref"] if previous_two else "",
                "previous_two_text": previous_two["text"] if previous_two else "",
                "next_ref": following["ref"] if following else "",
                "next_text": following["text"] if following else "",
            }
        )

    x_rows = [row for row in all_rows if row["typ"] in CAPITAL_X_TYPES]

    front_phrase_rows: list[dict[str, Any]] = []
    for row in x_rows:
        phrase_rows = phrase_cache[row["node"]]
        pred_index = row["predicate_index"]
        pre_predicate = phrase_rows[:pred_index] if pred_index is not None else []
        for order, phrase in enumerate(pre_predicate):
            if phrase["function"] == "Conj":
                continue
            front_phrase_rows.append(
                {
                    "clause_node": row["node"], "ref": row["ref"], "clause_type": row["typ"],
                    "order_before_predicate": order, "phrase_node": phrase["node"],
                    "function": phrase["function"], "phrase_type": phrase["phrase_type"],
                    "text": phrase["text"], "lexemes": participant_string(phrase["lexemes"]),
                    "participants": participant_string(phrase["participants"]),
                    "form_class": phrase_form_class(
                        F, L, phrase["node"], phrase["function"], phrase["phrase_type"]
                    ),
                    "clause_text": row["text"],
                }
            )

    manual_rows = [
        {
            "ref": row["ref"], "clause_node": row["node"], "typ": row["typ"],
            "hebrew": row["text"], "front_function": row["front_function"],
            "front_phrase_type": row["front_phrase_type"], "front_text": row["front_text"],
            "front_participants": row["front_participants"], "previous_ref": row["previous_ref"],
            "previous_text": row["previous_text"], "next_ref": row["next_ref"],
            "next_text": row["next_text"],
            "automatic_candidate": row["responsibility_relation_candidate"],
            "automatic_confidence": row["heuristic_confidence"],
            "manual_information_status": "", "manual_contrast_set": "",
            "manual_responsibility_bearer": "", "manual_boundary_or_speaker_shift": "",
            "manual_decision": "", "notes": "",
        }
        for row in x_rows
    ]

    x_type_counts = Counter(row["typ"] for row in x_rows)
    front_function_counts = Counter(row["front_function"] for row in x_rows)
    front_phrase_type_counts = Counter(row["front_phrase_type"] for row in x_rows)
    front_form_counts = Counter(row["front_form_class"] for row in x_rows)
    chapter_counts = Counter(row["chapter"] for row in x_rows)
    participant_counts: Counter[str] = Counter()
    for row in x_rows:
        tags = set(filter(None, row["front_participants"].split("|")))
        if not tags:
            participant_counts["(unclassified)"] += 1
        else:
            participant_counts.update(tags)

    status_counts = Counter(row["responsibility_relation_candidate"] for row in x_rows)
    subject_x_rows = [row for row in x_rows if row["front_function"] == "Subj"]
    subject_status_counts = Counter(row["responsibility_relation_candidate"] for row in subject_x_rows)

    control_rows = [
        row for row in all_rows
        if row["comparison_group"] in {"capital_X", "lowercase_x", "predicate_initial_or_W0"}
        and row["tam_family"] in {"qatal", "yiqtol", "imperative"}
    ]
    group_summary: dict[str, dict[str, Any]] = {}
    for (group, family), grouped in _group_rows(control_rows, "comparison_group", "tam_family"):
        count = len(grouped)
        overt = sum(bool(row["has_overt_subject"]) for row in grouped)
        pre = sum(row["subject_position"] == "pre_predicate" for row in grouped)
        group_summary[f"{group}:{family}"] = {
            "n": count,
            "overt_subject_n": overt,
            "overt_subject_pct": round(overt / count * 100, 2) if count else None,
            "pre_predicate_subject_n": pre,
            "pre_predicate_subject_pct": round(pre / count * 100, 2) if count else None,
            "domain": counter_dict(Counter(row["domain"] for row in grouped)),
        }

    type_front_v = cramers_v(x_rows, "typ", "front_function")
    summary = {
        "dataset": "ETCBC/BHSA", "version": args.version, "book": "Hosea",
        "total_clauses": len(all_rows), "capital_x_clauses": len(x_rows),
        "capital_x_share_pct": round(len(x_rows) / len(all_rows) * 100, 2),
        "capital_x_type_counts": counter_dict(x_type_counts),
        "front_function_counts": counter_dict(front_function_counts),
        "front_phrase_type_counts": counter_dict(front_phrase_type_counts),
        "front_form_counts": counter_dict(front_form_counts),
        "chapter_counts": counter_dict(chapter_counts),
        "front_participant_counts": counter_dict(participant_counts),
        "heuristic_status_counts": counter_dict(status_counts),
        "subject_fronting_n": len(subject_x_rows),
        "subject_fronting_share_pct": round(len(subject_x_rows) / len(x_rows) * 100, 2) if x_rows else None,
        "subject_status_counts": counter_dict(subject_status_counts),
        "comparison_groups": group_summary,
        "cramers_v_type_by_front_function": round(type_front_v, 4) if type_front_v is not None else None,
        "caveat": "Automatic status labels are candidates only. BHSA typ/function features do not directly annotate topic, focus, contrast, or agency.",
    }

    x_fields = [
        "sequence", "node", "ref", "chapter", "verse", "typ", "tam_family", "txt",
        "domain", "rela", "text", "phrase_functions", "phrase_types",
        "pre_predicate_functions", "front_phrase_node", "front_function",
        "front_phrase_type", "front_text", "front_lexemes", "front_participants",
        "front_form_class", "front_mentioned_prev1", "front_mentioned_prev2",
        "overt_subject_participants", "previous_subject_participants",
        "previous_clause_participants", "responsibility_relation_candidate",
        "heuristic_confidence", "previous_ref", "previous_text", "previous_two_ref",
        "previous_two_text", "next_ref", "next_text", "predicate_detection",
    ]
    write_csv(out_dir / "hosea_capital_x_clauses.csv", x_rows, x_fields)
    write_csv(out_dir / "hosea_capital_x_front_phrases.csv", front_phrase_rows)
    write_csv(out_dir / "hosea_capital_x_manual_coding.csv", manual_rows)
    write_csv(
        out_dir / "hosea_clause_comparison.csv", control_rows,
        ["sequence", "node", "ref", "typ", "tam_family", "comparison_group", "domain",
         "txt", "rela", "text", "has_overt_subject", "subject_position",
         "overt_subject_participants", "front_function", "front_text"],
    )
    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "report.md").write_text(
        build_report(
            summary=summary, x_rows=x_rows, subject_x_rows=subject_x_rows,
            x_type_counts=x_type_counts, front_function_counts=front_function_counts,
            front_phrase_type_counts=front_phrase_type_counts, front_form_counts=front_form_counts,
            chapter_counts=chapter_counts, participant_counts=participant_counts,
            status_counts=status_counts, subject_status_counts=subject_status_counts,
        ), encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
