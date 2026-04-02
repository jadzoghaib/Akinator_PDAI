import pandas as pd

CSV_FILE_PATH = "survey_responses.tsv"
NAME_COL = "0. Please write your name and surname"

# Binary questions ordered by expected information gain (most discriminating first).
# yes_value is the answer that counts as "Yes" for filtering.
QUESTIONS = [
    {"column": "5. When are you more productive?",              "text": "Are they a night owl?",                           "yes_value": "Night owl"},
    {"column": "14. Where do you sit in class?",               "text": "Do they sit in the front rows?",                  "yes_value": "Front rows"},
    {"column": "1. Do you have siblings",                      "text": "Do they have siblings?",                          "yes_value": "Yes"},
    {"column": "2. Do you have any pets?",                     "text": "Do they have any pets?",                          "yes_value": "Yes"},
    {"column": "6. Do you have any tattoos?",                  "text": "Do they have any tattoos?",                       "yes_value": "Yes"},
    {"column": "8. What team are you?",                        "text": "Are they team Coffee (not Tea)?",                 "yes_value": "Coffee"},
    {"column": "3. Marital status",                            "text": "Are they single?",                                "yes_value": "Single"},
    {"column": "9. Do you like spicy food?",                   "text": "Do they like spicy food?",                        "yes_value": "Yes"},
    {"column": "11. Do you have a technical background?",      "text": "Do they have a technical background?",            "yes_value": "Yes"},
    {"column": "12. Do you use glasses in class?",             "text": "Do they use glasses in class?",                   "yes_value": "Yes"},
    {"column": "4. Do you play any instruments",               "text": "Do they play any instruments?",                  "yes_value": "Yes"},
    {"column": "13. Do you procrastinate homework/studying?",  "text": "Do they procrastinate?",                         "yes_value": "Yes"},
    {"column": "10. When do you normally get to class?",       "text": "Do they usually arrive before 9?",               "yes_value": "Before 9"},
    {"column": "15. What is your drink of choice at Erika (ERREKA)?", "text": "Is their drink of choice at Erika Beer?", "yes_value": "Beer"},
    {"column": "7. Are you right-handed?",                     "text": "Are they right-handed?",                         "yes_value": "Yes"},
]


def load_all_candidates() -> dict:
    """Returns {name: {column: value, ...}} for every survey respondent."""
    df = pd.read_csv(CSV_FILE_PATH, sep="\t")
    data = {}
    for _, row in df.iterrows():
        name = str(row.get(NAME_COL, "")).strip()
        if name:
            data[name] = {col: str(row.get(col, "")).strip() for col in df.columns}
    return data


def best_next_question(candidates_data: dict, asked_columns: list) -> dict | None:
    """Return the question that splits the remaining candidates most evenly."""
    total = len(candidates_data)
    if total == 0:
        return None

    best_q = None
    best_diff = total + 1  # lower is better (closer to 50/50)

    for q in QUESTIONS:
        if q["column"] in asked_columns:
            continue

        yes_count = sum(
            1 for data in candidates_data.values()
            if data.get(q["column"], "").strip() == q["yes_value"]
        )
        no_count = total - yes_count

        # Skip questions where everyone answers the same way
        if yes_count == 0 or no_count == 0:
            continue

        diff = abs(yes_count - no_count)
        if diff < best_diff:
            best_diff = diff
            best_q = q

    return best_q


def filter_candidates(candidates_data: dict, column: str, yes_value: str, answer: str) -> dict:
    """
    Filter candidates based on the user's answer.
    answer: "yes" | "no" | "maybe"
    """
    if answer == "maybe":
        return candidates_data

    result = {}
    for name, data in candidates_data.items():
        matches = data.get(column, "").strip() == yes_value
        if answer == "yes" and matches:
            result[name] = data
        elif answer == "no" and not matches:
            result[name] = data
    return result
