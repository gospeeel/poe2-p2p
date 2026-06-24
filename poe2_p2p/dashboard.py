from __future__ import annotations

from html import escape
from pathlib import Path


def export_history_dashboard(rows: list[dict], output_path: str | Path) -> None:
    table_rows = "\n".join(
        "<tr>"
        f"<td>{escape(str(row['created_at']))}</td>"
        f"<td>{escape(str(row['path']))}</td>"
        f"<td>{float(row['net_profit']):.2f}</td>"
        f"<td>{float(row['roi_percent']):.2f}%</td>"
        f"<td>{float(row['profit_per_hour']):.2f}</td>"
        f"<td>{float(row['score']):.2f}</td>"
        f"<td>{escape(str(row['risk']))}</td>"
        "</tr>"
        for row in rows
    )
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>POE2 P2P History</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; background: #151719; color: #e8e8e8; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border-bottom: 1px solid #34383d; padding: 8px; text-align: left; }}
    th {{ background: #22262a; }}
    tr:hover {{ background: #202428; }}
  </style>
</head>
<body>
  <h1>POE2 P2P History</h1>
  <table>
    <thead>
      <tr>
        <th>Created</th>
        <th>Path</th>
        <th>Net Profit</th>
        <th>ROI</th>
        <th>Profit/h</th>
        <th>Score</th>
        <th>Risk</th>
      </tr>
    </thead>
    <tbody>
      {table_rows}
    </tbody>
  </table>
</body>
</html>
"""
    Path(output_path).write_text(html, encoding="utf-8")
