"""
filter universities based on minimum requirements.
Args: budget (range cost of attendance, tuition), concentration, degree (undergraduate, graduate, associate), grades (ACT, SAT), region
Output: Top 20 universities that satisfy the requirements
"""

import pandas as pd

from ..utils import load_local_data

DATA_PATH = "./data_source/us_uni_data_filtered.csv"


def filter_uni(
    budget_range: tuple[int, int],
    score_type: str | None,
    score: int | None,
    region: list[str] | None,
    data: pd.DataFrame,
) -> pd.DataFrame:

    # filter by budget
    min_budget, max_budget = budget_range
    df_budget = data[
        (data["latest.cost.attendance.academic_year"] >= min_budget)
        & (data["latest.cost.attendance.academic_year"] <= max_budget)
    ]

    # filter by score
    score_col = None
    df_score = df_budget

    if score_type == "ACT":
        score_col = "latest.admissions.act_scores.midpoint.cumulative"
    elif score_type == "SAT":
        score_col = "latest.admissions.sat_scores.average.overall"

    if score:
        df_score = df_budget[df_budget[score_col] <= score]

    # filter by region
    # TODO: add region column in dataset
    # northeast, midatlantic, midwest, west, southeast, southwest, northwest
    df_region = df_score

    # if region:
    #     df_region = df_region[df_region["region"].isin(region)]

    final_df = df_region
    return final_df


def layer1(
    budget_range: tuple[int, int],
    score_type: str | None = None,
    score: int | None = None,
    region: str | None = None,
) -> pd.DataFrame:
    df = load_local_data(DATA_PATH)
    df_filtered = filter_uni(budget_range, score_type, score, region, df)
    return df_filtered
