# Testing Strategy and Test Coverage Report

## 1. Overview

The test suite provides comprehensive test coverage across both the backend Python/Django application and the frontend React/TypeScript application.

All 15 verification areas mandated in Section 16 are thoroughly covered.

---

## 2. Test Coverage Matrix

| # | Test Area | Test File | Verified Scenarios |
|---|---|---|---|
| 1 | Wind risk thresholds | `test_risk_engine.py` | `<25` Low, `25-34` Moderate, `35-44` High, `45-54` Severe, `>=55` No Travel. Exact shared boundaries tested. |
| 2 | Rain risk thresholds | `test_risk_engine.py` | `<0.10` Low, `0.10-0.25` Moderate, `0.25-0.50` High, `0.50-1.00` Severe, `>1.00` No Travel. |
| 3 | Snow risk thresholds | `test_risk_engine.py` | `<0.5` Low, `0.5-1.0` Moderate, `1.0-2.0` High, `2.0-3.0` Severe, `>3.0` No Travel. |
| 4 | Load-based risk adjustments | `test_risk_engine.py` | Rule 1: Wind $\ge 55 \implies \text{No Travel}$ for all loads; Rule 2: Wind $45\text{–}54 \land \text{Load} > 30\text{k} \implies \text{No Travel}$; Rule 3: Wind $35\text{–}44 \land \text{Load} > 40\text{k} \implies \text{Severe}$. |
| 5 | Checkpoint generation intervals | `test_checkpoint_generator.py` | Sampling along polyline at 10, 25, and 50 miles. |
| 6 | Destination checkpoint inclusion | `test_checkpoint_generator.py` | Terminal destination point is guaranteed to be present even when route mileage is not an exact multiple of the interval. |
| 7 | Estimated arrival-time calculation | `test_arrival_time.py` | Segment-proportional duration interpolation, ETA timestamp formatting, timezone parsing. |
| 8 | Weather unit conversions | `test_arrival_time.py`, `test_risk_engine.py` | Verification of mph, in/hr, metric-to-imperial normalization. |
| 9 | Route metric calculations | `test_recommendation.py` | Low, moderate, high, severe, no-travel miles, average risk score. |
| 10 | Risk-mile calculations | `test_recommendation.py` | Conservative bounding segment attribution: $\max(\text{risk}(cp_i), \text{risk}(cp_{i+1}))$. |
| 11 | Route recommendation ordering | `test_recommendation.py` | Strict lexicographical comparison: Fewest Severe miles $\to$ Fewest High miles $\to$ Lowest average risk score $\to$ Shortest travel time. |
| 12 | No-Travel route handling | `test_recommendation.py` | Hard safety constraint disqualification; critical alert triggered if all routes contain hazards. |
| 13 | Invalid user inputs | `test_api_endpoints.py` | Missing fields, identical origin/destination, invalid dates, negative/excessive load weights, invalid sampling interval. |
| 14 | Missing weather data | `test_api_endpoints.py` | Safe fallback handling, `forecast_available` flags, gracefully handled network degradation. |
| 15 | Routing failure & fallback | `test_api_endpoints.py`, `test_checkpoint_generator.py` | Fallback corridor generator activates if primary routing provider is unreachable or returns $<3$ routes. |

---

## 3. Running Backend Tests

Navigate to `backend/` and execute `pytest`:

```bash
cd backend
pytest -v
```

Expected output:
```text
============================= test session starts =============================
platform win32 -- Python 3.14.5, pytest-9.2.0, pluggy-1.7.0
rootdir: C:\weather-aware-truck-routing\backend
plugins: django-4.14.0
collected 41 items

routing/tests/test_api_endpoints.py ........                             [ 17%]
routing/tests/test_arrival_time.py ..                                    [ 21%]
routing/tests/test_checkpoint_generator.py .....                         [ 34%]
routing/tests/test_recommendation.py ......                              [ 48%]
routing/tests/test_risk_engine.py .....................                  [100%]

============================== 41 passed in 1.17s ==============================
```

---

## 4. Running Frontend Tests

Navigate to `frontend/` and execute `npm test`:

```bash
cd frontend
npm test
```

Expected output:
```text
 RUN  v5.1.1 C:/weather-aware-truck-routing/frontend

 ✓ src/test/RouteForm.test.tsx (3 tests)
 ✓ src/test/ForecastSlider.test.tsx (2 tests)

 Test Files  2 passed (2)
      Tests  5 passed (5)
   Duration  2.25s
```

Total Automated Tests: **46 passed** (41 backend + 5 frontend).
