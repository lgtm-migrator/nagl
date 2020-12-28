import pytest
from openeye import oechem

from nagl.utilities.openeye import (
    enumerate_tautomers,
    guess_stereochemistry,
    requires_oe_package,
)
from nagl.utilities.utilities import MissingOptionalDependency


@requires_oe_package("oechem")
def dummy_oe_function():
    return 5


def test_requires_oe_package(monkeypatch):

    monkeypatch.setattr(oechem, "OEChemIsLicensed", lambda: False)

    with pytest.raises(MissingOptionalDependency) as error_info:
        dummy_oe_function()

    assert error_info.value.library_name == "openeye.oechem"
    assert error_info.value.license_issue is True


def test_guess_stereochemistry():

    oe_molecule = oechem.OEMol()
    oechem.OESmilesToMol(oe_molecule, "C(F)(Cl)(Br)")

    assert any(
        entity.IsChiral() and not entity.HasStereoSpecified()
        for entity in [*oe_molecule.GetAtoms(), *oe_molecule.GetBonds()]
    )

    oe_molecule = guess_stereochemistry(oe_molecule)

    assert not any(
        entity.IsChiral() and not entity.HasStereoSpecified()
        for entity in [*oe_molecule.GetAtoms(), *oe_molecule.GetBonds()]
    )


def test_enumerate_tautomers():
    oe_molecule = oechem.OEMol()
    oechem.OESmilesToMol(oe_molecule, "CC=C(C)O")

    tautomers = enumerate_tautomers(oe_molecule)
    assert len(tautomers) == 2

    assert {oechem.OEMolToSmiles(tautomer) for tautomer in tautomers} == {
        "CCC(=O)C",
        "CC=C(C)O",
    }
