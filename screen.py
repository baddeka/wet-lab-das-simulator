"""Screen every sensor element in data/sensors.csv against every clinical study
in data/clinical.csv, through the two-stage filter, and print the traffic-light
table.

    python screen.py                  summary, passes, rejections, gaps
    python screen.py --full           also the full sensor x study matrix
    python screen.py --scenario NAME  any scenario from data/scenarios.csv

Nothing is configured here. Change the data files, not this script.
"""
import sys

import sensorlab
from sensorlab import report


def main(argv):
    scenario = "screen_default"
    if "--scenario" in argv:
        scenario = argv[argv.index("--scenario") + 1]
    bundle = sensorlab.load(scenario)
    result = report.build(bundle)
    report.render_all(bundle, result, full="--full" in argv)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
