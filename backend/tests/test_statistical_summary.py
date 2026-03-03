import io
import pandas as pd
import pytest

from services.statistical_summary import StatisticalSummaryService


service = StatisticalSummaryService()


def test_analyze_csv_basic():
    csv = """nom,age,ville
Alice,30,Paris
Bob,25,Lyon
Charlie,35,Marseille"""
    res = service.analyze("data.csv", csv.encode("utf-8"))

    assert res["success"] is True
    summary = res["summary"]
    assert summary["structure"]["row_count"] == 3
    assert summary["structure"]["column_count"] == 3

    cols = {c['name']: c for c in summary['columns']}
    assert 'age' in cols
    assert cols['age']['type'] == 'number'
    assert cols['age']['stats']['sum'] == 90
    assert 'nom' in cols
    assert 'top_values' in cols['nom']


def test_analyze_excel_basic():
    df = pd.DataFrame({
        'nom': ['Alice', 'Bob', 'Charlie'],
        'age': [30, 25, 35],
        'ville': ['Paris', 'Lyon', 'Marseille']
    })

    buf = io.BytesIO()
    df.to_excel(buf, index=False, engine='openpyxl')
    content = buf.getvalue()

    res = service.analyze('sheet.xlsx', content)
    assert res['success'] is True
    structure = res['summary']['structure']
    assert structure['row_count'] == 3
    assert structure['column_count'] == 3


def test_missing_values_and_low_fill_rate_alerts():
    df = pd.DataFrame({
        'id': [1, 2, 3, 4],
        'quantity': [10, None, 5, None],
        'notes': [None, None, None, 'ok']
    })

    csv = df.to_csv(index=False)
    res = service.analyze('missing.csv', csv.encode('utf-8'))

    assert res['success'] is True
    alerts = res['summary']['alerts']

    # missing_values alert for 'quantity'
    assert any(a['type'] == 'missing_values' and a['column'] == 'quantity' for a in alerts)
    # low_fill_rate alert for 'notes'
    assert any(a['type'] == 'low_fill_rate' and a['column'] == 'notes' for a in alerts)


def test_date_detection_and_date_info():
    csv = """date,value
2026-01-01,10
2026-01-03,5
2026-01-02,7"""

    res = service.analyze('dates.csv', csv.encode('utf-8'))
    assert res['success'] is True

    cols = {c['name']: c for c in res['summary']['columns']}
    assert cols['date']['type'] == 'date'
    assert 'date_info' in cols['date'] and cols['date']['date_info']['min'] == '2026-01-01'


def test_duplicates_alert():
    csv = """a,b
1,x
1,x
2,y"""
    res = service.analyze('dup.csv', csv.encode('utf-8'))
    alerts = res['summary']['alerts']

    dup = next((a for a in alerts if a['type'] == 'duplicates'), None)
    assert dup is not None
    assert dup['count'] == 1


def test_unsupported_format_returns_error():
    res = service.analyze('file.pdf', b'%PDF-1.4 fake')
    assert res['success'] is False
    assert 'Format non support' in res['error'] or 'Format non supporté' in res['error']
