We have identified a critical bug in optimizer.py that is causing incorrect model behavior in our tests.



Symptoms Observed:

aFRR-E Revenue is 0.00: The model is not bidding into the aFRR energy market, even when EV-weighting is turned off.



Objective Function Instability: Toggling the use\_afrr\_ev\_weighting flag causes massive swings in the total objective value (-10% to -56%), even though the aFRR-E revenue remains zero.



Root Cause Analysis:

The bug is a "weight leakage" into a physical constraint.



The EV-weighting parameters (w\_pos\_afrr\_e\[t] and w\_neg\_afrr\_e\[t]) are correctly used in the objective function (objective\_rule) to calculate expected economic revenue.



However, these same weights are incorrectly also being used inside the physical power limit constraint (Cst-4).



Buggy Code in BESSOptimizerModelI.build\_optimization\_model:



Python



\# \[This is the BUGGY code from optimizer.py]

```python

@m.Constraint(m.B, m.T, name="total\\\_discharge\\\_power\\\_limit")

def total\\\_discharge\\\_power\\\_limit\\\_rule(m, b, t):

\&nbsp;   if t in m.t\\\_in\\\_b\\\[b]:

\&nbsp;       # BUG: Multiplying physical power by an economic weight

\&nbsp;       return (m.p\\\_dis\\\[t] + m.w\\\_pos\\\_afrr\\\_e\\\[t] \\\* m.p\\\_afrr\\\_pos\\\_e\\\[t]) + \\\\ 

\&nbsp;              1000 \\\* m.c\\\_fcr\\\[b] + \\\\

\&nbsp;              1000 \\\* m.c\\\_afrr\\\_pos\\\[b] \\\\

\&nbsp;              <= m.p\\\_config\\\_max

```

This bug explains both symptoms:



Explains Symptom 2: When EV-weighting is ON, w\_pos\_afrr\_e\[t] can be very low (e.g., 0.1 or 0). The constraint incorrectly tells the solver that a 10 MW bid only occupies 1 MW (or 0 MW) of physical capacity. This "phantom capacity" completely changes the bidding strategy for all other markets (DA, FCR, aFRR-C), causing the total objective to swing wildly.



Explains Symptom 1: In the objective\_rule, when w\_pos\_afrr\_e\[t] is 0, the model correctly sees the expected revenue as 0 and decides not to bid, resulting in 0 aFRR-E revenue.



Task: Implement the Solution

You must remove the EV-weighting parameters (w\_...) from all physical constraints. A bid for 1 MW must always reserve 1 MW of physical capacity, regardless of its activation probability.



Please modify the following two constraints in BESSOptimizerModelI.build\_optimization\_model to match our technical specification (p2\_bi\_model\_ggdp.tex, Cst-4) :



1\. total\_discharge\_power\_limit\_rule:



Current (Buggy): (m.p\_dis\[t] + m.w\_pos\_afrr\_e\[t] \* m.p\_afrr\_pos\_e\[t]) + ...



FIXED (Correct): (m.p\_dis\[t] + m.p\_afrr\_pos\_e\[t]) + ...



2\. total\_charge\_power\_limit\_rule:



Current (Buggy): (m.p\_ch\[t] + m.w\_neg\_afrr\_e\[t] \* m.p\_afrr\_neg\_e\[t]) + ...



FIXED (Correct): (m.p\_ch\[t] + m.p\_afrr\_neg\_e\[t]) + ...



The EV-weighting parameters must remain in the objective\_rule (lines 629-633), as their economic function there is correct. This fix will ensure they no longer corrupt the model's physical constraints.

