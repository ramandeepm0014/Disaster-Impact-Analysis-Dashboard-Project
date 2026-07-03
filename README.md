# Disaster Impact Analysis Website

A professional Python Flask dashboard built from the uploaded disaster impact Excel dataset.

## Features

- KPI dashboard for deaths, injured, affected population, economic damage, relief funds, recovery days, and coverage percentage
- Filters for country, city, disaster type, severity, and year range
- Interactive charts using Chart.js
- Disaster location map using Leaflet
- Filtered dataset table
- Responsive professional dark UI

## How to Run

1. Open this folder in VS Code.
2. Open terminal in this folder.
3. Create virtual environment:

```bash
python -m venv venv
```

4. Activate virtual environment:

Windows PowerShell:

```bash
venv\Scripts\activate
```

5. Install packages:

```bash
pip install -r requirements.txt
```

6. Run the website:

```bash
python app.py
```

7. Open in browser:

```text
http://127.0.0.1:5000
```

## Dataset

The Excel file is stored at:

```text
data/disaster_data.xlsx
```
