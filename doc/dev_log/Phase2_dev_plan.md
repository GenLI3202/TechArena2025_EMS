# TechArena 2025 Phase 2 Development Plan (REVISED)

**Created:** 2025-10-25
**Last Updated:** 2025-10-31 (Post-Week 1 Review)
**Timeline:** Oct 25 - Nov 9 (15 days total, 9 days remaining)
**Demo Deadline:** Oct 31 (TODAY)
**Submission Deadline:** Nov 9 (9 days remaining)

---

## ⚠️ WEEK 1 REALITY CHECK - CRITICAL UPDATE

**Overall Progress:** ~40% of Week 1 deliverables completed
**Status:** Behind schedule but with strong foundation
**Revised Target:** Aggressive sprint mode for Week 2

### What Actually Happened in Week 1

**✅ COMPLETED:**
1. **Phase 1 Model Validation** (Oct 27-30)
   - Comprehensive week-long validation across all 45 scenarios
   - Constraint verification and performance testing
   - Model refactoring and optimization
   - **Result:** Production-ready Phase 1 baseline

2. **Phase 2 Mathematical Design** (Oct 26-29)
   - Complete formulation in `doc/gg_dp_p2_model.tex/p2_model_ggdp.tex`
   - Battery degradation modeling approach (cyclic + calendar aging)
   - aFRR energy market integration design
   - **Result:** Implementation-ready mathematical model

3. **Data Processing & Visualization Infrastructure** (Oct 26)
   - Data pipeline: `process_phase2_data.py` ✅
   - View 1 visualizations: All 4 modules implemented ✅
   - McKinsey styling: `viz_config.py` ✅
   - **Result:** Dashboard backend is ready

**❌ NOT STARTED:**
1. Battery degradation model implementation (0%)
2. Phase 2 optimization model extension (0%)
3. Web dashboard application (Dash/Streamlit) (0%)

**Key Insight:** Week 1 prioritized "correctness over speed" - ensuring Phase 1 is bulletproof before extending. This was wise but creates time pressure for Week 2.

---

## Executive Summary (REVISED)

### Strategic Answer to Your Question

**Original Question:** Should you migrate visualization to web dashboard first, or focus on battery degradation modeling?

**REVISED Answer:** Neither-first is no longer viable. **DEGRADATION-FIRST ONLY.**

### Week 2 Strategy (Nov 1-9, 9 days to submission)

**CRITICAL PATH (Non-negotiable):**
1. **Days 1-3 (Nov 1-3):** Battery degradation model + Phase 2 optimization (60% of grade)
2. **Days 4-6 (Nov 4-6):** Scenario analysis (45 scenarios)
3. **Days 7-9 (Nov 7-9):** Results analysis + documentation + dashboard development

**SCOPE ADJUSTMENTS:**
- ✅ 45 scenarios: 5 countries (DE, AT, CH, CZ, HU) × 3 C-rates × 3 cycle settings
- ✅ Web dashboard development included
- ✅ 5 SOC segments (simplified degradation)
- [?] Temperature effects → Optional, if time permits (focus on C-rate, SOC, DoD primarily)

**Why This Will Work:**
- Visualization infrastructure already exists (Oct 26 work)
- Phase 1 model is validated and ready to extend
- Mathematical design is complete - just needs implementation
- 45 scenarios provide comprehensive methodology across all target markets

### Visualization Strategy: Web Dashboard + Notebooks

| Tool | Plan | Status | Justification |
|------|------|--------|---------------|
| **Web Dashboard** | Plotly Dash, 3 tabs, interactive | ✅ INCLUDED | Enhances presentation and code quality (target 90%+) |
| **Jupyter Notebooks** | Development & analysis | ✅ INCLUDED | View 1 functions already work; used for detailed analysis |
| **Existing Viz Functions** | Backend for dashboard | ✅ READY | `plot_*_mckinsey()` functions are presentation-ready |

**Impact on Code Quality Grade (20%):**
- Web dashboard with professional McKinsey-style plots: 90%+ potential
- Integration with existing visualization functions reduces development time
- Notebooks complement dashboard for detailed technical analysis

---

## 1. Evaluation Criteria Analysis (UNCHANGED)

### Phase 2 Grading Breakdown

| Criteria | Weight | Current Status | Week 2 Target | Development Priority |
|----------|--------|----------------|---------------|---------------------|
| **Revenue maximization** | 30% | Phase 1 baseline solid | 80%+ | P1 - Enhance with intraday aFRR |
| **Battery degradation** | 30% | ❌ Not started (0%) | 75%+ | **P0 - CRITICAL PATH** |
| **Investment optimization** | 10% | Phase 1 baseline solid | 85%+ | P2 - Update with degradation impact |
| **Configuration optimization** | 10% | Phase 1 validated | 85%+ | P2 - Re-analyze with degradation |
| **Code quality & documentation** | 20% | Good foundation exists | 85%+ | P1 - Notebooks + docs |

**Revised Target Score:** 80% (realistic given time pressure)
**Original Target:** 87% (no longer achievable without cutting sleep)

### What's NEW in Phase 2

1. **Battery Degradation Modeling** - Using simplified ORC approach (5 segments)
2. **Intraday aFRR Energy Market** - New revenue stream (activation-based)
3. **Enhanced Results Presentation** - Jupyter notebooks with professional plots

---

## 2. WEEK 2: Emergency Sprint Plan (Nov 1-9)

### Critical Time Budget

**Total Time Available:** 9 days × 8 hours/day = **72 hours**
**Required Work:** ~80 hours (original Week 1 + Week 2)
**Strategy:** Aggressive descoping + parallel work + accepting "good enough"

---

## 3. DAILY BREAKDOWN: Nov 1-3 (Critical Path Implementation)

### Day 1 (Nov 1): Battery Degradation Model Foundation

**Objective:** Implement simplified degradation calculator

#### Morning Session (4 hours): Literature & Parameters

**Task 1.1: Extract Degradation Parameters (2 hours)**
- [ ] Read Collath et al. (2023) Section 2.2 (Calendar aging model)
- [ ] Read Xu et al. (2017) Section III (Piecewise-linear cycling cost)
- [ ] Document key equations in notebook for reference
- [ ] Extract numerical parameters:
  - Calendar aging: SOC vs. capacity fade rate (Table II)
  - Cyclic aging: DoD vs. cycle life (Figure 3)

**Task 1.2: Design Simplified Model (2 hours)**
- [ ] Choose 5 SOC segments (0-20%, 20-40%, 40-60%, 60-80%, 80-100%)
- [ ] Calculate marginal costs for each segment:
  ```python
  # Example structure:
  DEGRADATION_COST = {
      'segment_1': 0.01,  # EUR/kWh (shallow cycles - cheap)
      'segment_2': 0.015,
      'segment_3': 0.02,
      'segment_4': 0.03,
      'segment_5': 0.05,  # EUR/kWh (deep cycles - expensive)
  }
  ```
- [ ] Define calendar aging breakpoints (5 points: 0%, 25%, 50%, 75%, 100% SOC)

#### Afternoon Session (4 hours): Implementation

**Task 1.3: Create `battery_degradation.py` (4 hours)**

```python
"""
Battery Degradation Model for TechArena 2025 Phase 2
====================================================

Implements simplified ORC-based degradation model with:
- Cyclic aging (piecewise-linear by SOC segment)
- Calendar aging (SOS2 linearization)

Author: Team SoloGen
Date: November 2025
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, List
import logging

logger = logging.getLogger(__name__)


class BatteryDegradationModel:
    """
    Simplified battery degradation calculator for BESS optimization.

    Focuses on P1 factors:
    - C-rate (implicit in power profile)
    - SoC range (via segmentation)
    - Depth of discharge (via piecewise-linear cost)

    Ignores for simplicity:
    - Temperature effects
    - Detailed SOH evolution (uses cost proxy instead)
    """

    def __init__(self, battery_capacity_kwh: float = 4472,
                 battery_cost_eur_per_kwh: float = 200,
                 expected_lifetime_years: int = 10):
        """
        Initialize degradation model with battery specs.

        Args:
            battery_capacity_kwh: Nominal battery capacity (default: 4472 kWh)
            battery_cost_eur_per_kwh: Battery replacement cost (default: 200 EUR/kWh)
            expected_lifetime_years: Expected operational lifetime (default: 10 years)
        """
        self.capacity_kwh = battery_capacity_kwh
        self.cost_eur_per_kwh = battery_cost_eur_per_kwh
        self.lifetime_years = expected_lifetime_years

        # Simplified degradation parameters (from literature)
        # These are annualized costs in EUR per kWh discharged from each segment
        self.cyclic_cost_per_segment = {
            1: 0.008,   # Segment 1: 80-100% SOC (shallow - cheapest)
            2: 0.012,   # Segment 2: 60-80% SOC
            3: 0.018,   # Segment 3: 40-60% SOC (middle)
            4: 0.028,   # Segment 4: 20-40% SOC
            5: 0.045,   # Segment 5: 0-20% SOC (deep - most expensive)
        }

        # Calendar aging: Cost per kWh*hour of storage at different SOC levels
        # (annualized)
        self.calendar_cost_by_soc = {
            0.0: 0.001,    # 0% SOC
            0.25: 0.0015,  # 25% SOC
            0.50: 0.002,   # 50% SOC
            0.75: 0.0035,  # 75% SOC
            1.0: 0.005,    # 100% SOC (highest calendar aging)
        }

        # SOC boundaries for each segment (5 segments)
        self.segment_bounds = {
            1: (0.80, 1.00),
            2: (0.60, 0.80),
            3: (0.40, 0.60),
            4: (0.20, 0.40),
            5: (0.00, 0.20),
        }

        logger.info("Battery degradation model initialized")
        logger.info(f"Capacity: {battery_capacity_kwh} kWh, "
                   f"Cost: {battery_cost_eur_per_kwh} EUR/kWh, "
                   f"Lifetime: {expected_lifetime_years} years")

    def get_segment_from_soc(self, soc: float) -> int:
        """
        Determine which segment a given SOC belongs to.

        Args:
            soc: State of charge (0.0 to 1.0)

        Returns:
            Segment number (1-5)
        """
        for seg_num, (lower, upper) in self.segment_bounds.items():
            if lower <= soc <= upper:
                return seg_num
        # Edge case: return nearest segment
        if soc > 1.0:
            return 1
        else:
            return 5

    def get_cyclic_cost_parameters(self) -> Dict[int, Tuple[float, float]]:
        """
        Get cyclic aging cost parameters for Pyomo model.

        Returns:
            Dict mapping segment number to (capacity_kwh, cost_eur_per_kwh)
        """
        segment_capacity = self.capacity_kwh / 5  # Equal segments

        return {
            seg: (segment_capacity, cost)
            for seg, cost in self.cyclic_cost_per_segment.items()
        }

    def get_calendar_cost_breakpoints(self) -> Tuple[List[float], List[float]]:
        """
        Get calendar aging breakpoints for SOS2 linearization.

        Returns:
            Tuple of (soc_points, cost_points) for Pyomo SOS2 constraints
        """
        soc_points = sorted(self.calendar_cost_by_soc.keys())
        cost_points = [self.calendar_cost_by_soc[soc] for soc in soc_points]

        return soc_points, cost_points

    def estimate_annual_degradation_cost(self,
                                        discharge_by_segment: Dict[int, float],
                                        avg_soc: float,
                                        hours: int = 8760) -> Dict[str, float]:
        """
        Estimate annual degradation cost from operational profile.

        This is a post-optimization analysis function (not used in optimization itself).

        Args:
            discharge_by_segment: Total kWh discharged from each segment in the year
            avg_soc: Average SOC throughout the year (0.0 to 1.0)
            hours: Number of hours (default: 8760 for full year)

        Returns:
            Dict with 'cyclic_cost', 'calendar_cost', 'total_cost' in EUR
        """
        # Cyclic cost
        cyclic_cost = sum(
            discharge_by_segment.get(seg, 0) * cost
            for seg, cost in self.cyclic_cost_per_segment.items()
        )

        # Calendar cost (interpolate for avg SOC)
        soc_points, cost_points = self.get_calendar_cost_breakpoints()
        calendar_cost_per_hour = np.interp(avg_soc, soc_points, cost_points)
        calendar_cost = calendar_cost_per_hour * self.capacity_kwh * hours

        return {
            'cyclic_cost_eur': cyclic_cost,
            'calendar_cost_eur': calendar_cost,
            'total_degradation_cost_eur': cyclic_cost + calendar_cost
        }
```

**Deliverable:** Working `battery_degradation.py` with tests

---

### Day 2 (Nov 2): Phase 2 Optimization Model - Part 1

**Objective:** Extend Phase 1 model with degradation and aFRR energy

#### Morning Session (4 hours): Model Structure

**Task 2.1: Create `model_phase2.py` (4 hours)**

```python
"""
Phase 2 BESS Optimization Model with Degradation
=================================================

Extends Phase 1 model (model.py) with:
1. Battery degradation cost (cyclic + calendar)
2. aFRR energy market integration

Author: Team SoloGen
Date: November 2025
"""

from model import ImprovedBESSOptimizer
from battery_degradation import BatteryDegradationModel
import pyomo.environ as pyo
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


class Phase2BESSOptimizer(ImprovedBESSOptimizer):
    """
    Phase 2 BESS optimizer with degradation modeling.

    Extends Phase 1 by:
    - Adding aFRR energy market variables
    - Segmenting SOC for piecewise-linear cyclic aging
    - Adding SOS2 constraints for calendar aging
    - Modifying objective to subtract degradation cost
    """

    def __init__(self):
        """Initialize Phase 2 optimizer."""
        super().__init__()

        # Initialize degradation model
        self.degradation_model = BatteryDegradationModel(
            battery_capacity_kwh=self.battery_params['capacity_kwh']
        )

        # Phase 2 market parameters
        self.market_params['min_bid_afrr_energy'] = 1.0  # MW

        # SOC segmentation (5 segments for cyclic aging)
        self.num_segments = 5
        self.segment_capacity = self.battery_params['capacity_kwh'] / self.num_segments

        logger.info("Phase 2 BESS Optimizer initialized with degradation modeling")

    def create_phase2_model(self, country_data: pd.DataFrame,
                           c_rate: float, daily_cycles: float,
                           include_degradation: bool = True) -> pyo.ConcreteModel:
        """
        Create Phase 2 Pyomo model with degradation.

        Args:
            country_data: Market data (same as Phase 1)
            c_rate: C-rate configuration
            daily_cycles: Daily cycle limit (may be ignored if degradation included)
            include_degradation: Whether to include degradation cost (default: True)

        Returns:
            Pyomo ConcreteModel ready to solve
        """
        logger.info(f"Creating Phase 2 model: C-rate={c_rate}, "
                   f"Cycles={daily_cycles}, Degradation={include_degradation}")

        # Start with Phase 1 model structure
        # (We'll modify it rather than calling super().create_model())

        model = pyo.ConcreteModel()

        # === SETS === (same as Phase 1, plus segments)
        # ... [Implementation continues - see below]

        return model
```

#### Afternoon Session (4 hours): aFRR Energy Market Variables

**Task 2.2: Add aFRR Energy Market Variables (4 hours)**
- [ ] Add variables: `p_afrr_energy_pos[t]`, `p_afrr_energy_neg[t]`
- [ ] Add binaries: `y_afrr_energy_pos[t]`, `y_afrr_energy_neg[t]`
- [ ] Add to objective:
  ```python
  afrr_energy_revenue = sum(
      (prices['afrr_energy_pos'][t] * model.p_afrr_energy_pos[t] -
       prices['afrr_energy_neg'][t] * model.p_afrr_energy_neg[t])
      * dt / 1000  # Convert kW to MW
      for t in model.T
  )
  ```
- [ ] Add minimum bid constraints (similar to DA market)

**Deliverable:** Model with aFRR energy integrated

---

### Day 3 (Nov 3): Phase 2 Model - Part 2 & Critical Testing

**Objective:** Complete degradation integration and validate model solves

#### Morning Session (4 hours): Degradation Variables

**Task 3.1: Add SOC Segmentation (2 hours)**
- [ ] Add variables: `e_soc_segment[j, t]` for j=1..5 segments
- [ ] Add variables: `p_ch_segment[j, t]`, `p_dis_segment[j, t]`
- [ ] Modify SOC dynamics:
  ```python
  # Total SOC is sum of segments
  model.total_soc_constraint = pyo.Constraint(
      model.T,
      rule=lambda m, t: m.e_soc[t] == sum(m.e_soc_segment[j, t] for j in range(1, 6))
  )

  # Segment capacity limits
  model.segment_capacity_constraint = pyo.Constraint(
      range(1, 6), model.T,
      rule=lambda m, j, t: m.e_soc_segment[j, t] <= segment_capacity
  )
  ```

**Task 3.2: Add Calendar Aging SOS2 (2 hours)**
- [ ] Add variables: `lambda_soc[i, t]` for i=1..5 SOC breakpoints
- [ ] Add SOS2 constraint:
  ```python
  model.sos2_constraint = pyo.SOSConstraint(
      model.T,
      var=model.lambda_soc,
      sos=2
  )
  ```
- [ ] Link SOC to calendar cost via breakpoints

#### Afternoon Session (4 hours): Integration & Testing

**Task 3.3: Update Objective Function (1 hour)**
- [ ] Add degradation cost terms:
  ```python
  # Cyclic aging cost
  cyclic_cost = sum(
      cost_per_seg[j] * model.p_dis_segment[j, t] * dt
      for j in range(1, 6)
      for t in model.T
  )

  # Calendar aging cost
  calendar_cost = sum(
      model.calendar_cost[t] * dt
      for t in model.T
  )

  # Modified objective
  model.obj = pyo.Objective(
      expr=da_revenue + as_revenue + afrr_energy_revenue - cyclic_cost - calendar_cost,
      sense=pyo.maximize
  )
  ```

**Task 3.4: CRITICAL TESTING (3 hours)**
- [ ] Test Case 1: Phase 1 comparison
  - Run same scenario (DE, 0.5C, 2.0) with degradation OFF
  - Results should match Phase 1 within 1%

- [ ] Test Case 2: Phase 2 with degradation
  - Run DE, 0.5C, 2.0 with degradation ON
  - Model must solve within 10 minutes
  - Check: Revenue should be higher (aFRR energy), but net profit lower (degradation cost)

- [ ] Test Case 3: Solver tolerance
  - If timeout: Increase MIP gap to 3-5%
  - If infeasible: Debug constraint violations

**GATE:** Model must solve successfully before continuing to Day 4

**Deliverable:** Validated Phase 2 model that solves

---

## 4. DAILY BREAKDOWN: Nov 4-6 (Scenario Analysis - Complete Matrix)

### Day 4 (Nov 4): Batch Run Setup & Launch

**Objective:** Run 45 scenarios overnight

#### Morning Session (3 hours): Setup

**Task 4.1: Create Scenario Runner (3 hours)**

```python
"""
Phase 2 Scenario Analysis Runner
=================================

Runs complete scenario matrix:
- Countries: DE, AT, CH, CZ, HU (5 countries)
- C-rates: 0.25, 0.33, 0.5 (3 rates)
- Daily cycles: 1.0, 1.5, 2.0 (3 limits)
Total: 5 × 3 × 3 = 45 scenarios

Author: Team SoloGen
Date: November 2025
"""

from model_phase2 import Phase2BESSOptimizer
from market_da import load_phase2_market_tables
import pandas as pd
import json
from pathlib import Path
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Complete scenario matrix
COUNTRIES = ['DE', 'AT', 'CH', 'CZ', 'HU']  # All 5 target countries
C_RATES = [0.25, 0.33, 0.5]
DAILY_CYCLES = [1.0, 1.5, 2.0]

def run_phase2_scenarios():
    """Run all 45 Phase 2 scenarios."""

    results = []
    optimizer = Phase2BESSOptimizer()

    # Load market data
    data_path = Path('data/TechArena2025_Phase2_data.xlsx')
    tables = load_phase2_market_tables(data_path)

    scenario_num = 0
    total_scenarios = len(COUNTRIES) * len(C_RATES) * len(DAILY_CYCLES)  # 5 × 3 × 3 = 45

    for country in COUNTRIES:
        country_data = prepare_country_data(tables, country)

        for c_rate in C_RATES:
            for cycles in DAILY_CYCLES:
                scenario_num += 1
                logger.info(f"[{scenario_num}/{total_scenarios}] "
                           f"Running {country}, C={c_rate}, N={cycles}")

                try:
                    # Run optimization
                    result = optimizer.optimize_phase2(
                        country_data=country_data,
                        c_rate=c_rate,
                        daily_cycles=cycles,
                        solver_name='cbc',  # or 'gurobi'
                        time_limit=600,
                        mip_gap=0.03  # Accept 3% gap for speed
                    )

                    results.append({
                        'country': country,
                        'c_rate': c_rate,
                        'daily_cycles': cycles,
                        'status': 'success',
                        **result
                    })

                except Exception as e:
                    logger.error(f"Scenario failed: {e}")
                    results.append({
                        'country': country,
                        'c_rate': c_rate,
                        'daily_cycles': cycles,
                        'status': 'failed',
                        'error': str(e)
                    })

    # Save results
    df = pd.DataFrame(results)
    output_path = Path('results/phase2/scenario_analysis.csv')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)

    logger.info(f"Completed {len(results)} scenarios. Results saved to {output_path}")
    return df
```

#### Afternoon Session (5 hours): Launch & Monitor

**Task 4.2: Start Batch Run (5 hours)**
- [ ] Run `python run_phase2_scenarios.py` in background
- [ ] Monitor progress (45 scenarios × 10 min = ~7.5 hours)
- [ ] Debug any failed scenarios in real-time
- [ ] If solver times out:
  - Increase MIP gap to 5%
  - Reduce time limit to 300s
  - Accept suboptimal solutions

**Deliverable:** 45 scenario results (CSV file)

---

### Day 5 (Nov 5): Complete Runs & Analysis

#### Morning Session (4 hours): Finish & Collect

**Task 5.1: Complete Batch (if needed) (2 hours)**
- [ ] Rerun any failed scenarios
- [ ] Accept partial results if necessary (minimum 40/45 scenarios)

**Task 5.2: Results Analysis (2 hours)**
- [ ] Load `scenario_analysis.csv`
- [ ] Calculate key metrics:
  - Annual revenue by market (DA, FCR, aFRR capacity, aFRR energy)
  - Degradation cost (cyclic vs. calendar)
  - Net profit (revenue - degradation)
- [ ] Identify best configuration per country

#### Afternoon Session (4 hours): Visualization

**Task 5.3: Create Analysis Notebook (4 hours)**

Use existing visualization functions from Oct 26 work:
- [ ] Bar chart: Revenue comparison across countries
- [ ] Heatmap: Configuration performance (C-rate × cycles)
- [ ] Scatter: Revenue vs. degradation cost (Pareto frontier)
- [ ] Table: Top 5 configurations by net profit

**Deliverable:** Analysis notebook with key insights

---

### Day 6 (Nov 6): Investment Analysis Update

**Objective:** Calculate degradation-adjusted NPV

#### Full Day Session (8 hours): DCF Model

**Task 6.1: Update Investment Calculator (4 hours)**

```python
def calculate_npv_with_degradation(
    annual_revenue: float,
    degradation_cost: float,
    country: str,
    years: int = 10
) -> Dict[str, float]:
    """
    Calculate NPV accounting for degradation over 10 years.

    Simplified assumptions:
    - Linear revenue decline with capacity fade (1% per year)
    - Constant degradation cost (conservative)
    - No battery replacement (assume stays above 80% SOH)
    """

    WACC = {'DE': 0.083, 'AT': 0.083, 'CH': 0.083, 'HU': 0.15, 'CZ': 0.12}
    INFLATION = {'DE': 0.02, 'AT': 0.033, 'CH': 0.001, 'HU': 0.046, 'CZ': 0.029}

    wacc = WACC[country]
    inflation = INFLATION[country]
    capex = 200 * 4472  # EUR/kWh * capacity

    # Calculate NPV
    npv = -capex  # Initial investment

    for year in range(1, years + 1):
        # Revenue decreases due to capacity fade (assume 1% per year)
        capacity_factor = 1.0 - 0.01 * year

        # Net cash flow
        net_revenue = (annual_revenue * capacity_factor - degradation_cost)
        inflated_revenue = net_revenue * (1 + inflation) ** (year - 1)

        # Discount to present value
        pv = inflated_revenue / (1 + wacc) ** year
        npv += pv

    # Salvage value (assume 90% SOH after 10 years)
    salvage = capex * 0.3 * 0.9
    npv += salvage / (1 + wacc) ** years

    # ROI
    levelized_roi = (npv / capex) * 100

    return {
        'npv_eur': npv,
        'levelized_roi_percent': levelized_roi,
        'payback_years': estimate_payback(annual_revenue, degradation_cost, capex)
    }
```

**Task 6.2: Run Investment Analysis (2 hours)**
- [ ] Calculate NPV for all 27 scenarios
- [ ] Identify best investment country
- [ ] Generate investment recommendation table

**Task 6.3: Configuration Ranking (2 hours)**
- [ ] Rank configurations per country by NPV
- [ ] Document optimal settings (C-rate, cycles)
- [ ] Calculate sensitivity to degradation assumptions

**Deliverable:** Investment analysis with NPV rankings

---

## 5. DAILY BREAKDOWN: Nov 7-9 (Documentation, Dashboard & Submission)

### Day 7 (Nov 7): Master Results Notebook + Dashboard Development

**Objective:** Create presentation-quality Jupyter notebook and start dashboard development

#### Morning Session (4 hours): Notebook Structure

**Task 7.1: Create Master Notebook (4 hours)**

Sections:
1. **Introduction** (Markdown)
   - Phase 2 objectives
   - Methodology overview

2. **Market Data Exploration** (Use Oct 26 functions)
   - `plot_price_time_series_mckinsey()` for each country
   - `plot_da_price_heatmap_mckinsey()` to show patterns

3. **Phase 2 Model Overview** (Markdown + Equations)
   - Show degradation formulation
   - Explain piecewise-linear approach
   - Export LaTeX equations as images

4. **Scenario Results** (Tables + Charts)
   - Revenue comparison bar chart
   - Configuration heatmaps
   - Best configs per country

#### Afternoon Session (4 hours): Degradation Analysis

**Task 7.2: Degradation Visualizations (4 hours)**
- [ ] Degradation cost breakdown (cyclic vs. calendar)
- [ ] Revenue vs. degradation scatter plot
- [ ] SOC usage distribution (show shallow vs. deep cycling)
- [ ] Pareto frontier (if time permits)

**Deliverable:** Complete results notebook

---

### Day 8 (Nov 8): Dashboard Development + Technical Report

**Objective:** Complete web dashboard and write technical report

#### Morning Session (4 hours): Dashboard Development

**Task 8.1: Create Interactive Dashboard (4 hours)**

```python
"""
Phase 2 Interactive Dashboard
==============================

Plotly Dash web app with 3 main views:
1. Market Data Explorer: Price visualization across countries
2. Scenario Results: Configuration comparison and analysis
3. Investment Analysis: NPV, ROI, and recommendations

Author: Team SoloGen
Date: November 2025
"""

import dash
from dash import dcc, html, Input, Output
import plotly.graph_objects as go
from market_da import plot_price_time_series_mckinsey, plot_da_price_heatmap_mckinsey
from viz_config import MCKINSEY_COLORS, MCKINSEY_FONTS
import pandas as pd

# Initialize Dash app
app = dash.Dash(__name__)

# Layout with 3 tabs
app.layout = html.Div([
    html.H1("TechArena 2025 Phase 2 - BESS Optimization Results"),
    dcc.Tabs([
        dcc.Tab(label='Market Data', children=[
            # Country selector and price visualizations
        ]),
        dcc.Tab(label='Scenario Results', children=[
            # Configuration heatmaps and comparison charts
        ]),
        dcc.Tab(label='Investment Analysis', children=[
            # NPV rankings and recommendations
        ]),
    ])
])

if __name__ == '__main__':
    app.run_server(debug=True)
```

- [ ] Implement Tab 1: Market Data Explorer with country selector
- [ ] Implement Tab 2: Scenario Results with interactive filters
- [ ] Implement Tab 3: Investment Analysis with NPV rankings
- [ ] Integrate existing McKinsey-style plotting functions
- [ ] Test dashboard functionality

#### Afternoon Session (4 hours): Report Writing

**Structure:**

1. **Executive Summary** (1 page, 1 hour)
   - Key findings
   - Best investment country: [COUNTRY]
   - Optimal configuration: [C-rate] / [cycles]
   - Expected ROI: [X]%

2. **Methodology** (5 pages, 3 hours)
   - **2.1 Battery Degradation Model**
     - Piecewise-linear cyclic aging (Xu et al. approach)
     - SOS2 calendar aging (Collath et al. approach)
     - Parameters and assumptions
   - **2.2 Optimization Model**
     - Phase 2 extensions (aFRR energy + degradation)
     - Objective function formulation
     - Key constraints
   - **2.3 Scenario Matrix**
     - 45 scenarios (5 countries × 9 configs)
     - Solver settings and performance

3. **Results** (6 pages, 3 hours)
   - **3.1 Revenue Analysis**
     - Comparison across countries
     - Market contribution breakdown (DA, FCR, aFRR capacity, aFRR energy)
     - Impact of aFRR energy integration (+X% revenue)
   - **3.2 Degradation Impact**
     - Degradation cost by configuration
     - Trade-off: Revenue vs. battery life
     - Cyclic vs. calendar aging contribution
   - **3.3 Investment Recommendations**
     - NPV analysis
     - Optimal configurations per country
     - Sensitivity analysis

4. **Discussion** (2 pages, 1 hour)
   - Trade-offs (revenue vs. lifetime)
   - Limitations (simplified model, ignored factors)
   - Sensitivity to assumptions

5. **Conclusion** (1 page, 0.5 hours)
   - Key insights
   - Recommendations
   - Future work

**Appendices:**
- A: Model equations (LaTeX)
- B: Parameter tables
- C: Scenario results summary

**Deliverable:** 15-page technical report (PDF)

---

### Day 9 (Nov 9): Submission Preparation

**Objective:** Package and submit

#### Morning Session (4 hours): Submission Files

**Task 9.1: Generate Required CSVs (2 hours)**

1. **TechArena_Phase2_Configuration.csv**
   - Best configuration analysis
   - Columns: Country, C_rate, Daily_Cycles, Annual_Revenue, Degradation_Cost, Net_Profit, NPV, ROI

2. **TechArena_Phase2_Investment.csv**
   - 10-year cash flow projection
   - Columns: Country, Year, Revenue, Degradation_Cost, Net_CF, SOH, NPV, WACC, Inflation

3. **TechArena_Phase2_Operation.csv**
   - Best scenario operational schedule (full year)
   - Columns: Timestamp, SOC, Energy_Stored, Charge, Discharge, FCR_Bid, aFRR_Pos_Bid, aFRR_Neg_Bid, aFRR_Energy_Pos, aFRR_Energy_Neg

**Task 9.2: Code Package (2 hours)**
- [ ] Create `README.md` with setup instructions
- [ ] Update `requirements.txt`
- [ ] Add docstrings to all new functions
- [ ] Create example notebook: `example_phase2_usage.ipynb`

#### Afternoon Session (3 hours): Final Checks & Submit

**Task 9.3: Validation (1.5 hours)**
- [ ] Run end-to-end test with fresh Python environment
- [ ] Verify all CSVs open correctly
- [ ] Proofread report (spell check, equation numbering)
- [ ] Check code runs without errors

**Task 9.4: Create Submission ZIP (0.5 hours)**

```
TechArena2025_Phase2_Submission.zip
├── code/
│   ├── py_script/
│   │   ├── model.py                    # Phase 1 (validated)
│   │   ├── model_phase2.py             # Phase 2 (NEW)
│   │   ├── battery_degradation.py      # Degradation model (NEW)
│   │   ├── market_da.py                # Data loading + viz
│   │   ├── viz_config.py               # McKinsey styling
│   │   ├── process_phase2_data.py      # Data pipeline
│   │   ├── investment_analysis.py      # Updated for degradation
│   │   └── run_phase2_scenarios.py     # Scenario runner (NEW)
│   ├── notebooks/
│   │   ├── phase2_results_master.ipynb # Main results notebook
│   │   └── example_phase2_usage.ipynb  # Usage demo
│   ├── requirements.txt
│   └── README.md
├── output/
│   ├── TechArena_Phase2_Configuration.csv
│   ├── TechArena_Phase2_Investment.csv
│   └── TechArena_Phase2_Operation.csv
├── docs/
│   └── Technical_Report_Phase2.pdf
└── README.txt                          # Submission instructions
```

**Task 9.5: SUBMIT (1 hour)**
- [ ] Upload to submission portal
- [ ] Confirm receipt
- [ ] 🎉 **CELEBRATE!** 🎉

---

## 6. Risk Management (UPDATED)

### Critical Risks

| Risk | Likelihood | Impact | Mitigation | Status |
|------|-----------|--------|------------|--------|
| **Model doesn't solve** | HIGH | CRITICAL | Accept 5% MIP gap; simplify degradation | ACTIVE |
| **Scenarios don't finish** | MEDIUM | HIGH | Plan for 45 scenarios; can reduce to 30 if needed | MITIGATED |
| **Parameter extraction unclear** | MEDIUM | MEDIUM | Use simplified assumptions from literature reviews | ACTIVE |
| **Integration bugs** | HIGH | MEDIUM | 50% time buffer in Days 2-3; extensive testing | PLANNED |
| **Dashboard complexity** | MEDIUM | LOW | Use existing viz functions; prioritize core features | PLANNED |
| **Report quality suffers** | LOW | MEDIUM | Reuse Phase 1 report structure | MITIGATED |

### Contingency Decision Points

**If behind schedule by Nov 6:**
1. Reduce to 30 scenarios (top configs per country)
2. Simplify dashboard to 2 tabs instead of 3
3. Skip Pareto frontier analysis
4. Accept degradation model without calendar aging (cyclic only)

**Quick Wins Available:**
- Reuse Phase 1 validation plots in report
- Reuse Phase 1 report methodology sections
- Use existing Oct 26 visualization functions directly
- Leverage validated Phase 1 model (minimal changes needed)

---

## 7. Success Metrics (REVISED)

### Today's Demo (Oct 31)

**Achievable Goals:**
- ✅ Show Phase 1 validation results (impressive plots exist)
- ✅ Present Phase 2 mathematical design (LaTeX document ready)
- ✅ Demonstrate View 1 visualizations (Oct 26 work)
- ✅ Outline realistic Week 2 sprint plan

**Key Message:** "We prioritized correctness over speed in Week 1. Our Phase 1 foundation is bulletproof, our Phase 2 design is complete, and we're ready for focused execution."

### Submission Success (Nov 9)

**Target Submission:**
- ✅ Working Phase 2 model with degradation integration
- ✅ 45 scenarios with results (acceptable: 40+ scenarios)
- ✅ Degradation analysis showing cost impact
- ✅ Investment recommendation with NPV across all countries
- ✅ Interactive web dashboard for results visualization
- ✅ 15-page technical report
- ✅ All required CSV files
- ✅ Clean, documented code with dashboard

### Grading Target (UPDATED)

| Criterion | Original | Updated | Strategy |
|-----------|----------|---------|----------|
| Revenue (30%) | 85% | 85% | aFRR energy + comprehensive optimization |
| Degradation (30%) | 90% | 80% | Simplified but theoretically sound model |
| Investment (10%) | 85% | 85% | Keep high - DCF across 5 countries |
| Configuration (10%) | 85% | 90% | 9 configs × 5 countries = comprehensive |
| Code Quality (20%) | 90% | 90% | Dashboard + notebooks + docs score high |
| **Overall** | **87%** | **85%** | **Strong and competitive** |

---

## 8. Tools & Technology Stack (UPDATED)

### Core Python Environment

```txt
# Optimization (Phase 1 + Phase 2)
pyomo>=6.6.0
cbc>=2.10.0 or gurobi>=10.0.0

# Data Processing
pandas>=2.0.0
numpy>=1.24.0

# Visualization (Already implemented - Oct 26)
plotly>=5.14.0
dash>=2.14.0           # For web dashboard
scipy>=1.10.0          # For KDE
pyarrow>=14.0.0        # For Parquet (5.6x compression)

# Notebook Environment
jupyterlab>=3.6.0

# Code Quality
black>=23.3.0
flake8>=6.0.0
```

### Visualization Strategy (UPDATED)

**DECISION:** Web dashboard + Jupyter notebooks for comprehensive presentation

**Rationale:**
- Oct 26 work provides presentation-ready McKinsey-style plots as foundation
- All 4 View 1 modules already implemented - can be directly integrated into dashboard
- Dashboard enhances code quality score (target 90%+)
- Notebooks complement dashboard for detailed technical analysis

**Implementation Plan:**
- **Day 8 (Nov 8):** Build interactive Plotly Dash web app (4 hours)
  - Tab 1: Market Data Explorer
  - Tab 2: Scenario Results Comparison
  - Tab 3: Investment Analysis
- Leverage existing functions from `viz_config.py` and `market_da.py`
- Use notebooks for additional detailed analysis and documentation

**Files to Use:**
- `viz_config.py` - McKinsey styling
- `market_da.py` - All plot functions (`plot_*_mckinsey()`)
- `test_phase2_visualizations.ipynb` - Example usage and detailed analysis

---

## 9. Implementation Checklist (DAILY TRACKING)

### ✅ Completed (Oct 25-31)

**Phase 1 Foundation:**
- [x] Model refactoring and optimization
- [x] Comprehensive 45-scenario validation
- [x] Performance testing and constraint verification

**Phase 2 Design:**
- [x] Mathematical formulation (`p2_model_ggdp.tex`)
- [x] Degradation modeling approach
- [x] aFRR energy market integration design

**Data & Visualization Infrastructure:**
- [x] Data processing pipeline (`process_phase2_data.py`)
- [x] View 1 visualizations (all 4 modules)
- [x] McKinsey styling configuration (`viz_config.py`)
- [x] Custom exceptions for error handling

### 📋 Week 2 Checklist (Nov 1-9)

#### Day 1 (Nov 1): Degradation Model
- [ ] Extract parameters from Collath et al. (2023)
- [ ] Extract parameters from Xu et al. (2017)
- [ ] Create `battery_degradation.py`
- [ ] Implement `BatteryDegradationModel` class
- [ ] Test with dummy data
- [ ] Document assumptions

#### Day 2 (Nov 2): Phase 2 Model Part 1
- [ ] Create `model_phase2.py`
- [ ] Extend `ImprovedBESSOptimizer` → `Phase2BESSOptimizer`
- [ ] Add aFRR energy variables and constraints
- [ ] Add SOC segmentation variables
- [ ] Implement total power aggregation

#### Day 3 (Nov 3): Phase 2 Model Part 2
- [ ] Add SOS2 calendar aging variables
- [ ] Implement degradation cost in objective
- [ ] Update cross-market constraints
- [ ] **CRITICAL TEST:** DE, 0.5C, 2.0 must solve
- [ ] Verify revenue higher, net profit accounts for degradation

#### Day 4-6 (Nov 4-6): Scenarios & Analysis
- [ ] Create `run_phase2_scenarios.py`
- [ ] Run 45 scenarios (background process)
- [ ] Handle failed scenarios
- [ ] Analyze results (best configs, degradation impact)
- [ ] Update investment analysis with NPV across all 5 countries

#### Day 7-9 (Nov 7-9): Documentation & Dashboard
- [ ] Create master results notebook
- [ ] Generate all visualizations
- [ ] Build interactive web dashboard (Plotly Dash, 3 tabs)
- [ ] Integrate existing McKinsey-style plot functions
- [ ] Write 15-page technical report
- [ ] Prepare submission CSVs
- [ ] Package code with documentation and dashboard
- [ ] Final validation & submission

---

## 10. Key Contacts & Resources

### Official Resources
- **Phase 2 Q&A:** [Google Doc](https://docs.google.com/document/d/1NHbycnyq_boqihHSY8Gw4GtrUCdVqaBkwO1my5SLUsY/edit)
- **PICASSO 4-sec Data:** https://www.transnetbw.de/en/energy-market/ancillary-services/picasso (DESCOPED)
- **Phase 2 Slides:** `doc/official_instruction_docs/round2_intro_slides.md`

### Key Literature
1. **Collath et al. (2023):** "Increasing the lifetime profitability of battery energy storage systems through aging aware operation" - Applied Energy 348, 121531
   - Focus: Calendar aging model (Section 2.2)
2. **Xu et al. (2017):** "Factoring the Cycle Aging Cost of Batteries Participating in Electricity Markets" - arXiv:1707.04567v2
   - Focus: Piecewise-linear cyclic aging (Section III)
3. **ORC Battery Degradation Model:** Official competition documentation (if available)

### Internal Documentation
- `doc/whole_project_description.md` - Complete project overview
- `doc/gg_dp_p2_model.tex/p2_model_ggdp.tex` - Phase 2 mathematical model
- `doc/dev_summary/Phase2_implementation_summary.md` - Oct 26 infrastructure work
- `doc/dev_plan/data_result_dashboard.md` - Original dashboard specs

---

## Conclusion & Immediate Next Steps

### Honest Post-Week 1 Assessment

**What Went Right:**
- Phase 1 model is production-grade (comprehensive validation)
- Phase 2 is fully designed mathematically
- Visualization infrastructure is ready to use
- Foundation is solid - no technical debt

**What Went Wrong:**
- Zero implementation progress on degradation (30% of grade)
- Zero implementation on Phase 2 optimization
- Web dashboard doesn't exist (only backend functions)

**Critical Insight:** You chose quality over quantity in Week 1. This was defensible but creates intense Week 2 pressure.

### The Path Forward (9 Days)

**Ambitious but Achievable IF:**
1. You work focused 8-hour days
2. You leverage existing work (validation plots, viz functions, Phase 1 code)
3. You prioritize efficiently (degradation model first, then scenarios)
4. You use parallel processing for scenario runs

**Non-Negotiables:**
- Degradation model must work (30% of grade)
- aFRR energy must be integrated (part of 30% revenue grade)
- 45 scenarios across all 5 countries must complete
- Interactive web dashboard for strong code quality score
- Professional technical report

**Smart Simplifications:**
- 5 SOC segments (not 10) for degradation modeling
- Temperature effects marked [?] - optional if time permits
- Accept 3-5% MIP gap for solver efficiency
- Leverage existing visualization infrastructure

### Immediate Actions (Next 2 Hours Before Demo)

1. **Prepare Demo Materials (90 minutes):**
   - Create notebook showing Phase 1 validation plots
   - Add markdown explaining Phase 2 design (embed LaTeX equations as images)
   - Show View 1 visualizations (use Oct 26 test notebook)
   - Add "Week 2 Sprint Plan" section with revised timeline

2. **Prepare Talking Points (30 minutes):**
   - "Week 1 focused on foundation: validated Phase 1, designed Phase 2, built viz infrastructure"
   - "Trade-off: Depth over breadth - ensuring correctness before extension"
   - "Week 2: Pure execution mode - implementation, scenarios, documentation"
   - "Realistic target: 80% overall score (competitive), not 87% (unrealistic)"

### After Demo

- **Today (Oct 31 evening):** Rest and prepare mentally
- **Tomorrow (Nov 1):** START DAY 1 IMMEDIATELY - degradation model is critical path
- **Daily check-ins:** Review progress against checklist above
- **Decision point Nov 3 evening:** If model doesn't solve, implement contingency (soft constraints instead of hard degradation costs)

---

**You can do this.** The math is done. The foundation is validated. The infrastructure exists. Now it's focused execution with clear deliverables.

**Remember:** 85% is a strong grade. Work smart with existing infrastructure. Execute efficiently. 🚀

---

**Document Version:** 2.0 - Post-Week 1 Reality Check
**Previous Version:** 1.0 (Oct 25) - Original optimistic plan
**Last Updated:** October 31, 2025
**Next Review:** After implementation milestone (Nov 3 evening) or if major blocker occurs
**Author:** Gen Li (Team SoloGen) with Claude Code assistance

---

**END OF REVISED PLAN**
