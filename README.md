
# Road Traffic Crash Analysis in Nigeria (2021–2023)

## Project Overview
This project analyzes road traffic crash occurrences in Nigeria from 2021 to 2023 using quarterly road transport data. The analysis focuses on identifying patterns, trends, and variations in reported crash cases across different states and quarters.

## Objectives
- Examine how road traffic crash occurrences changed across quarters from 2021 to 2023.
- Clean and organize the road transport dataset for analysis.
- Summarize crash totals across relevant periods.
- Visualize trends in road traffic crash occurrences.
- Support data-driven understanding of road safety patterns in Nigeria.

## Files in this Repository
- `Group_B7_Project.ipynb` — Jupyter Notebook containing the main data analysis.
- `Group_B7_Project.py` — Python script version of the analysis.
- `Group_B7_dashboard.py` — Python dashboard script for presenting results.
- `Road_Transport_Data.xlsx` — Source dataset used for the analysis.
- `gadm41_NGA_1.json` — GeoJSON file used for mapping and spatial visualization.
- `requirements.txt` — List of required Python libraries.
- `README.md` — Project documentation.

## Tools and Libraries Used
- Python
- Pandas
- Matplotlib
- GeoPandas
- Jupyter Notebook

## Method Summary
The project loads quarterly crash data from multiple Excel sheets, filters out summary rows to avoid double counting, and calculates total crash cases for each quarter. The cleaned results are then used for analysis and visualization.

## Example Research Question
**How have road traffic crash occurrences changed across quarters from 2021 to 2023 in Nigeria?**

## How to Run the Project

### In Jupyter Notebook
Open the notebook file:

```python
jupyter notebook Group_B7_Project.ipynb
