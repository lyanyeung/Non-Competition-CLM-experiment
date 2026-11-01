"""Fixed site registry for ICOS 38 and AmeriFlux five batches of 10.

ICOS source: CLM-FATES-single-site-workflows/examples/ICOS_sites/ICOS_PFT/
FINAL_38_SITE_FIXNC_PFT_20261025.csv.
AmeriFlux source: examples/Ameriflux_Site/Ameriflux_PFT/metadata/
sites_50_manifest.csv, Git blob 5554992072d95b83ec100562df77289683d2c88c.
This is an inventory, not a claim that cases exist or are complete.
"""
ICOS = ("DE-Tha NL-Loo DE-Hai RU-Fyo DK-Sor IL-Yat CZ-BK1 IT-Ren FR-Hes FR-FBn "
        "DE-Hzd CH-Dav BE-Vie IT-Lav BE-Bra FR-Fon GL-ZaH IT-Noe AT-Neu FI-Sod "
        "CH-Aws CH-Cha CH-Fru CH-Lae CZ-Stn DE-Lnf DE-Obe ES-Agu ES-LJu IT-Col "
        "DE-Gri DE-RuR FI-Hyy FI-Let FR-Pue GF-Guy IT-MBo IT-Tor").split()
ICOS_BATCHES = {
    "Batch01": "DE-Hai RU-Fyo CZ-BK1 IT-Ren CH-Dav BE-Vie FR-Fon FI-Sod IT-Col FR-Pue".split(),
    "Batch02": "DK-Sor FR-Hes FR-FBn BE-Bra IT-Noe CH-Fru CH-Lae ES-LJu FI-Hyy IT-MBo".split(),
    "Batch03": "IL-Yat DE-Hzd IT-Lav AT-Neu CH-Cha CZ-Stn DE-Lnf DE-Obe FI-Let GF-Guy".split(),
    "Example": "DE-Tha NL-Loo".split(),
    "Unassigned": "GL-ZaH CH-Aws ES-Agu DE-Gri DE-RuR IT-Tor".split(),
}
AMERIFLUX = {
    "Batch01": "BR-Ma2 CA-Ca3 CA-Cbo CA-LP1 CA-Man CA-TP1 CA-TP3 CA-TP4 US-Aud US-Bar".split(),
    "Batch02": "US-BZS US-CMW US-EML US-GLE US-Ha1 US-Ho1 US-Ho2 US-Ho3 US-ICh US-ICt".split(),
    "Batch03": "US-Kon US-Me2 US-Me6 US-MMS US-MOz US-Mpj US-MtB US-NC2 US-NR1 US-NR3".split(),
    "Batch04": "US-Rpf US-Seg US-Ses US-Slt US-SP1 US-SRG US-SRM US-Syv US-Ton US-Uaf".split(),
    "Batch05": "US-UiD US-UMB US-UMd US-Var US-Vcm US-Vcp US-WCr US-Whs US-Wjs US-Wkg".split(),
}


def records():
    out = [{"site": site, "network": "ICOS", "batch": batch}
           for batch, sites in ICOS_BATCHES.items() for site in sites]
    out += [{"site": site, "network": "AmeriFlux", "batch": batch}
            for batch, sites in AMERIFLUX.items() for site in sites]
    if len(ICOS) != 38 or any(len(sites) != 10 for sites in AMERIFLUX.values()) or len(out) != 88:
        raise ValueError("Invalid 38+50 site registry")
    if {r["site"] for r in out if r["network"] == "ICOS"} != set(ICOS):
        raise ValueError("ICOS registry does not match source inventory")
    if len({r["site"] for r in out}) != 88:
        raise ValueError("Site registry has duplicates")
    return out

