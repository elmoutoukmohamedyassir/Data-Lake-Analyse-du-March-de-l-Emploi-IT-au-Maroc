"""
dags/mexora_pipeline_dag.py
============================
Orchestre le pipeline Bronze → Silver → Gold avec Airflow.
Chaque étape est une tâche séparée : si Silver échoue, Gold ne se lance pas
(dépendances explicites), et Airflow retente automatiquement en cas d'échec.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

default_args = {
    "owner": "mexora",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


def _run_bronze():
    from main import run_bronze
    run_bronze()


def _run_silver():
    from main import run_silver
    run_silver()


def _run_data_quality():
    from main import run_data_quality
    run_data_quality()


def _run_gold():
    from main import run_gold
    run_gold()


with DAG(
    dag_id="mexora_rh_pipeline",
    default_args=default_args,
    description="Pipeline Bronze -> Silver -> Gold pour le data lake Mexora RH",
    schedule="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["mexora", "data-lake"],
) as dag:

    bronze = PythonOperator(task_id="bronze_ingestion", python_callable=_run_bronze)
    silver = PythonOperator(task_id="silver_transform", python_callable=_run_silver)
    data_quality = PythonOperator(task_id="data_quality_check", python_callable=_run_data_quality)
    gold = PythonOperator(task_id="gold_aggregation", python_callable=_run_gold)

    # Si data_quality_check échoue (règle GE non respectée), Airflow
    # n'exécute PAS gold_aggregation — c'est la porte de qualité en action.
    bronze >> silver >> data_quality >> gold