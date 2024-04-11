import argparse
import collections
import hashlib
import os.path
import re
import sys

from typing import Dict, List, NamedTuple, Optional, Tuple


SEPARATOR = "=================="

PRIMITIVE_PREFIXES = [
    "_Py_atomic",
]

PRIMITIVE_RE = re.compile("^" + "|".join(PRIMITIVE_PREFIXES))

TEST_STATUS_RE = re.compile("^\d+:\d+:\d+ load avg: \d+.\d+ \[ ?\d+/\d+] (test_[a-zA-Z0-9]+)")


class Location(NamedTuple):
    func: str
    path: str
    lineno: int

    def to_id(self) -> str:
        return f"{self.func}:{self.path}:{self.lineno}"


def get_key(lines: List[str]) -> Optional[Location]:
    for line in lines:
        if line.startswith("    #"):
            _, func, loc, rest = line.split(maxsplit=3)
            if PRIMITIVE_RE.match(func) is None:
                try:
                    path, lineno, _ = loc.split(":")
                except ValueError:
                    path = loc
                    lineno = "0"
                basename = os.path.basename(path)
                return Location(func, basename, int(lineno))
    return None


class Race:
    def __init__(self, loc: Location) -> None:
        self.tests = set()
        self.loc = loc
        self.examples = []


def render_races(races: Dict[Location, Race]) -> None:
    print("<!DOCTYPE html>")
    print("<html>")
    print("<head>")
    print('''
     <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">

    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@4.0.0/dist/css/bootstrap.min.css" integrity="sha384-Gn5384xqQ1aoWXA+058RXPxPg6fy4IWvTNh0E263XmFcJlSAwiGgFAW/dAiS6JXm" crossorigin="anonymous">
<script src="https://code.jquery.com/jquery-3.2.1.slim.min.js" integrity="sha384-KJ3o2DKtIkvYIK3UENzmM7KCkRr/rE9/Qpg6aAZGJwFDMVNA/GpGFF93hXpG5KkN" crossorigin="anonymous"></script>
<script src="https://cdn.jsdelivr.net/npm/popper.js@1.12.9/dist/umd/popper.min.js" integrity="sha384-ApNbgh9B+Y1QKtv3Rn7W3mgPxhU9K/ScQsAP7hUibX39j7fakFPskvXusvfa0b4Q" crossorigin="anonymous"></script>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@4.0.0/dist/js/bootstrap.min.js" integrity="sha384-JZR6Spejh4U02d8jOt6vLEHfe/JQGiRRSQQxSfFWpi1MquVdAyjUar5+76PVCmYl" crossorigin="anonymous"></script>
    <style>
      .race:hover {
        background: #efefef;
      }

    </style>
    ''')
    print("</head>")
    print("<body>")
    print("<div class='container-fluid'>")
    print("<div class='row'><div class='col'><strong>Function</strong></div><div class='col'><strong>File</strong></div><div class='col'><strong>Lineno</strong></div><div class='col'><strong>Count</strong></div><div class='col'><strong>Tests</strong></div><div class='col'><strong>Examples</strong></div></div>")
    sorted_races = sorted(races.items(), reverse=True, key=lambda kv: len(kv[1].examples))
    for loc, race in sorted_races:
        examples_id = loc.to_id() + "_examples"
        tests = ", ".join(sorted(race.tests))
        print(f"  <div class='row race'><div class='col'>{loc.func}</div><div class='col'>{loc.path}</div><div class='col'>{loc.lineno}</div><div class='col'>{len(race.examples)}</div><div class='col'>{tests}</div><div class='col'><a data-toggle='collapse' href='#{examples_id}'>Show/hide examples</a></div></div>")
        print(f"  <div class='row collapse' id='{examples_id}'><div class='col'>")
        for example in race.examples:
            print(f"    <details><summary>Example</summary><p><pre><code>{example}</code></pre></p></details>")
        print("</div></div>")

    print("</div>")
    print("</body>")
    print("</html>")


def main(path: str) -> None:
    races = {}
    if path == "-":
        infile = sys.stdin
    else:
        infile = open(path)
    try:
        lines = []
        in_race = False
        cur_test = None
        for line in infile:
            line = line.strip("\n")
            if in_race:
                if line == SEPARATOR:
                    loc = get_key(lines)
                    race = races.get(loc, None)
                    if race is None:
                        race = Race(loc)
                        races[loc] = race
                    race.examples.append("\n".join(lines))
                    if cur_test is not None:
                        race.tests.add(cur_test)
                    in_race = False
                    lines = []
                else:
                    lines.append(line)
            else:
                matches = TEST_STATUS_RE.match(line)
                if matches is not None:
                    cur_test = matches.group(1)
                elif line == SEPARATOR:
                    in_race = True
    finally:
        infile.close()
    render_races(races)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("races_path")
    args = parser.parse_args()
    main(args.races_path)
