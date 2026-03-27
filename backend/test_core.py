"""
Tests unitarios para VigilaChile — validacion de calculos criticos.
Ejecutar con: pytest test_core.py -v
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from risk import calculate_risk
from regions import calculate_region_risk
from datetime import datetime, timezone, timedelta


def _make_quake(magnitude, hours_ago=1, lat=-33.5, lon=-70.5, place="Test"):
    t = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
    return {
        "magnitude": magnitude,
        "lat": lat,
        "lon": lon,
        "depth": 30,
        "place": place,
        "time": t.strftime("%Y-%m-%d %H:%M:%S")
    }


def _make_fire(lat=-33.5, lon=-70.5, frp=10.0):
    return {"lat": lat, "lon": lon, "brightness": 350, "date": "2026-03-26", "confidence": "80", "frp": frp, "satellite": "NOAA-20", "instrument": "VIIRS", "resolution": "375m"}


# =====================================================================
# RISK CALCULATION TESTS
# =====================================================================

class TestRiskCalculation:
    def test_no_data_returns_low_risk(self):
        result = calculate_risk([], [])
        assert result["score"] >= 1
        assert result["score"] <= 3
        assert result["level"] in ("Bajo", "Moderado-Bajo")

    def test_normal_chile_activity_is_low(self):
        """20-30 sismos M2.5-3.5 diarios es NORMAL para Chile."""
        quakes = [_make_quake(3.0, hours_ago=i) for i in range(25)]
        result = calculate_risk(quakes, [])
        assert result["score"] <= 4, f"25 sismos M3.0 should be low risk, got {result['score']}"
        assert "Bajo" in result["level"] or "Moderado" in result["level"]

    def test_m6_earthquake_raises_risk(self):
        quakes = [_make_quake(6.2, hours_ago=1)]
        result = calculate_risk(quakes, [])
        assert result["score"] >= 4, f"M6.2 should raise risk, got {result['score']}"

    def test_m7_plus_is_critical(self):
        quakes = [_make_quake(7.8, hours_ago=0.5)]
        result = calculate_risk(quakes, [])
        assert result["score"] >= 7, f"M7.8 should be high/critical, got {result['score']}"

    def test_fires_add_to_risk(self):
        quakes = [_make_quake(3.0)]
        no_fires = calculate_risk(quakes, [])
        fires = [_make_fire() for _ in range(5)]
        with_fires = calculate_risk(quakes, fires)
        assert with_fires["score"] >= no_fires["score"], "Fires should increase risk"

    def test_frp_weighting(self):
        """High FRP fires should contribute more to risk than low FRP fires"""
        quakes = [_make_quake(3.0)]
        low_frp = calculate_risk(quakes, [_make_fire(frp=1) for _ in range(10)])
        high_frp = calculate_risk(quakes, [_make_fire(frp=50) for _ in range(3)])
        assert high_frp["score"] >= low_frp["score"], \
            f"3 fires FRP=50MW ({high_frp['score']}) should >= 10 fires FRP=1MW ({low_frp['score']})"

    def test_risk_has_required_fields(self):
        result = calculate_risk([_make_quake(4.0)], [])
        assert "score" in result
        assert "level" in result
        assert "color" in result
        assert "description" in result
        assert "recent_quakes" in result
        assert "active_fires" in result
        assert "max_magnitude" in result

    def test_risk_score_bounded_1_10(self):
        """Risk score should always be between 1 and 10."""
        # Extreme case: many large earthquakes + fires
        quakes = [_make_quake(7.0, hours_ago=i * 0.5) for i in range(20)]
        fires = [_make_fire() for _ in range(50)]
        result = calculate_risk(quakes, fires)
        assert 1 <= result["score"] <= 10, f"Score out of bounds: {result['score']}"

    def test_risk_color_format(self):
        result = calculate_risk([_make_quake(5.5)], [])
        assert result["color"].startswith("#"), f"Color should be hex: {result['color']}"


# =====================================================================
# REGION RISK TESTS
# =====================================================================

class TestRegionRisk:
    def test_returns_all_regions(self):
        result = calculate_region_risk([], [])
        assert result["count"] == 16, f"Expected 16 regions, got {result['count']}"

    def test_region_has_required_fields(self):
        quakes = [_make_quake(4.0, lat=-33.5, lon=-70.5)]
        result = calculate_region_risk(quakes, [])
        for r in result["data"]:
            assert "id" in r
            assert "name" in r
            assert "level" in r
            assert "color" in r
            assert "quakes_24h" in r
            assert "max_magnitude" in r
            assert "population" in r

    def test_metropolitana_detects_nearby_quake(self):
        """A quake at -33.5, -70.5 should be detected by Metropolitana region."""
        quakes = [_make_quake(5.0, lat=-33.5, lon=-70.5)]
        result = calculate_region_risk(quakes, [])
        metro = next(r for r in result["data"] if r["id"] == "metropolitana")
        assert metro["quakes_24h"] >= 1, "Metropolitana should detect nearby quake"
        assert metro["max_magnitude"] >= 5.0

    def test_no_quakes_all_green(self):
        result = calculate_region_risk([], [])
        for r in result["data"]:
            assert r["level"] in ("VERDE", "SIN ACTIVIDAD"), f"{r['name']} should be green, got {r['level']}"

    def test_arica_region_exists(self):
        """Arica y Parinacota (XVI region) must be present."""
        result = calculate_region_risk([], [])
        ids = [r["id"] for r in result["data"]]
        assert "arica" in ids, "Arica y Parinacota region missing"

    def test_tsunami_risk_only_coastal_m65(self):
        """Tsunami risk should only be True for coastal regions with M>=6.5."""
        quakes = [_make_quake(6.8, lat=-33.0, lon=-71.3)]  # Near Valparaiso coast
        result = calculate_region_risk(quakes, [])
        valpo = next(r for r in result["data"] if r["id"] == "valparaiso")
        metro = next(r for r in result["data"] if r["id"] == "metropolitana")
        # Valparaiso is coastal, Metropolitana is not
        assert metro["tsunami_risk"] is False, "Non-coastal region shouldn't have tsunami risk"


# =====================================================================
# VOLCANO DATA TESTS
# =====================================================================

class TestVolcanoes:
    def test_returns_data(self):
        from volcanoes import get_volcanoes
        result = get_volcanoes()
        assert result["count"] >= 40, f"Expected 40+ volcanoes, got {result['count']}"
        assert "data" in result
        assert "source" in result

    def test_villarrica_is_rank_1(self):
        from volcanoes import VOLCANOES_DB
        villarrica = next(v for v in VOLCANOES_DB if v["name"] == "Villarrica")
        assert villarrica["risk_rank"] == 1, "Villarrica should be rank 1"
        assert villarrica["alert"] != "Verde", "Villarrica should not be Verde"

    def test_all_volcanoes_have_coordinates(self):
        from volcanoes import VOLCANOES_DB
        for v in VOLCANOES_DB:
            assert -56 <= v["lat"] <= -17, f"{v['name']} lat out of Chile: {v['lat']}"
            assert -76 <= v["lon"] <= -66, f"{v['name']} lon out of Chile: {v['lon']}"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
