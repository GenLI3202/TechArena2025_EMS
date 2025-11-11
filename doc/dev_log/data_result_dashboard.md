
<!-- UPDATED: 2025-10-25 - Integrated into Phase2_dev_plan.md -->
<!-- See: Phase2_dev_plan.md for complete timeline and implementation strategy -->
### **Product Requirements Document: BESS Optimization Dashboard**

#### **1. Product Vision & User Stories**

* **Vision:** To create a local, browser-based dashboard that transforms raw time-series data and complex optimization outputs into an interactive, human-readable format. The goal is to rapidly accelerate insight generation and debugging.
* **User Story 1 (Data):** "As a researcher, I need to visually explore the input price data (DA, FCR, aFRR) across different countries so that I can quickly identify patterns, correlations, and anomalies *before* running my optimization."
* **User Story 2 (Results):** "As an optimizer, I need to compare the performance of my 45 scenarios (country x config) so that I can immediately understand which configuration is most profitable, how the BESS *actually* operates, and what drives its revenue."

---

### **2. View 1: Data Exploration Dashboard**

**Purpose:** This view is dedicated to the *input data*. It allows the user to perform visual exploratory data analysis (EDA) on the market prices.

**Global Controls (Page-Level):**
* **Country Selector:** A dropdown menu (options: DE, AT, CH, HU, CZ). This filter controls all modules on this page.
* **Time Range Selector:** A date-picker or dropdown (options: Full Year, Q1, Q2, Q3, Q4, specific month). This filter controls the "Electricity Price Time Series" chart.

**Component Breakdown:**

* **Module A: Electricity Price Time Series**
    * **Title:** `Electricity Price Time Series (DA, FCR, aFRR)`
    * **Visualization Type:** Multi-series line chart.
    * **Functional Requirements:**
        * Must plot `DA Price`, `FCR Price`, `aFRR Pos Price`, and `aFRR Neg Price` on the same axes.
        * Must be interactive: zoom, pan, and hover-tooltips showing all values at a specific timestamp.
        * Must update dynamically based on the **Global Country Selector** and **Global Time Range Selector**.
        * Must have a clickable legend to toggle individual time series (e.g., hide all aFRR prices to focus on DA vs. FCR).

* **Module B: Price Distribution (DA)**
    * **Title:** `Price Distribution (DA)`
    * **Visualization Type:** Histogram or Kernel Density Estimation (KDE) plot.
    * **Functional Requirements:**
        * Displays the frequency distribution of the `DA Price`.
        * Must update dynamically based on the **Global Country Selector**. (The time range selector does *not* affect this plot; it always shows the full-year distribution for the selected country).

* **Module C: DA Price Heatmap**
    * **Title:** `DA Price Heatmap (Hour of Day vs. Month)`
    * **Visualization Type:** 2D Heatmap.
    * **Functional Requirements:**
        * X-axis: Month (Jan, Feb, ..., Dec).
        * Y-axis: Hour of Day (0, 1, ..., 23).
        * Color: Represents the average `DA Price` for that hour/month block.
        * Must update dynamically based on the **Global Country Selector**.

* **Module D: Price Statistics**
    * **Title:** `Price Statistics`
    * **Visualization Type:** Table or a series of "Stat Cards".
    * **Functional Requirements:**
        * Displays key descriptive statistics: Mean, Median, Std Dev, Min, Max.
        * Must update dynamically based on the **Global Country Selector**.
        * *Bonus:* Include a small dropdown *within* this module to select the market (DA, FCR, aFRR Pos, aFRR Neg) and update the table accordingly.

---

### **3. View 2: Optimization Results Dashboard**

**Purpose:** This view is dedicated to the *output data*. It allows the user to analyze the performance and operational behavior of the solved optimization models.

**Global Controls (Page-Level):**
* **Country Selector:** A dropdown menu (options: DE, AT, CH, HU, CZ).
* **Scenario Selector:** A dropdown menu (options: 0.25C/1.0Cyc, 0.25C/1.5Cyc, ..., 0.5C/2.0Cyc). This is a list of all 9 BESS configurations.
* **These two selectors are the master filters** for this entire view (except for the "Profit vs. Scenario" chart).

**Component Breakdown:**

* **Module A: Key Performance Indicators (KPIs)**
    * **Title:** `Key Performance Indicators (KPIs)`
    * **Visualization Type:** A row of "KPI Cards" (large numbers).
    * **Functional Requirements:**
        * Must display: `Total Annual Profit`, `Levelized ROI`, `Total Cycles Used`, and `NPV`.
        * All four KPIs must update dynamically based on the **Global Country Selector** and **Global Scenario Selector**.

* **Module B: BESS Operational Schedule**
    * **Title:** `BESS Operational Schedule (Sample Week)`
    * **Visualization Type:** A composite chart with dual Y-axes.
        * **Left Y-Axis (Power [MW]):** A bar chart for `Charge/Discharge Power`. (e.g., charge is negative, discharge is positive).
        * **Left Y-Axis (Energy [MWh]):** An area chart for `State of Charge (SoC)`.
        * **Right Y-Axis (Price [€/MWh]):** A line chart for `DA Price` (to show context).
    * **Functional Requirements:**
        * All chart layers must update based on the **Global Country Selector** and **Global Scenario Selector**.
        * Must include a **Time Range Selector** (e.g., a date picker or a "Sample Week" dropdown) to navigate the year.
        * Must be interactive: zoom, pan, and a "crosshair" tooltip that shows SoC, Power, and Price at the same timestamp.

* **Module C: Annual Revenue Breakdown**
    * **Title:** `Annual Revenue Breakdown`
    * **Visualization Type:** Pie Chart or Donut Chart.
    * **Functional Requirements:**
        * Slices must represent the share of total profit from: `DA Arbitrage`, `FCR Revenue`, `aFRR Pos Revenue`, `aFRR Neg Revenue`.
        * Must update dynamically based on the **Global Country Selector** and **Global Scenario Selector**.
        * Tooltip on hover must show the percentage and absolute EUR value for each slice.

* **Module D: Profit vs. Scenario**
    * **Title:** `Profit vs. Scenario (Bar Chart)`
    * **Visualization Type:** Bar Chart.
    * **Functional Requirements:**
        * This chart has a unique filter rule. It should **only** be filtered by the **Global Country Selector**.
        * It must display the `Total Annual Profit` (Y-axis) for all 9 BESS configuration scenarios (X-axis) for the *single selected country*.
        * This provides an "at-a-glance" comparison of all 9 configs for a given market.
        * *Bonus:* The bar corresponding to the scenario chosen in the **Global Scenario Selector** should be highlighted (e.g., a different color).