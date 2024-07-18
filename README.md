DetectiCE - Detection of Complex Events in video streams
===

This project is the implementation part of my master thesis called _Complex event detection in video streams_.

It is a CLI application written in Python, built as a part of the Videolytics system.

## Access to the Videolytics database

The Videolytics database is not public. Without this access, it is not possible to obtain input data for DetectiCE 
and run custom queries or visualize already computed results.
However, it is entirely possible to connect to a different database with an identical structure of relevant tables 
by altering the `try_connect` function in `connector`. 

## Installation

### Prerequisites

Make sure Python is installed and available on your system. For details on how to install, 
check their [official website](https://www.python.org/downloads/).

The recommended version of Python is 3.12.

Additionally, pip needs to be installed to get all required dependencies. You can ensure pip is installed by running

```shell
pip --version
```

If no version is returned, see [official page](https://pip.pypa.io/en/stable/installation/).

### Dependencies

All Python dependencies need to be installed, either globally, or inside a virtual environment.

#### Setting up a virtual environment

The recommended way to install dependencies is within a custom virtual environment by running:

For Windows:
```commandline
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

For Linux:
```shell
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

At this point, the software is ready to be used. Once finished, you can exit the venv by running

```shell
deactivate
```

#### Installing dependencies globally

Alternatively, dependencies can be installed without a virtual environment. In this case,
the process consists of simply installing dependencies with:

```shell
pip install -r requirements.txt
```

However, we strongly recommend using virtual environment.

## Usage

The DetectiCE can be run as a CLI application to search and detect queried behavior on top of a pre-processed video file.

```commandline
usage: main.py [-h] --preset {rvacka_pravo,rvacka_stred,kradez_pravo,kradez_stred} [--preview] [-C] [-L] [-S] [-k CONFIDENCE_COEFFICIENT] [-c MIN_CONFIDENCE] [-m MAX_MEMORY]
               [-r RESULTS_PATH] [-v VIDEO_PATH]
               [query_path]

positional arguments:
  query_path            Path to text file with query to search.

options:
  -h, --help            show this help message and exit
  --preset {rvacka_pravo,rvacka_stred,kradez_pravo,kradez_stred}
  --preview             Only preview agents and their features.
  -C, --compute_only    If set, previews won't start at the end of the run.
  -L, --force_load      Delete cached data, load new data from DB.
  -S, --force_search    Delete cached results, run query search.
  -k CONFIDENCE_COEFFICIENT, --confidence_coefficient CONFIDENCE_COEFFICIENT
                        Convex parameter t for RC-comparer of confidences.
  -c MIN_CONFIDENCE, --min_confidence MIN_CONFIDENCE
                        Minimal threshold for confidence. Any intermediate confidence below this threshold will be removed from further processing.
  -m MAX_MEMORY, --max_memory MAX_MEMORY
                        Maximal size of memory stack for each node in time graph.
  -r RESULTS_PATH, --results_path RESULTS_PATH
                        Path where results are saved/loaded. Defaults to ./results/<preset>/<query_file.name>.csv
  -v VIDEO_PATH, --video_path VIDEO_PATH
                        Path where video is stored. Defaults to ./videos/<preset>.mp4
```

### Video file

Each preset corresponds to a single video file from which the data have been pre-processed.
In order to visualize the results, the video needs to be present locally.
These videos are currently not made public and are stored on the server alongside the database.
Besides that, to visualize the results, an access to the Videolytics database is needed, as mentioned above.

### Query file

The input for DetectiCE is a textual query file containing a query written in a custom context-free grammar.
The structure of this grammar is denoted in diagrams found [here](documentation/behavior_grammar.html).

A part of this project are some existing example queries found in [examples](./examples).

### Simple usage example

```commandline
python main.py --preset kradez_pravo examples/pickpocket.txt
```

For more examples, please refer to the [user guide](documentation/user_guide.md#usage).

## Other resources

User guide with information focused on installation and usage of the software can be found [here](documentation/user_guide.md).

Technical documentation containing information about the project structure, architecture, 
models and algorithms can be found [here](documentation/technical_documentation.md).
