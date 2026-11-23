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
| 14 | Missing weather data | `test_risk_engine.py`, `test_recommendation.py`, `test_heatmap.py` | Missing data classified as `Data Unavailable` (never Low). Routes with missing forecasts cannot be certified safe (`is_safe_for_travel=False`, clearance withheld). |
| 15 | Routing failure & simulated fallback | `test_routing_provider.py` | Verified road routes return `is_simulated=False`. Fallback returns `is_simulated=True`, unverified road warning. Raises error by default unless fallback explicitly enabled. |
| 16 | Dynamic Timeline & Slider Offsets | `test_heatmap.py` | Slider offsets relative to departure time ($T_{\text{dep}} + H$). Dynamic risk recalculation per checkpoint and dynamic heatmap segments. |
| 17 | Timezone handling & instant matching | `test_arrival_time.py` | Timezone-aware ISO strings, browser offset minutes, and UTC instant matching with Open-Meteo. |

---

## 3. Running Backend Tests

Navigate to `backend/` and execute `pytest`:

```bash
cd backend
pytest -v
```

Actual output:
```text
============================= test session starts =============================
platform win32 -- Python 3.14.5, pytest-9.2.0, pluggy-1.7.0
rootdir: C:\weather-aware-truck-routing\backend
plugins: django-4.14.0
collected 55 items

routing/tests/test_api_endpoints.py .......                              [ 12%]
routing/tests/test_arrival_time.py .....                                 [ 21%]
routing/tests/test_checkpoint_generator.py .....                         [ 30%]
routing/tests/test_heatmap.py ..                                         [ 34%]
routing/tests/test_recommendation.py ........                            [ 49%]
routing/tests/test_risk_engine.py .........................              [ 94%]
routing/tests/test_routing_provider.py ...                               [100%]

============================== 55 passed in 1.17s ==============================
```

---

## 4. Running Frontend Tests

Navigate to `frontend/` and execute `npm test`:

```bash
cd frontend
npm test
```

Actual output:
```text
 RUN  v5.1.1 C:/weather-aware-truck-routing/frontend

 ✓ src/test/RecommendationBanner.test.tsx (3 tests)
 ✓ src/test/RouteComparison.test.tsx (2 tests)
 ✓ src/test/ForecastSlider.test.tsx (2 tests)
 ✓ src/test/RouteForm.test.tsx (4 tests)
 ✓ src/test/CheckpointTable.test.tsx (3 tests)

 Test Files  5 passed (5)
      Tests  14 passed (14)
   Duration  2.33s
```

---

## 5. Total Test Suite Summary

- **Backend Automated Tests:** 55 passed
- **Frontend Automated Tests:** 14 passed
- **Combined Test Count:** 69 automated tests passing with 100% success rate.
