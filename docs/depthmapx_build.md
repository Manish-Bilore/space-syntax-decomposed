# Building depthmapXcli without Qt

The GUI needs Qt5; the command-line tool does not. Tested on Linux with CMake + Ninja + GCC 13
(macOS with Xcode command-line tools should work the same way).

```bash
git clone --depth 1 https://github.com/SpaceGroupUCL/depthmapX.git
cd depthmapX

# comment out the GUI and test subdirectories
sed -i.bak -E 's/^add_subdirectory\((genlibTest|mgraph440Test|salaTest|cliTest|depthmapXTest|depthmapX|GuiUnitTest|moduleTest)\)/# &/' CMakeLists.txt

mkdir build && cd build
cmake .. -G Ninja -DCMAKE_BUILD_TYPE=Release
ninja depthmapXcli

export DEPTHMAPX=$PWD/depthmapXcli/depthmapXcli
$DEPTHMAPX -h
```

On macOS use `sed -i '' -E ...`. If Ninja is missing, drop `-G Ninja` and run `make depthmapXcli`.

The repo also ships reference data used in `scripts/00_fidelity.py`:
`testdata/barnsbury_extended1_axial.csv` (Barnsbury, London; 1,100 axial lines).

## Commands the wrapper runs

```bash
$DEPTHMAPX -m IMPORT     -f lines.csv  -o g.graph
$DEPTHMAPX -m MAPCONVERT -f g.graph    -o g.graph -co axial   -con Axial
$DEPTHMAPX -m MAPCONVERT -f g.graph    -o g.graph -co segment -con Segment
$DEPTHMAPX -m SEGMENT    -f g.graph    -o g.graph -st tulip -stb 1024 -srt metric -sr n,400,800 -sic
$DEPTHMAPX -m EXPORT     -f g.graph    -o map.csv  -em shapegraph-map-csv
$DEPTHMAPX -m EXPORT     -f g.graph    -o conn.csv -em shapegraph-connections-csv
```
