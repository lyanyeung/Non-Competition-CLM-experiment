#!/usr/bin/env python3
"""READ-ONLY side-by-side comparison of FATES PFT parameters (default: needleleaf 2, broadleaf 6, C3 grass 13).

Works on the JSON parameter file used by CTSM-FATES (fates_params_default.json; layout
{"attributes", "dimensions", "parameters": {name: {"dims", "units", "long_name", "data"}}}).

Writes to --outdir (default ~/FATES_PFT_param_compare_<UTC>):
  pft_params_all.csv          every parameter with a fates_pft dimension, one row per (parameter, sub-index),
                              values for the selected PFTs plus all PFTs, a 'differs' flag and the category
  pft_params_differing.csv    only the rows where the selected PFTs differ
  derived_leaf_economics.csv  leaf C and N per leaf area, Ryan-1991 leaf maintenance respiration per area,
                              Rd/Vcmax, and per-tree leaf area / crown area / crown LAI / fine-root C at
                              DBH 5, 10, 20, 30 cm for woody PFTs on the 2-power leaf/crown allometry
  scalar_params.csv           scalar parameters in the respiration / phenology / mortality / allocation groups
  summary.md                  readable report of the above (also printed)
  [--other FILE]              other_file_differences.csv: same PFTs, parameters whose values differ between files

Usage on IRIDIS6 (clm_fates_env):
  python 01_compare_fates_pft_parameters.py
  python 01_compare_fates_pft_parameters.py --pfts 2 6 13 11 --other /path/to/another_params.json
Nothing is modified.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

DEFAULT_PARAM = "/iridisfs/scratch/ly3n24/CLM_FATES/CTSM/src/fates/parameter_files/fates_params_default.json"
ORGAN_NAMES = {1: "leaf", 2: "fnrt", 3: "sapw", 4: "store", 5: "repro", 6: "struct"}
HYDR_ORGANS = ["leaf", "stem", "troot", "aroot"]
CATEGORIES = [  # (category, name prefixes) in display order
    ("leaf/photosynthesis", ("fates_leaf_", "fates_leafn_", "fates_maintresp_leaf")),
    ("respiration", ("fates_maintresp", "fates_grperc", "fates_q10")),
    ("allometry", ("fates_allom_",)),
    ("allocation/storage", ("fates_alloc_", "fates_c2b")),
    ("turnover", ("fates_turnover_",)),
    ("stoichiometry", ("fates_stoich_", "fates_cnp_")),
    ("phenology", ("fates_phen_",)),
    ("mortality", ("fates_mort_",)),
    ("recruitment/seed", ("fates_recruit_", "fates_seed_", "fates_frag_seed")),
    ("water", ("fates_nonhydro_", "fates_hydro_", "fates_hydr_")),
    ("radiation", ("fates_rad_",)),
    ("other", ("fates_",)),
]
SUSPECTS = {  # flagged in the report; why they matter for the ENF / grass failures
    "fates_leaf_slatop": "leaf area per unit leaf C; low SLA = little leaf area per kg leaf C",
    "fates_leaf_slamax": "SLA cap deeper in the canopy",
    "fates_leaf_vcmax25top": "photosynthetic capacity per leaf area",
    "fates_stoich_nitr": "leaf/root N per C -> maintenance respiration (Ryan 1991 is per g N)",
    "fates_maintresp_leaf_ryan1991_baserate": "leaf MR per g N (used with fates_leafresp_model = ryan1991)",
    "fates_maintresp_leaf_atkin2017_baserate": "leaf MR per leaf area (used with atkin2017)",
    "fates_allom_d2bl1": "leaf C vs DBH intercept (kg C, not area)",
    "fates_allom_d2bl2": "leaf C vs DBH exponent",
    "fates_allom_d2ca_coefficient_max": "crown area vs DBH coefficient",
    "fates_allom_d2ca_coefficient_min": "crown area vs DBH coefficient",
    "fates_allom_blca_expnt_diff": "crown-area exponent offset",
    "fates_allom_l2fr": "fine-root C per leaf C (root MR and turnover cost)",
    "fates_turnover_leaf_canopy": "leaf longevity in canopy (yr)",
    "fates_turnover_leaf_ustory": "leaf longevity in understory (yr)",
    "fates_turnover_fnrt": "fine-root longevity (yr)",
    "fates_alloc_storage_cushion": "storage target relative to leaf C",
    "fates_mort_scalar_cstarvation": "max carbon-starvation mortality",
    "fates_mort_freezetol": "freezing mortality threshold (degC)",
    "fates_phen_leaf_habit": "1 evergreen, 2 cold-deciduous, 3 stress(drought)-deciduous",
    "fates_phen_drought_threshold": "soil water / potential that triggers drought leaf-off",
    "fates_phen_moist_threshold": "soil water / potential for leaf-on after drought",
    "fates_phen_mindaysoff": "minimum days leaves stay off",
    "fates_recruit_height_min": "recruit height",
    "fates_recruit_init_density": "cold-start seedling density",
    "fates_recruit_init_dbh": "nocomp closed-canopy init DBH (only with use_fates_dbh_init)",
    "fates_recruit_seed_alloc": "seed allocation",
    "fates_recruit_seed_alloc_mature": "seed allocation of mature plants",
    "fates_recruit_seed_dbh_repro_threshold": "DBH at which mature seed allocation starts",
    "fates_recruit_seed_germination_rate": "germination rate",
    "fates_nonhydro_smpsc": "soil potential at full stomatal closure",
    "fates_nonhydro_smpso": "soil potential at full stomatal opening",
}
SCALAR_PREFIXES = ("fates_maintresp", "fates_q10", "fates_phen_", "fates_mort_", "fates_alloc_", "fates_recruit_",
                   "fates_canopy_", "fates_leaf_", "fates_base_mr", "fates_grperc", "fates_daylength")
DBHS = (5.0, 10.0, 20.0, 30.0)


def category(name):
    for cat, prefixes in CATEGORIES:
        if name.startswith(prefixes):
            return cat
    return "other"


def load(path):
    obj = json.loads(Path(path).read_text())
    params = obj.get("parameters", obj)
    names = params["fates_pftname"]["data"]
    names = ["".join(n) if isinstance(n, list) else str(n) for n in names]
    return obj, params, [n.strip() for n in names]


def sub_labels(params, dims, nrow):
    d0 = dims[0] if len(dims) > 1 else None
    if d0 == "fates_plant_organs" and "fates_alloc_organ_id" in params:
        ids = [int(x) for x in params["fates_alloc_organ_id"]["data"]]
        return [ORGAN_NAMES.get(i, f"organ{i}") for i in ids][:nrow]
    if d0 == "fates_hydr_organs":
        return HYDR_ORGANS[:nrow]
    if d0 == "fates_hlm_pftno":
        return [f"hlm{i + 1}" for i in range(nrow)]
    if d0:
        return [f"{d0.replace('fates_', '')}{i}" for i in range(nrow)]
    return [""]


def pft_rows(params, npft):
    rows = []
    for name, p in params.items():
        dims = p.get("dims") or []
        if "fates_pft" not in dims or p.get("dtype") == "string" or name == "fates_pftname":
            continue
        try:
            a = np.asarray(p["data"], dtype=float)
        except (TypeError, ValueError):
            continue
        if a.shape[-1] != npft:
            continue
        a = a.reshape(-1, npft)
        for r, lab in enumerate(sub_labels(params, dims, a.shape[0])):
            rows.append({"parameter": name, "sub": lab, "row": r, "values": a[r], "units": p.get("units", ""),
                         "long_name": p.get("long_name", ""), "category": category(name)})
    return rows


def val(params, name, pft, row=0):
    p = params.get(name)
    if p is None:
        return math.nan
    a = np.asarray(p["data"], dtype=float)
    if a.ndim == 0:
        return float(a)
    a = a.reshape(-1, a.shape[-1])
    return float(a[row, pft - 1]) if a.shape[-1] > 1 else float(a[row, 0])


def leaf_row(params):
    if "fates_alloc_organ_id" in params:
        ids = [int(x) for x in params["fates_alloc_organ_id"]["data"]]
        return ids.index(1) if 1 in ids else 0
    return 0


def fnrt_row(params):
    if "fates_alloc_organ_id" in params:
        ids = [int(x) for x in params["fates_alloc_organ_id"]["data"]]
        return ids.index(2) if 2 in ids else 1
    return 1


def derived(params, pfts, names):
    out = []
    lr, fr = leaf_row(params), fnrt_row(params)
    nonleaf = val(params, "fates_maintresp_nonleaf_baserate", 1)
    for k in pfts:
        sla = val(params, "fates_leaf_slatop", k)
        nleaf = val(params, "fates_stoich_nitr", k, lr)
        nfnrt = val(params, "fates_stoich_nitr", k, fr)
        ryan = val(params, "fates_maintresp_leaf_ryan1991_baserate", k)
        vcmax = val(params, "fates_leaf_vcmax25top", k)
        c_area = 1.0 / sla if sla > 0 else math.nan                      # g C per m2 leaf (canopy top)
        n_area = nleaf * c_area                                         # g N per m2 leaf
        rd_ryan = ryan * n_area / 12.011 * 1e6                          # umol C m-2 leaf s-1 at 20 C
        r = {"pft": k, "name": names[k - 1], "woody": val(params, "fates_woody", k),
             "leaf_habit": val(params, "fates_phen_leaf_habit", k),
             "slatop_m2_per_gC": sla, "leafC_per_area_gC_m2": c_area, "leafN_per_C": nleaf,
             "leafN_per_area_gN_m2": n_area, "vcmax25top": vcmax,
             "Rd_ryan1991_20C_umol_m2_s": rd_ryan, "Rd_atkin2017_base_umol_m2_s": val(params, "fates_maintresp_leaf_atkin2017_baserate", k),
             "Rd_ryan_over_vcmax25": rd_ryan / vcmax if vcmax else math.nan,
             "leaf_turnover_canopy_yr": val(params, "fates_turnover_leaf_canopy", k),
             "leafC_replacement_gC_m2leaf_yr": c_area / val(params, "fates_turnover_leaf_canopy", k),
             "l2fr": val(params, "fates_allom_l2fr", k), "fnrt_turnover_yr": val(params, "fates_turnover_fnrt", k)}
        lmode, amode = val(params, "fates_allom_lmode", k), val(params, "fates_allom_amode", k)
        if r["woody"] == 1 and lmode == 2 and amode in (1, 2, 3):
            p1, p2 = val(params, "fates_allom_d2bl1", k), val(params, "fates_allom_d2bl2", k)
            c2b = val(params, "fates_c2b", k)
            ca = val(params, "fates_allom_d2ca_coefficient_max", k)     # site spread = 1 (closed canopy)
            ediff = val(params, "fates_allom_blca_expnt_diff", k)
            dmax = val(params, "fates_allom_dbh_maxheight", k)
            for d in DBHS:
                deff = min(d, dmax) if amode in (1, 3) else d
                bl = p1 * d ** p2 / c2b                                  # kg C leaf (untrimmed max)
                la = bl * 1000.0 * sla                                   # m2 leaf at canopy-top SLA
                crown = ca * deff ** (p2 + ediff)
                r[f"dbh{int(d)}_leafC_kg"] = bl
                r[f"dbh{int(d)}_leafarea_m2"] = la
                r[f"dbh{int(d)}_crownarea_m2"] = crown
                r[f"dbh{int(d)}_crownLAI"] = la / crown if crown else math.nan
                r[f"dbh{int(d)}_fnrtC_kg"] = bl * r["l2fr"]
                r[f"dbh{int(d)}_leaf_plus_fnrt_N_g"] = bl * 1000 * nleaf + bl * r["l2fr"] * 1000 * nfnrt
                r[f"dbh{int(d)}_leaf_plus_fnrt_MR_20C_gC_day"] = (bl * 1000 * nleaf * ryan +
                                                                  bl * r["l2fr"] * 1000 * nfnrt * nonleaf) * 86400
        out.append(r)
    return out


def fmt(x):
    if isinstance(x, str):
        return x
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return "nan"
    ax = abs(x)
    return f"{x:.4g}" if (ax == 0 or 1e-3 <= ax < 1e5) else f"{x:.3e}"


def write_csv(path, rows, fields):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--param", default=DEFAULT_PARAM)
    ap.add_argument("--pfts", nargs="+", type=int, default=[2, 6, 13], help="1-based FATES PFT indices")
    ap.add_argument("--other", help="second parameter file to diff against (same PFT indices)")
    ap.add_argument("--outdir", type=Path)
    a = ap.parse_args(argv)
    out = a.outdir or Path.home() / f"FATES_PFT_param_compare_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    out.mkdir(parents=True, exist_ok=True)
    obj, params, names = load(a.param)
    npft = len(names)
    sel = [k for k in a.pfts if 1 <= k <= npft]
    if not sel:
        ap.error(f"no valid PFT among {a.pfts} (file has {npft})")
    labels = [f"pft{k}_{names[k - 1]}" for k in sel]
    rows = pft_rows(params, npft)
    table = []
    for r in rows:
        v = r["values"][[k - 1 for k in sel]]
        fin = v[np.isfinite(v)]
        differs = len(fin) > 1 and not np.allclose(fin, fin[0], rtol=1e-9, atol=0)
        rec = {"category": r["category"], "parameter": r["parameter"], "sub": r["sub"], "units": r["units"],
               "differs": differs, "suspect": "yes" if r["parameter"] in SUSPECTS else "",
               "why_it_matters": SUSPECTS.get(r["parameter"], ""), "long_name": r["long_name"]}
        rec.update({lab: float(x) for lab, x in zip(labels, v)})
        rec["all_pfts"] = " ".join(fmt(float(x)) for x in r["values"])
        table.append(rec)
    order = {c: i for i, (c, _) in enumerate(CATEGORIES)}
    table.sort(key=lambda t: (order[t["category"]], t["suspect"] != "yes", t["parameter"], t["sub"]))
    fields = ["category", "parameter", "sub", "units", "differs", "suspect"] + labels + ["why_it_matters", "long_name", "all_pfts"]
    write_csv(out / "pft_params_all.csv", table, fields)
    diff = [t for t in table if t["differs"]]
    write_csv(out / "pft_params_differing.csv", diff, fields)

    der = derived(params, sel, names)
    dfields = sorted({k for r in der for k in r}, key=lambda k: (k not in ("pft", "name"), k))
    write_csv(out / "derived_leaf_economics.csv", der, dfields)

    scal = []
    for n, p in params.items():
        if (p.get("dims") or []) == ["scalar"] and n.startswith(SCALAR_PREFIXES):
            scal.append({"parameter": n, "value": p["data"][0] if isinstance(p["data"], list) else p["data"],
                         "units": p.get("units", ""), "long_name": p.get("long_name", "")})
    scal.sort(key=lambda s: s["parameter"])
    write_csv(out / "scalar_params.csv", scal, ["parameter", "value", "units", "long_name"])

    L = [f"# FATES PFT parameter comparison", "",
         f"File: `{a.param}`  ({npft} PFTs)  |  generated {datetime.now(timezone.utc).isoformat()}",
         f"Selected: " + ", ".join(labels), ""]
    hist = obj.get("attributes", {}).get("history")
    if hist:
        L += [f"File history attribute: {str(hist)[:300]}", ""]
    L += ["## Suspect parameters (selected PFTs)", "", "| parameter | sub | " + " | ".join(f"PFT {k}" for k in sel) + " | units | why |",
          "| --- | --- | " + " | ".join("---:" for _ in sel) + " | --- | --- |"]
    for t in table:
        if t["suspect"]:
            L.append(f"| {t['parameter']} | {t['sub']} | " + " | ".join(fmt(t[l]) for l in labels) +
                     f" | {t['units']} | {t['why_it_matters']} |")
    L += ["", "## Derived leaf economics and per-tree allometry", "",
          "Leaf area uses canopy-top SLA (a lower bound: FATES raises SLA with canopy depth up to slamax). "
          "Crown area assumes site spread = 1. Respiration at 20 C before temperature and canopy scaling.", "",
          "| quantity | " + " | ".join(f"PFT {r['pft']}" for r in der) + " |", "| --- | " + " | ".join("---:" for _ in der) + " |"]
    keys = ["leafC_per_area_gC_m2", "leafN_per_area_gN_m2", "vcmax25top", "Rd_ryan1991_20C_umol_m2_s",
            "Rd_atkin2017_base_umol_m2_s", "Rd_ryan_over_vcmax25", "leaf_turnover_canopy_yr",
            "leafC_replacement_gC_m2leaf_yr", "l2fr", "fnrt_turnover_yr"]
    keys += [f"dbh{int(d)}_{q}" for d in DBHS for q in ("leafC_kg", "leafarea_m2", "crownarea_m2", "crownLAI",
                                                         "leaf_plus_fnrt_MR_20C_gC_day")]
    for k in keys:
        if any(k in r for r in der):
            L.append(f"| {k} | " + " | ".join(fmt(r.get(k, math.nan)) for r in der) + " |")
    L += ["", f"## All differing PFT parameters ({len(diff)} rows)", "",
          "| category | parameter | sub | " + " | ".join(f"PFT {k}" for k in sel) + " | units |",
          "| --- | --- | --- | " + " | ".join("---:" for _ in sel) + " | --- |"]
    for t in diff:
        L.append(f"| {t['category']} | {t['parameter']} | {t['sub']} | " + " | ".join(fmt(t[l]) for l in labels) + f" | {t['units']} |")
    L += ["", f"## Scalar parameters in respiration / phenology / mortality / allocation groups ({len(scal)})", "",
          "| parameter | value | units |", "| --- | ---: | --- |"]
    for s in scal:
        L.append(f"| {s['parameter']} | {fmt(float(s['value'])) if isinstance(s['value'], (int, float)) else s['value']} | {s['units']} |")

    if a.other:
        _, p2, n2 = load(a.other)
        rows2 = {(r["parameter"], r["row"]): r["values"] for r in pft_rows(p2, len(n2))}
        od = []
        for r in rows:
            v2 = rows2.get((r["parameter"], r["row"]))
            if v2 is None:
                od.append({"parameter": r["parameter"], "sub": r["sub"], "note": "missing in other file"})
                continue
            v1 = r["values"][[k - 1 for k in sel]]
            w = v2[[k - 1 for k in sel if k <= len(v2)]] if len(v2) >= max(sel) else None
            if w is None or not np.allclose(v1, w, rtol=1e-9, atol=0, equal_nan=True):
                rec = {"parameter": r["parameter"], "sub": r["sub"], "note": ""}
                rec.update({f"this_{lab}": float(x) for lab, x in zip(labels, v1)})
                if w is not None:
                    rec.update({f"other_pft{k}": float(x) for k, x in zip(sel, w)})
                od.append(rec)
        ofields = sorted({k for r in od for k in r}, key=lambda k: (k not in ("parameter", "sub", "note"), k))
        write_csv(out / "other_file_differences.csv", od, ofields)
        L += ["", f"## Differences against `{a.other}`: {len(od)} rows (other_file_differences.csv)"]

    text = "\n".join(L) + "\n"
    (out / "summary.md").write_text(text, encoding="utf-8")
    print(text)
    print(f"OUTPUT: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
