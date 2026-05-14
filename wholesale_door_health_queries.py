from __future__ import annotations

import os

import pandas as pd
from google.cloud import bigquery

_PROJECT = "product-analytics-389809"
_TABLE = f"`{_PROJECT}.wholesale_dashboard_src.main`"

_BASE_FILTER = """
    company_location_id IS NOT NULL
    AND financial_status != 'pending'
"""


def get_client() -> bigquery.Client:
    import streamlit as st
    from google.oauth2 import service_account

    if "gcp_service_account" in st.secrets:
        creds = service_account.Credentials.from_service_account_info(
            dict(st.secrets["gcp_service_account"]),
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        return bigquery.Client(project=_PROJECT, credentials=creds)

    key = "product-analytics-389809-47c798f65a92.json"
    if os.path.exists(key):
        os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", key)
    return bigquery.Client(project=_PROJECT)


def door_health_summary(client: bigquery.Client, as_of: str) -> dict[str, int]:
    q = f"""
    WITH latest AS (
      SELECT
        company_location_id,
        MAX(DATE(created_at_et)) AS last_order_date
      FROM {_TABLE}
      WHERE {_BASE_FILTER}
        AND DATE(created_at_et) <= '{as_of}'
      GROUP BY 1
    )
    SELECT
      CASE
        WHEN DATE_DIFF(DATE '{as_of}', last_order_date, DAY) <= 30 THEN 'Active'
        WHEN DATE_DIFF(DATE '{as_of}', last_order_date, DAY) <= 60 THEN 'At Risk'
        WHEN DATE_DIFF(DATE '{as_of}', last_order_date, DAY) <= 90 THEN 'Churned'
        ELSE 'Lost'
      END AS status,
      COUNT(*) AS doors
    FROM latest
    GROUP BY 1
    """
    rows = client.query(q).result()
    return {r["status"]: r["doors"] for r in rows}


def monthly_trend(client: bigquery.Client) -> pd.DataFrame:
    q = f"""
    WITH monthly AS (
      SELECT
        DATE_TRUNC(DATE(created_at_et), MONTH) AS month_date,
        FORMAT_DATE('%b %Y', DATE_TRUNC(DATE(created_at_et), MONTH)) AS month_label,
        COUNT(DISTINCT company_location_id) AS active_doors,
        COUNT(DISTINCT IF(
          DATE_TRUNC(DATE(DATETIME(door_first_order_created_at, 'America/New_York')), MONTH) = DATE_TRUNC(DATE(created_at_et), MONTH),
          company_location_id, NULL
        )) AS new_doors
      FROM {_TABLE}
      WHERE {_BASE_FILTER}
        AND created_at_et >= DATE_TRUNC(
              DATE_SUB(CURRENT_DATE('America/New_York'), INTERVAL 5 MONTH), MONTH)
      GROUP BY 1, 2
    )
    SELECT
      month_date,
      month_label,
      active_doors,
      new_doors,
      active_doors - LAG(active_doors) OVER (ORDER BY month_date) AS net_change
    FROM monthly
    ORDER BY month_date
    """
    return client.query(q).to_dataframe()


def weekly_trend(client: bigquery.Client) -> pd.DataFrame:
    q = f"""
    WITH weekly AS (
      SELECT
        DATE_TRUNC(DATE(created_at_et), WEEK(MONDAY)) AS week_date,
        FORMAT_DATE('%b %d', DATE_TRUNC(DATE(created_at_et), WEEK(MONDAY))) AS week_label,
        COUNT(DISTINCT company_location_id) AS active_doors,
        COUNT(DISTINCT IF(
          DATE_TRUNC(DATE(DATETIME(door_first_order_created_at, 'America/New_York')), WEEK(MONDAY)) = DATE_TRUNC(DATE(created_at_et), WEEK(MONDAY)),
          company_location_id, NULL
        )) AS new_doors
      FROM {_TABLE}
      WHERE {_BASE_FILTER}
        AND created_at_et >= DATE_TRUNC(
              DATE_SUB(CURRENT_DATE('America/New_York'), INTERVAL 8 WEEK), WEEK(MONDAY))
      GROUP BY 1, 2
    )
    SELECT
      week_date,
      week_label,
      active_doors,
      new_doors,
      active_doors - LAG(active_doors) OVER (ORDER BY week_date) AS net_change
    FROM weekly
    ORDER BY week_date
    """
    return client.query(q).to_dataframe()


def door_detail(client: bigquery.Client, as_of: str) -> pd.DataFrame:
    q = f"""
    WITH door_latest AS (
      SELECT
        company_location_id,
        MAX(company_name)               AS company,
        MAX(location_name)              AS door_name,
        MAX(location_address_city)      AS city,
        MAX(location_address_province)  AS state,
        MAX(imputed_owner_name)         AS rep,
        MAX(DATE(created_at_et))        AS last_order_date,
        DATE_DIFF(DATE '{as_of}', MAX(DATE(created_at_et)), DAY) AS days_since_order
      FROM {_TABLE}
      WHERE {_BASE_FILTER}
        AND DATE(created_at_et) <= '{as_of}'
      GROUP BY company_location_id
    ),
    door_spend AS (
      SELECT
        company_location_id,
        ROUND(SUM(IF(DATE(created_at_et) BETWEEN DATE_SUB(DATE '{as_of}', INTERVAL 90 DAY) AND DATE '{as_of}', line_net_total, 0)), 2) AS spend_30d,
        ROUND(SUM(IF(DATE(created_at_et) <= DATE '{as_of}', line_net_total, 0)), 2) AS spend_total
      FROM {_TABLE}
      WHERE {_BASE_FILTER}
      GROUP BY 1
    )
    SELECT
      d.company,
      d.door_name,
      d.city,
      d.state,
      d.rep,
      d.last_order_date,
      d.days_since_order,
      COALESCE(s.spend_30d, 0)    AS spend_30d,
      COALESCE(s.spend_total, 0)  AS spend_total,
      CASE
        WHEN d.days_since_order <= 30 THEN 'Active'
        WHEN d.days_since_order <= 60 THEN 'At Risk'
        WHEN d.days_since_order <= 90 THEN 'Churned'
        ELSE 'Lost'
      END AS status
    FROM door_latest d
    LEFT JOIN door_spend s USING (company_location_id)
    ORDER BY d.days_since_order
    """
    return client.query(q).to_dataframe()
