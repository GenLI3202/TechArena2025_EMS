After a detailed review of the optimizer.py file, we have identified two critical bugs that must be fixed. These bugs are preventing the MPC (rolling horizon) simulation from functioning correctly and are causing incorrect economic calculations for the aFRR energy market.

Please implement the following two fixes:

Task 1: Fix the MPC State Propagation Bug
Problem: The MPCSimulator (in mpc_simulator.py) correctly calculates the final SOC at the end of an execution block. However, when it passes this new state back to the BESSOptimizer for the next iteration, the build_optimization_model function in BESSOptimizerModelI ignores it.

The model is hard-coded to always read the default initial_soc (e.g., 0.5) when setting the model.E_soc_init parameter, completely breaking the state-passing logic of the MPC loop.

Solution: Modify BESSOptimizerModelI.build_optimization_model (around line 382) to dynamically read the initial SOC value. This value will be set externally by the MPCSimulator.

In optimizer.py, find the build_optimization_model method within the BESSOptimizerModelI class.

Locate the model.E_soc_init parameter definition (around line 382).

Modify its initialize logic to first check for an externally-set value (e.g., initial_soc_kwh) from self.battery_params. If that key doesn't exist, it should fall back to the default value.

Implementation (around lines 382-387):

Python
```python
# [Original Code from optimizer.py]
# model.E_soc_init = pyo.Param(initialize=self.battery_params['initial_soc'] * self.battery_params['capacity_kwh'],
#                                     doc="Initial SOC energy (kWh)")

# [NEW CODE to implement]
# FIX: Prioritize 'initial_soc_kwh' (set by MPC) and fall back to 'initial_soc' (default)
default_init_soc_kwh = self.battery_params['initial_soc'] * self.battery_params['capacity_kwh']
current_init_soc_kwh = self.battery_params.get('initial_soc_kwh', default_init_soc_kwh)

model.E_soc_init = pyo.Param(
    initialize=current_init_soc_kwh,
    doc="Initial SOC energy (kWh) [Dynamically set by MPC simulator]"
)
```
This ensures the MPCSimulator's updated SOC is correctly used in the next simulation step.