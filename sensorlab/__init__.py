"""sensorlab - module selection for a biosensor platform.

Layered so the kinetic core stays untouched:

    tables / units / spreads   reading and converting data files
    data                       typed records and parameter assembly
    stage1                     can the clinic tell sick from healthy at all
    stage2                     can a sensor read that difference
    report                     the traffic-light table

Named sensorlab rather than platform so it cannot shadow the standard library.
stage1 and stage2 are not imported here: stage2 pulls in das_model, and keeping
that out of the package import keeps the dependency one-directional.
"""
from . import data, spreads, tables, units  # noqa: F401


def load(scenario="screen_default"):
    """Everything the two stages need, with units already resolved."""
    platform = data.load_platform()
    scenarios = data.load_scenarios()
    if scenario not in scenarios:
        raise KeyError("scenario %r is not in scenarios.csv" % scenario)
    return dict(
        platform=platform,
        scenario=scenarios[scenario],
        scenario_name=scenario,
        sensors=data.load_sensors(),
        clinical=data.load_clinical(),
        unit_table=units.UnitTable(platform=platform),
        spread_table=spreads.SpreadTable(),
    )
