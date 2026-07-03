from flask import Flask, render_template, jsonify, request
import pandas as pd
import os

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "disaster_data.xlsx")


def load_data():
    """Load and clean the disaster dataset."""
    if not os.path.exists(DATA_FILE):
        raise FileNotFoundError(f"Dataset not found at: {DATA_FILE}")

    df = pd.read_excel(DATA_FILE)

    # Standardize dates and numeric columns
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df["Date_Display"] = df["Date"].dt.strftime("%d %b %Y")

    numeric_columns = [
        "Year", "Latitude", "Longitude", "Magnitude", "Deaths", "Injured",
        "Affected_Population", "Economic_Damage_USD", "Recovery_Days",
        "Relief_Funds_USD", "Deaths_and_Injured", "Economic_Damage_USD_Millions",
        "Relief_Funds_USD_Millions", "Funding_Gap_USD_Millions", "Relief_Coverage_Pct"
    ]
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    text_columns = ["Country", "City", "Continent", "Disaster_Type", "Severity", "Month"]
    for col in text_columns:
        if col in df.columns:
            df[col] = df[col].fillna("Unknown").astype(str)

    return df


DF = load_data()


def apply_filters(df):
    """Apply URL query filters to the dataframe."""
    filtered = df.copy()

    country = request.args.get("country", "All")
    city = request.args.get("city", "All")
    disaster_type = request.args.get("type", "All")
    severity = request.args.get("severity", "All")
    start_year = request.args.get("start_year")
    end_year = request.args.get("end_year")

    if country != "All" and "Country" in filtered.columns:
        filtered = filtered[filtered["Country"] == country]
    if city != "All" and "City" in filtered.columns:
        filtered = filtered[filtered["City"] == city]
    if disaster_type != "All" and "Disaster_Type" in filtered.columns:
        filtered = filtered[filtered["Disaster_Type"] == disaster_type]
    if severity != "All" and "Severity" in filtered.columns:
        filtered = filtered[filtered["Severity"] == severity]

    if start_year and "Year" in filtered.columns:
        filtered = filtered[filtered["Year"] >= int(start_year)]
    if end_year and "Year" in filtered.columns:
        filtered = filtered[filtered["Year"] <= int(end_year)]

    return filtered


def format_number(value):
    try:
        return f"{int(value):,}"
    except Exception:
        return "0"


@app.route("/")
def index():
    years = sorted(DF["Year"].dropna().astype(int).unique().tolist()) if "Year" in DF.columns else []
    filters = {
        "countries": sorted(DF["Country"].dropna().unique().tolist()) if "Country" in DF.columns else [],
        "cities": sorted(DF["City"].dropna().unique().tolist()) if "City" in DF.columns else [],
        "types": sorted(DF["Disaster_Type"].dropna().unique().tolist()) if "Disaster_Type" in DF.columns else [],
        "severities": sorted(DF["Severity"].dropna().unique().tolist()) if "Severity" in DF.columns else [],
        "min_year": min(years) if years else 2010,
        "max_year": max(years) if years else 2025,
    }
    return render_template("index.html", filters=filters)


@app.route("/api/summary")
def api_summary():
    df = apply_filters(DF)
    total_disasters = len(df)
    deaths = df["Deaths"].sum() if "Deaths" in df.columns else 0
    injured = df["Injured"].sum() if "Injured" in df.columns else 0
    affected = df["Affected_Population"].sum() if "Affected_Population" in df.columns else 0
    economic_damage = df["Economic_Damage_USD"].sum() if "Economic_Damage_USD" in df.columns else 0
    relief_funds = df["Relief_Funds_USD"].sum() if "Relief_Funds_USD" in df.columns else 0
    recovery_avg = df["Recovery_Days"].mean() if "Recovery_Days" in df.columns and len(df) else 0
    coverage_avg = df["Relief_Coverage_Pct"].mean() if "Relief_Coverage_Pct" in df.columns and len(df) else 0

    return jsonify({
        "total_disasters": format_number(total_disasters),
        "deaths": format_number(deaths),
        "injured": format_number(injured),
        "affected": format_number(affected),
        "economic_damage_b": round(economic_damage / 1_000_000_000, 2),
        "relief_funds_m": round(relief_funds / 1_000_000, 2),
        "avg_recovery_days": round(recovery_avg, 1),
        "avg_relief_coverage": round(coverage_avg, 2),
    })


@app.route("/api/charts")
def api_charts():
    df = apply_filters(DF)

    def group_sum(group_col, value_col, top=10):
        if group_col not in df.columns or value_col not in df.columns:
            return {"labels": [], "values": []}
        result = df.groupby(group_col)[value_col].sum().sort_values(ascending=False).head(top)
        return {"labels": result.index.astype(str).tolist(), "values": result.round(2).tolist()}

    def group_count(group_col):
        if group_col not in df.columns:
            return {"labels": [], "values": []}
        result = df[group_col].value_counts()
        return {"labels": result.index.astype(str).tolist(), "values": result.values.tolist()}

    yearly_damage = {"labels": [], "values": []}
    if "Year" in df.columns and "Economic_Damage_USD_Millions" in df.columns:
        y = df.groupby("Year")["Economic_Damage_USD_Millions"].sum().sort_index()
        yearly_damage = {"labels": y.index.astype(int).astype(str).tolist(), "values": y.round(2).tolist()}

    return jsonify({
        "disaster_count_by_type": group_count("Disaster_Type"),
        "deaths_by_type": group_sum("Disaster_Type", "Deaths"),
        "affected_by_city": group_sum("City", "Affected_Population"),
        "severity_count": group_count("Severity"),
        "yearly_damage": yearly_damage,
        "funding_gap_by_type": group_sum("Disaster_Type", "Funding_Gap_USD_Millions"),
    })


@app.route("/api/map")
def api_map():
    df = apply_filters(DF)
    required = ["Latitude", "Longitude", "City", "Country", "Disaster_Type", "Severity", "Deaths", "Affected_Population"]
    for col in required:
        if col not in df.columns:
            return jsonify([])

    map_df = df[(df["Latitude"] != 0) & (df["Longitude"] != 0)].copy()
    # Keep browser fast
    map_df = map_df.sort_values("Affected_Population", ascending=False).head(300)
    rows = []
    for _, row in map_df.iterrows():
        rows.append({
            "lat": float(row["Latitude"]),
            "lon": float(row["Longitude"]),
            "city": str(row["City"]),
            "country": str(row["Country"]),
            "type": str(row["Disaster_Type"]),
            "severity": str(row["Severity"]),
            "deaths": int(row["Deaths"]),
            "affected": int(row["Affected_Population"]),
        })
    return jsonify(rows)


@app.route("/api/records")
def api_records():
    df = apply_filters(DF)
    columns = [
        "Date_Display", "Year", "Country", "City", "Disaster_Type", "Severity",
        "Magnitude", "Deaths", "Injured", "Affected_Population",
        "Economic_Damage_USD_Millions", "Relief_Coverage_Pct", "Recovery_Days"
    ]
    available = [col for col in columns if col in df.columns]
    table = df[available].head(100).copy()
    table = table.rename(columns={
        "Date_Display": "Date",
        "Disaster_Type": "Disaster Type",
        "Affected_Population": "Affected Population",
        "Economic_Damage_USD_Millions": "Damage USD Millions",
        "Relief_Coverage_Pct": "Relief Coverage %",
        "Recovery_Days": "Recovery Days",
    })
    return jsonify(table.to_dict(orient="records"))


if __name__ == "__main__":
    app.run(debug=True)
