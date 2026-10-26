# Batch03: AD400 verified complete, Normal5 verified, Normal395 submitted (26 October 2026)

Operator run of [Stage14](../scripts/14_batch03_AD400_to_NORMAL400.py) on IRIDIS6 (login6001, `ulimit -s unlimited`), commit `36613e8`.

## AD400 completion (`audit-ad400`, read only): 10/10 PASS

Each site: 80 `run` + 80 `st_archive` jobs `COMPLETED 0:0` since the recorded AD5 job, 80 archived restart folders, final three-component restart at Y+400, land `spinup_state=2`.

| Site | AD case | AD start Y | Final AD restart |
| --- | --- | ---: | --- |
| IT-Lav | IT-Lav_B03_FIXNC_AD400 | 2003 | 2403-01-01-00000 |
| FI-Let | FI-Let_B03_FIXNC_AD400 | 2010 | 2410-01-01-00000 |
| IL-Yat | IL-Yat_B03_FIXNC_BARE52_AD400 | 2000 | 2400-01-01-00000 |
| DE-Obe | DE-Obe_B03_FIXNC_AD400 | 2008 | 2408-01-01-00000 |
| CZ-Stn | CZ-Stn_B03_FIXNC_AD400 | 2010 | 2410-01-01-00000 |
| DE-Lnf | DE-Lnf_B03_FIXNC_AD400 | 2002 | 2402-01-01-00000 |
| DE-Hzd | DE-Hzd_B03_FIXNC_AD400 | 2010 | 2410-01-01-00000 |
| GF-Guy | GF-Guy_B03_FIXNC_AD400 | 2004 | 2404-01-01-00000 |
| AT-Neu | AT-Neu_B03_FIXNC_AD400 | 2002 | 2402-01-01-00000 |
| CH-Cha | CH-Cha_B03_FIXNC_AD400 | 2005 | 2405-01-01-00000 |

## Normal400 progress

`stage-normal` 10/10: each hybrid case validated with `spinup_state` absent from the generated `lnd_in`, `CLM_ACCELERATED_SPINUP=off`, and restarts copied from the final AD checkpoint. `submit-normal5` 10/10. `audit-normal5` 10/10 PASS: run and archive `COMPLETED 0:0`, land `spinup_state=0`. `continue-normal395` 10/10 submitted (`CONTINUE_RUN=TRUE`, `RESUBMIT=78`).

| Site | Normal case | Normal5 run / archive | Normal5 restart | Normal395 first run / archive | Target |
| --- | --- | --- | --- | --- | --- |
| IT-Lav | IT-Lav_B03_FIXNC_NORMAL400 | 4733846 / 4733847 | 2408 | 4733904 / 4733905 | 2803-01-01 |
| FI-Let | FI-Let_B03_FIXNC_NORMAL400 | 4733848 / 4733849 | 2415 | 4733906 / 4733907 | 2810-01-01 |
| IL-Yat | IL-Yat_B03_FIXNC_BARE52_NORMAL400 | 4733850 / 4733851 | 2405 | 4733908 / 4733909 | 2800-01-01 |
| DE-Obe | DE-Obe_B03_FIXNC_NORMAL400 | 4733852 / 4733853 | 2413 | 4733910 / 4733911 | 2808-01-01 |
| CZ-Stn | CZ-Stn_B03_FIXNC_NORMAL400 | 4733854 / 4733855 | 2415 | 4733912 / 4733913 | 2810-01-01 |
| DE-Lnf | DE-Lnf_B03_FIXNC_NORMAL400 | 4733856 / 4733857 | 2407 | 4733914 / 4733915 | 2802-01-01 |
| DE-Hzd | DE-Hzd_B03_FIXNC_NORMAL400 | 4733858 / 4733859 | 2415 | 4733916 / 4733917 | 2810-01-01 |
| GF-Guy | GF-Guy_B03_FIXNC_NORMAL400 | 4733860 / 4733861 | 2409 | 4733918 / 4733919 | 2804-01-01 |
| AT-Neu | AT-Neu_B03_FIXNC_NORMAL400 | 4733862 / 4733863 | 2407 | 4733920 / 4733921 | 2802-01-01 |
| CH-Cha | CH-Cha_B03_FIXNC_NORMAL400 | 4733864 / 4733865 | 2410 | 4733922 / 4733923 | 2805-01-01 |

Submission is not completion. When no `*_B03_*_NORMAL400` jobs remain, run `python3 -B examples/Batch03_10/scripts/14_batch03_AD400_to_NORMAL400.py audit-normal400` (80 + 80 successes, restart Y+800, `spinup_state=0`). Do not rerun `continue-normal395`. Reaching 800 model years does not demonstrate carbon-pool equilibrium; drift diagnostics are a separate step.
