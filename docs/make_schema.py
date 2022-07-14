import codecs
import subprocess

import sadisplay

from dhos_encounters_api.models import encounter, location_history, score_system_history

desc = sadisplay.describe(
    [
        encounter.Encounter,
        location_history.LocationHistory,
        score_system_history.ScoreSystemHistory,
    ]
)
with codecs.open("docs/schema.plantuml", "w", encoding="utf-8") as f:
    f.write(sadisplay.plantuml(desc).rstrip() + "\n")

with codecs.open("docs/schema.dot", "w", encoding="utf-8") as f:
    f.write(sadisplay.dot(desc).rstrip() + "\n")

my_cmd = ["dot", "-Tpng", "docs/schema.dot"]
with open("docs/schema.png", "w") as outfile:
    subprocess.run(my_cmd, stdout=outfile)
