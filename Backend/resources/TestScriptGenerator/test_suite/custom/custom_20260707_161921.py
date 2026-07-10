```python
import pytest

# This test script uses pytest to verify the understanding of the chemical and physical
# changes in sourdough bread baking, focusing on fermentation by wild yeasts and lactic acid bacteria (LAB).
# Since this is a knowledge-based test, the assertions check for expected known facts.

def test_chemical_changes_during_sourdough_baking():
    # Fermentation by wild yeasts primarily produces CO2 and ethanol
    co2_production = True  # Wild yeasts convert sugars to CO2 (leavening) and ethanol (alcohol)
    ethanol_production = True
    assert co2_production, "Wild yeasts should produce CO2 during fermentation"
    assert ethanol_production, "Wild yeasts should produce ethanol during fermentation"

    # LAB produce lactic acid (and sometimes acetic acid), lowering dough pH
    lactic_acid_production = True
    acetic_acid_production = True  # varies based on LAB strain and conditions
    dough_pH_decrease = True
    assert lactic_acid_production, "LAB should produce lactic acid during fermentation"
    assert acetic_acid_production, "LAB may produce acetic acid during fermentation"
    assert dough_pH_decrease, "Fermentation should lower dough pH due to acid production"

    # Breakdown of starches and proteins into simpler molecules by enzymes
    starch_hydrolysis = True  # amylase enzymes break down starch to maltose and glucose
    protein_hydrolysis = True  # proteases break down gluten proteins partially
    assert starch_hydrolysis, "Enzymatic starch breakdown should occur during fermentation"
    assert protein_hydrolysis, "Proteins partially hydrolyzed during fermentation"

def test_physical_changes_during_sourdough_baking():
    # CO2 production causes dough to rise (leavening)
    dough_rise = True
    assert dough_rise, "CO2 production causes dough to rise physically"

    # Heat causes gelatinization of starches (absorbing water, swelling)
    starch_gelatinization = True
    assert starch_gelatinization, "Heat causes starch gelatinization during baking"

    # Maillard reaction between amino acids and reducing sugars produces browning and flavor
    maillard_reaction = True
    assert maillard_reaction, "Maillard reaction occurs during baking, creating crust color and flavor"

    # Denaturation of gluten proteins firms the bread structure
    gluten_denaturation = True
    assert gluten_denaturation, "Heat denatures gluten proteins, stabilizing bread structure"

def test_fermentation_process_of_wild_yeasts_and_lab():
    # Wild yeasts metabolize sugars anaerobically producing CO2 and ethanol
    yeast_metabolism = {
        "substrates": ["glucose", "fructose", "maltose"],
        "products": ["CO2", "ethanol", "heat"]
    }
    assert "CO2" in yeast_metabolism["products"], "Wild yeasts produce CO2"
    assert "ethanol" in yeast_metabolism["products"], "Wild yeasts produce ethanol"

    # LAB metabolize sugars primarily producing lactic acid (homofermentative) or lactic + acetic acid (heterofermentative)
    lab_metabolism = {
        "substrates": ["glucose", "fructose"],
        "products_homofermentative": ["lactic acid"],
        "products_heterofermentative": ["lactic acid", "acetic acid", "CO2", "ethanol"]
    }
    assert "lactic acid" in lab_metabolism["products_homofermentative"], "Homofermentative LAB produce lactic acid"
    assert "acetic acid" in lab_metabolism["products_heterofermentative"], "Heterofermentative LAB produce acetic acid"

def test_overall_effects_on_bread_qualities():
    # Acidification by LAB improves flavor and shelf-life
    acidification_effect = True
    assert acidification_effect, "Acidification improves flavor and shelf-life"

    # CO2 leavens dough, creating porous crumb structure
    crumb_structure = "porous"
    assert crumb_structure == "porous", "CO2 creates porous crumb structure"

    # Heat-induced reactions form crust and develop aroma
    crust_formation = True
    aroma_development = True
    assert crust_formation, "Baking heat forms crust"
    assert aroma_development, "Baking heat develops aroma via Maillard and caramelization"

# Run tests with pytest
if __name__ == "__main__":
    pytest.main([__file__])
```