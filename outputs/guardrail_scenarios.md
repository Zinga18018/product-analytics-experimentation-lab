# Guardrail stress scenarios

These constructed fixtures test decision behavior. They do not estimate real-world performance.

| Scenario | Eligible users | Conversion difference | Conversion gate | Retention gate | Revenue gate | Sample ratio | Decision |
| --- | ---: | ---: | --- | --- | --- | --- | --- |
| conversion_gain_retention_loss | 1000 | 30.00% | True | False | True | True | hold |
| conversion_gain_revenue_loss | 1000 | 30.00% | True | True | False | True | hold |
| conversion_gain_assignment_mismatch | 1500 | 30.00% | True | True | True | False | hold |
| all_gates_pass | 1000 | 30.00% | True | True | True | True | eligible_for_rollout_review |
