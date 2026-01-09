# OpenDrive-Map-Generator
A standalone tool to generate real-world OpenDRIVE (.xodr) maps for driving simulators (CARLA, CarMaker, etc.) using OpenStreetMap data. Features a GUI, multi-server support, and automatic location naming.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.x-blue.svg)](https://www.python.org/)


## Features

* **GUI Map Selector:** Search for specific locations or use the rectangle selection interface to select regions.
* **Automated Conversion:** Downloads OSM vector data and converts it to the OpenDRIVE standard.
* **Backend:** Utilizes Eclipse SUMO's `netconvert` utility for data processing.
* **Network Handling:** Includes failover support for multiple OSM server mirrors to reduce timeout errors during large downloads.
* **Automatic Naming:** Detects the location name (City/Town) to generate descriptive filenames.
* **Portable:** Can be packaged as a standalone executable with no external system dependencies.

---

## Download and Usage

### Option 1: Portable Executable (Recommended)
Use this method to run the tool without installing Python or additional libraries.

1.  Navigate to the **[Releases](../../releases)** page.
2.  Download the latest `.zip` archive.
3.  Extract the contents to a folder.
4.  Run `OpenDriveGenerator.exe`.
5.  **Note:** The executable requires the `sumo_bin` folder to be in the same directory. Do not move the executable separately.

### Option 2: Run from Source
For developers who wish to modify or inspect the code.

1.  Clone the repository:
    ```bash
    git clone [https://github.com/your-username/OpenDrive-Map-Generator.git](https://github.com/your-username/OpenDrive-Map-Generator.git)
    cd OpenDrive-Map-Generator
    ```

2.  Install dependencies:
    ```bash
    pip install requests tkintermapview
    ```

3.  **Setup SUMO:**
    * **Method A:** Install [Eclipse SUMO](https://eclipse.dev/sumo/) and add it to your system PATH.
    * **Method B:** Create a folder named `sumo_bin` in the project root and place `netconvert.exe` and its required DLLs inside.

4.  Run the script:
    ```bash
    python OpenDriveTool.py
    ```

---

## How It Works

1.  **Selection:** The user defines a bounding box using the map interface.
2.  **Data Retrieval:** The tool queries the Overpass API (OpenStreetMap) to retrieve road vector data (`.osm`).
3.  **Preprocessing:** The data is filtered to remove non-drivable geometry and calculate the geolocation name.
4.  **Conversion:** The SUMO `netconvert` binary transforms the nodes and ways into OpenDRIVE geometry, including lanes, junctions, and signals.
5.  **Output:** The final `.xodr` file is saved to the user's Desktop in the `OpenDriveMaps` folder.

---

## License and Credits

This project integrates components with different licenses. Please review the following when redistributing.

### 1. Source Code
The Python source code in this repository is licensed under the **MIT License**.

### 2. SUMO (Simulation of Urban MObility)
This tool uses the `netconvert` utility from the Eclipse SUMO project.
* [cite_start]**License:** [Eclipse Public License 2.0 (EPL-2.0)](https://www.eclipse.org/legal/epl-2.0/) [cite: 2]
* **Source:** [https://github.com/eclipse-sumo/sumo](https://github.com/eclipse-sumo/sumo)
* *Note: Distributions of this tool must include the SUMO license file.*

### 3. Map Data
Map data is provided by **OpenStreetMap**.
* **Copyright:** © OpenStreetMap contributors
* **License:** [ODbL (Open Data Commons Open Database License)](https://opendatacommons.org/licenses/odbl/)

---

## Contributing

Contributions are welcome. Please open an issue to discuss significant changes before submitting a pull request.

1.  Fork the Project
2.  Create your Feature Branch (`git checkout -b feature/NewFeature`)
3.  Commit your Changes (`git commit -m 'Add NewFeature'`)
4.  Push to the Branch (`git push origin feature/NewFeature`)
5.  Open a Pull Request

---

## Disclaimer

This software is provided "as is", without warranty of any kind. It is intended for educational and research purposes. The authors are not responsible for the accuracy of the generated maps or their use in safety-critical systems.
