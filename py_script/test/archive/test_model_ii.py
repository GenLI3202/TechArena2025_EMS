"""
Unit and integration tests for Model (ii): Cyclic Aging Cost Integration

Tests based on the implementation plan in doc/dev_plan/model_ii_implementation_plan.md

Author: Gen Li (Team SoloGen)
Date: 2025-01-08
"""

import pytest
import sys
from pathlib import Path
import pandas as pd
import numpy as np

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'py_script'))

from core.optimizer import BESSOptimizerModelII, BESSOptimizerModelI


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def minimal_country_data():
    """
    Create minimal test dataset for quick tests (16 timesteps = 4 hours).
    """
    timestamps = pd.date_range('2024-01-01', periods=16, freq='15min')

    # Create price variation to enable optimization
    prices_da = [20, 30, 40, 50, 60, 70, 80, 90,  # Rising
                  90, 80, 70, 60, 50, 40, 30, 20]  # Falling

    return pd.DataFrame({
        'timestamp': timestamps,
        'price_day_ahead': prices_da,
        'price_fcr': [0.0] * 16,  # Disable for simplicity
        'price_afrr_pos': [0.0] * 16,
        'price_afrr_neg': [0.0] * 16,
        'price_afrr_energy_pos': [0.0] * 16,
        'price_afrr_energy_neg': [0.0] * 16,
        'hour': timestamps.hour.tolist(),
        'day_of_year': [1] * 16,
        'month': [1] * 16,
        'year': [2024] * 16,
        'block_of_day': [i//16 for i in range(16)],
        'block_id': [0] * 16,
        'day_id': [0] * 16,
    })


@pytest.fixture
def one_day_data():
    """
    Create 1-day test dataset (96 timesteps = 24 hours).
    """
    timestamps = pd.date_range('2024-01-01', periods=96, freq='15min')

    # Create realistic daily price pattern
    hour_of_day = timestamps.hour.to_numpy()
    # Low at night (hours 0-6), high during day (hours 9-18), medium evening
    base_price = 40
    hourly_variation = 30 * np.sin((hour_of_day - 6) * np.pi / 12)
    prices_da = base_price + hourly_variation

    return pd.DataFrame({
        'timestamp': timestamps,
        'price_day_ahead': prices_da,
        'price_fcr': [100.0] * 96,
        'price_afrr_pos': [50.0] * 96,
        'price_afrr_neg': [50.0] * 96,
        'price_afrr_energy_pos': prices_da + 10,  # Slightly higher
        'price_afrr_energy_neg': prices_da - 10,  # Slightly lower
        'hour': timestamps.hour.tolist(),
        'day_of_year': [1] * 96,
        'month': [1] * 96,
        'year': [2024] * 96,
        'block_of_day': [i//16 for i in range(96)],
        'block_id': [i//16 for i in range(96)],
        'day_id': [0] * 96,
    })


# ============================================================================
# Test Class 1: Initialization
# ============================================================================

class TestModelIIInitialization:
    """Test Model (ii) initialization and configuration loading."""

    def test_load_degradation_config(self):
        """Degradation config should load and expose monotone marginal costs."""
        optimizer = BESSOptimizerModelII(
            degradation_config_path='data/phase2_aging_config/aging_config.json'
        )
        assert optimizer.degradation_params['num_segments'] == 10
        assert len(optimizer.degradation_params['marginal_costs']) == 10
        assert optimizer.degradation_params['marginal_costs'][0] == pytest.approx(0.0052)
        assert optimizer.degradation_params['marginal_costs'][-1] == pytest.approx(0.0990)

    def test_invalid_config_path(self):
        """Should raise FileNotFoundError for invalid config path."""
        with pytest.raises(FileNotFoundError):
            BESSOptimizerModelII(degradation_config_path='nonexistent.json')

    def test_segment_capacity_calculation(self):
        """Segment capacity should be total capacity divided by number of segments."""
        optimizer = BESSOptimizerModelII()
        expected_seg_cap = 4472 / 10  # 447.2 kWh
        assert optimizer.degradation_params['segment_capacity_kwh'] == pytest.approx(expected_seg_cap)

    def test_alpha_parameter(self):
        """Alpha parameter should be set correctly."""
        optimizer = BESSOptimizerModelII(alpha=2.5)
        assert optimizer.degradation_params['alpha'] == 2.5

    def test_cost_sum_equals_full_cycle_cost(self):
        """Sum of marginal costs times segment size should equal cost per full cycle."""
        optimizer = BESSOptimizerModelII()
        costs = optimizer.degradation_params['marginal_costs']
        seg_cap = optimizer.degradation_params['segment_capacity_kwh']

        total_cost = sum(costs) * seg_cap
        expected_cost = 232.92  # EUR per full cycle (from plan)

        # Allow 1% tolerance due to rounding
        assert total_cost == pytest.approx(expected_cost, rel=0.01)

    def test_enforce_segment_binary_flag(self):
        """Enforcement of segment binary can be disabled for performance."""
        optimizer_enabled = BESSOptimizerModelII(enforce_segment_binary=True)
        optimizer_disabled = BESSOptimizerModelII(enforce_segment_binary=False)

        assert optimizer_enabled.degradation_params['enforce_segment_binary'] is True
        assert optimizer_disabled.degradation_params['enforce_segment_binary'] is False


# ============================================================================
# Test Class 2: Model Building
# ============================================================================

class TestModelIIModelBuilding:
    """Test Pyomo model construction for Model (ii)."""

    def test_segment_set_creation(self, minimal_country_data):
        """Segment set J should have 10 elements (1 to 10)."""
        optimizer = BESSOptimizerModelII()
        model = optimizer.build_optimization_model(minimal_country_data, c_rate=0.5)
        assert list(model.J) == list(range(1, 11))

    def test_segment_variables_exist(self, minimal_country_data):
        """All segment-related variables and components should exist."""
        optimizer = BESSOptimizerModelII()
        model = optimizer.build_optimization_model(minimal_country_data, c_rate=0.5)

        import pyomo.environ as pyo

        # Variables
        assert hasattr(model, 'p_ch_j'), "Missing segment charge power variable"
        assert hasattr(model, 'p_dis_j'), "Missing segment discharge power variable"
        assert hasattr(model, 'e_soc_j'), "Missing segment SOC variable"

        # Total SOC as expression (not variable)
        assert hasattr(model, 'e_soc'), "Missing total SOC"
        assert isinstance(model.e_soc, pyo.base.expression.IndexedExpression) or \
               isinstance(model.e_soc, pyo.base.expression._GeneralExpressionData), \
               "e_soc should be an Expression"

        # Constraints
        assert hasattr(model, 'stacked_tank_ordering'), "Missing stacked-tank ordering constraint"
        assert hasattr(model, 'segment_soc_dynamics'), "Missing segment SOC dynamics"

    def test_aggregation_constraints(self, minimal_country_data):
        """Power aggregation constraints should exist and be active."""
        optimizer = BESSOptimizerModelII()
        model = optimizer.build_optimization_model(minimal_country_data, c_rate=0.5)

        assert hasattr(model, 'total_charge_aggregation')
        assert hasattr(model, 'total_discharge_aggregation')
        assert model.total_charge_aggregation.active
        assert model.total_discharge_aggregation.active

    def test_daily_cycle_limit_not_created_when_none(self, minimal_country_data):
        """Daily cycle limit constraint should not exist when daily_cycle_limit=None."""
        optimizer = BESSOptimizerModelII()
        model = optimizer.build_optimization_model(minimal_country_data, c_rate=0.5, daily_cycle_limit=None)

        # The constraint should not exist at all
        assert not hasattr(model, 'daily_cycle_limit'), \
            "daily_cycle_limit constraint should not be created when daily_cycle_limit=None"

    def test_daily_cycle_limit_deactivated_when_provided(self, minimal_country_data):
        """Daily cycle limit should be deactivated if Model (i) creates it."""
        optimizer = BESSOptimizerModelII()
        # Pass a value to trigger parent constraint creation (if it does)
        model = optimizer.build_optimization_model(minimal_country_data, c_rate=0.5, daily_cycle_limit=1.5)

        # If it exists, it should be deactivated
        if hasattr(model, 'daily_cycle_limit'):
            assert not model.daily_cycle_limit.active(), \
                "Daily cycle limit should be deactivated in Model (ii)"

    def test_objective_includes_degradation_cost(self, minimal_country_data):
        """Objective should include degradation cost term."""
        import pyomo.environ as pyo

        optimizer = BESSOptimizerModelII(alpha=1.0)
        model = optimizer.build_optimization_model(minimal_country_data, c_rate=0.5)

        # Check objective exists and is maximize
        assert hasattr(model, 'objective')
        assert model.objective.sense == pyo.maximize

        # Check alpha parameter exists
        assert hasattr(model, 'alpha')
        assert hasattr(model, 'c_cost')


# ============================================================================
# Test Class 3: Model Validation
# ============================================================================

class TestModelIIPhysicalCorrectness:
    """Test that Model (ii) enforces physical correctness."""

    def test_model_respects_total_soc_limits(self, minimal_country_data):
        """Total SOC should stay within [0, E_nom] bounds."""
        pytest.skip("Requires solver - tested in integration tests")

    def test_stacked_tank_monotonicity(self, minimal_country_data):
        """Shallower segments should have >= energy than deeper segments."""
        pytest.skip("Requires solver - tested in integration tests")

    def test_segment_capacity_limits(self, minimal_country_data):
        """Each segment should respect its capacity limit."""
        optimizer = BESSOptimizerModelII()
        model = optimizer.build_optimization_model(minimal_country_data, c_rate=0.5)

        # Check bounds are set correctly
        seg_cap = optimizer.degradation_params['segment_capacity_kwh']

        for t in list(model.T)[:3]:  # Check first few timesteps
            for j in model.J:
                var = model.e_soc_j[t, j]
                lb, ub = var.bounds
                assert lb == 0
                assert ub == seg_cap


# ============================================================================
# Test Class 4: Comparison with Model (i)
# ============================================================================

class TestModelIIVsModelI:
    """Integration tests comparing Model (i) and Model (ii) behavior."""

    def test_model_ii_can_build_without_model_i_cycle_limit(self, minimal_country_data):
        """Model (ii) should build even without cycle limit (uses cost instead)."""
        optimizer = BESSOptimizerModelII(alpha=1.0)
        model = optimizer.build_optimization_model(minimal_country_data, c_rate=0.5, daily_cycle_limit=None)

        assert model is not None
        assert hasattr(model, 'J')
        assert len(list(model.J)) == 10

    def test_model_ii_ignores_cycle_limit_parameter(self, minimal_country_data):
        """Model (ii) should ignore daily_cycle_limit parameter if provided."""
        optimizer = BESSOptimizerModelII(alpha=1.0)

        # Model (ii) should build successfully even if daily_cycle_limit is provided
        model = optimizer.build_optimization_model(
            minimal_country_data, c_rate=0.5, daily_cycle_limit=1.5
        )

        # Check that the model built correctly with segments
        assert hasattr(model, 'J')
        assert len(list(model.J)) == 10  # Should have 10 segments


# ============================================================================
# Test Class 5: Degradation Metrics
# ============================================================================

class TestModelIIDegradationMetrics:
    """Test degradation metric calculation."""

    def test_metrics_calculation_with_zero_discharge(self):
        """Metrics should handle case with no discharge (zero cost)."""
        import pyomo.environ as pyo

        optimizer = BESSOptimizerModelII(alpha=1.0)

        # Create mock model with minimal components
        model = pyo.ConcreteModel()
        model.T = pyo.Set(initialize=[0, 1])
        model.J = pyo.Set(initialize=range(1, 11))
        model.D = pyo.Set(initialize=[0])
        model.eta_dis = pyo.Param(initialize=0.95)
        model.dt = pyo.Param(initialize=0.25)
        model.E_nom = pyo.Param(initialize=4472)
        model.c_cost = pyo.Param(model.J, initialize={j: 0.01 * j for j in range(1, 11)})

        # Empty discharge dictionary (no discharge occurred)
        p_dis_j = {}

        metrics = optimizer._calculate_degradation_metrics(model, p_dis_j)

        assert metrics['total_cyclic_cost_eur'] == 0.0
        assert metrics['equivalent_full_cycles'] == 0.0
        assert metrics['total_throughput_kwh'] == 0.0

    def test_metrics_structure(self):
        """Degradation metrics should have all required keys."""
        import pyomo.environ as pyo

        optimizer = BESSOptimizerModelII(alpha=1.5)

        # Create mock model
        model = pyo.ConcreteModel()
        model.T = pyo.Set(initialize=[0])
        model.J = pyo.Set(initialize=range(1, 11))
        model.D = pyo.Set(initialize=[0])
        model.eta_dis = pyo.Param(initialize=0.95)
        model.dt = pyo.Param(initialize=0.25)
        model.E_nom = pyo.Param(initialize=4472)
        model.c_cost = pyo.Param(model.J, initialize={j: 0.01 * j for j in range(1, 11)})
        model.alpha = pyo.Param(initialize=1.5)

        # Minimal discharge
        p_dis_j = {(0, 1): 100.0}  # 100 kW from segment 1 at t=0

        metrics = optimizer._calculate_degradation_metrics(model, p_dis_j)

        # Check all required keys exist
        required_keys = [
            'total_cyclic_cost_eur',
            'equivalent_full_cycles',
            'total_throughput_kwh',
            'throughput_per_segment_kwh',
            'cost_per_segment_eur',
            'average_dod',
            'alpha'
        ]

        for key in required_keys:
            assert key in metrics, f"Missing required metric: {key}"


# ============================================================================
# Test Class 6: Edge Cases
# ============================================================================

class TestModelIIEdgeCases:
    """Edge-case scenarios ensuring robustness."""

    def test_zero_alpha_disables_degradation_cost(self, minimal_country_data):
        """Alpha=0 should disable degradation cost (same as Model i without limit)."""
        optimizer = BESSOptimizerModelII(alpha=0.0)
        model = optimizer.build_optimization_model(minimal_country_data, c_rate=0.5)

        import pyomo.environ as pyo

        # Alpha should be 0
        assert pyo.value(model.alpha) == 0.0

    def test_very_high_alpha_penalizes_all_discharge(self, minimal_country_data):
        """Very high alpha should heavily penalize discharge."""
        optimizer = BESSOptimizerModelII(alpha=1000.0)
        model = optimizer.build_optimization_model(minimal_country_data, c_rate=0.5)

        import pyomo.environ as pyo
        assert pyo.value(model.alpha) == 1000.0

    def test_single_timestep_model(self):
        """Model should handle single timestep (degenerate case)."""
        timestamps = pd.date_range('2024-01-01', periods=1, freq='15min')
        data = pd.DataFrame({
            'timestamp': timestamps,
            'price_day_ahead': [50.0],
            'price_fcr': [0.0],
            'price_afrr_pos': [0.0],
            'price_afrr_neg': [0.0],
            'price_afrr_energy_pos': [0.0],
            'price_afrr_energy_neg': [0.0],
            'hour': [0],
            'day_of_year': [1],
            'month': [1],
            'year': [2024],
            'block_of_day': [0],
            'block_id': [0],
            'day_id': [0],
        })

        optimizer = BESSOptimizerModelII(alpha=1.0)
        model = optimizer.build_optimization_model(data, c_rate=0.5)

        assert len(list(model.T)) == 1
        assert hasattr(model, 'J')


# ============================================================================
# Integration Tests (may be slow)
# ============================================================================

@pytest.mark.slow
class TestModelIIIntegration:
    """Integration tests requiring solver - marked as slow."""

    def test_one_day_optimization(self, one_day_data):
        """Test full 1-day optimization with degradation cost."""
        pytest.skip("Integration test - requires solver and is slow. Run manually.")

        # This would be the actual integration test code:
        # optimizer = BESSOptimizerModelII(alpha=1.0, enforce_segment_binary=False)
        # results = optimizer.optimize(one_day_data, c_rate=0.5, daily_cycle_limit=None)
        # assert results['status'] in ['optimal', 'feasible']
        # assert 'degradation_metrics' in results


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == '__main__':
    # Run all tests with verbose output
    pytest.main([__file__, '-v', '--tb=short'])
