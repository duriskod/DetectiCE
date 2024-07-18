DetectiCE - User Documentation
===

DetectiCE is a CLI application developed as a part of the Videolytics system.

It is used to parse textual queries describing behavioral patterns, and use those to seek and detect instances of 
this pattern in video footage which has been pre-processed by the Videolytics pipeline.

# Table of contents

<!-- TOC start (generated with https://github.com/derlin/bitdowntoc) -->

- [Installation](#installation)
   * [Prerequisites](#prerequisites)
   * [Dependencies](#dependencies)
      + [Setting up a virtual environment](#setting-up-a-virtual-environment)
      + [Installing dependencies globally](#installing-dependencies-globally)
- [Usage](#usage)
   * [Preset](#preset)
   * [Preview](#preview)
   * [Paths](#paths)
   * [Configuration](#configuration)
   * [Flags](#flags)
- [Process](#process)
   * [Input - Queries](#input---queries)
      + [Actors](#actors)
      + [Features](#features)
         - [Speed](#speed)
         - [(Change of) Direction](#change-of-direction)
         - [Distance](#distance)
         - [Mutual Direction](#mutual-direction)
         - [(Actual) Distance Change](#actual-distance-change)
         - [Intended Distance Change](#intended-distance-change)
         - [Relative Direction](#relative-direction)
      + [Logical connectors](#logical-connectors)
         - [Conjunction](#conjunction)
         - [Disjunction](#disjunction)
         - [Negation](#negation)
      + [Restrictions](#restrictions)
         - [Time restriction](#time-restriction)
         - [Confidence restriction](#confidence-restriction)
      + [Temporal connectors](#temporal-connectors)
      + [Examples](#examples)
   * [Output - Results](#output---results)
   * [Visualization](#visualization)

<!-- TOC end -->

# Installation

DetectiCE is written in Python and therefore requires Python to be installed on the system where it is run.

## Prerequisites

Make sure Python is installed and available on your system. For details on how to install, 
check their [official website](https://www.python.org/downloads/).

The recommended version of Python is 3.12.

Additionally, pip needs to be installed to get all required dependencies. You can ensure pip is installed by running

```shell
pip --version
```

If no version is returned, see [official page](https://pip.pypa.io/en/stable/installation/).

## Dependencies

The application depends on several other important packages. These need to be installed, either globally, or inside a virtual environment.

### Setting up a virtual environment

The recommended way to install dependencies is within a custom virtual environment. This will serve to contain the 
packages and avoid polluting the global environment. This is just one of the advantages, and you can read more regarding
virtual environments [here](https://docs.python.org/3/library/venv.html).

You can install the dependencies by opening Command Prompt or PowerShell (on Windows), or Terminal (on Linux), then navigate to the project directory by i.e.:

```commandline
cd path/to/DetectiCE
```

And then setting up the virtual environment and installing dependencies as follows:

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

At this point, the software should be ready to be used. You can check this for example by running:

For Windows:
```commandline
python main.py --help
```

For Linux:
```commandline
python3 main.py --help
```

This should print an argument help. Afterwards, once finished, you can exit the venv by running

```shell
deactivate
```

### Installing dependencies globally

Alternatively, dependencies can be installed without a virtual environment. In this case,
the process consists of simply installing dependencies with:

```shell
pip install -r requirements.txt
```

Similarly to venv alternative, at this point, the program should be runnable. You can check this for example by running:

For Windows:
```commandline
python main.py --help
```

For Linux:
```commandline
python3 main.py --help
```

# Usage

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

The DetectiCE can be run from a command line / terminal by passing a set of arguments. These can be categorized into multiple categories:

## Preset

Preset is a fixed value corresponding to one of the pre-processed videos saved in the Videolytics database ready to be used.
Currently, there are 4 videos which can be used for behavioral search:
- rvacka_pravo - wide angle footage of several role-played fights in a public space
- rvacka_stred - narrow angle footage of the same role-played fights
- kradez_pravo - wide angle footage of several role-played robberies and pickpockets, again in the same public space
- kradez_stred - narrow angle footage of the same role-played robberies and pickpockets

While the preset technically selects the video, these presets essentially describe specific configurations for loading the data of these videos, thus the argument name.

## Preview

The preview flag overrides the functionality of DetectiCE and instead only runs the preview of the video with no processing and no behavioral data.
The only data shown are the trajectories and their details including semantic representations such as features and tuple features.

## Paths

There are 3 paths/files important to the run of a DetectiCE:

- Query path
  - must point to a text file containing the query describing a behavioral pattern.
- Video path 
  - must point to a video file for the used preset. This is used for the final preview of matched instances.
- Results path
  - has default value equal to `./results/{query_name}.csv`
  - if the file exists (either where results_path points or at the default position otherwise), these results are loaded directly and no computation is conducted (this behavior can be overridden by flag -S)
  - if the file does not exist, the computation takes place and the results are saved at the specified path

## Configuration

Configuration arguments are optional, as there are defaults defined for each (found in [configuration.py](../behavior/configuration.py)).

- Confidence coefficient - A coefficient defined in range <0; 1>. It decides how much accuracy is preferred over the duration of matches. Simply put, a coefficient equal to 0 results in only the duration of matches being taken into account, while 1 results in only the accuracy (i.e., percentage of the match being correct) being taken into account.
- Minimal confidence - A bottom threshold, below which any confidences are prematurely cut off during all parts of the process. Increasing this threshold may improve accuracy but may potentially create false negatives and also decrease performance.
- Maximal memory - Specifies the depth of memory nodes during one of the computation steps - time graph. An increase of this parameter may decrease performance while potentially increasing the number of results.

## Flags

- Compute only - Specifies not to show previews of computed results. This is especially useful when running queries in bulk, i.e, using an external script.
- Force load - The data from the server regarding trajectories and other data is cached locally for faster access in later runs. This flag can be specified to purge the cache and re-query the data, for example if changes are made to the data in the database.
- Force search - If the results file is found, it will be used for preview by default and no search is run. This flag can be specified to force the search to run and overwrite the results file.

# Process

## Input - Queries

Queries are the input of the DetectiCE. They describe the behavior which should be searched for in the video footage.

These queries are written as simple text and resemble a natural language by design, albeit somewhat primitive at the moment.
They describe recursive temporal, restricting, and logical connections of desired features of individual actors present in the pattern.

The complete definition of the context-free grammar to which the queries must conform can be found [here](./behavior_grammar.html).

### Actors

Actors are any non-reserved strings of alphanumeric characters including underscore which don't start with a number. They are case-sensitive.

Words such as "Anna", "Bob", "Bystander001", "PotentialSuspect" and "man_with_a_cane" are all valid actors.

While there is a considerable amount of reserved words, these are mostly words that usually aren't used in place of nouns or pronouns.

### Features

Currently recognized set of features is defined on top of either one (unary) or two actors (binary).
Those defined on top of a pair of actors can be further divided into symmetrical and asymmetrical.

Symmetrical features are often identical for both actors and their order is unimportant.

For example,

> Anna is far from Bob.

describes symmetrical feature of **Distance** and is equivalent to

> Bob is far from Anna.

On the other hand, asymmetrical feature **Intended direction**, such as

> Anna moves towards Bob.

describes only the actions of Anna, and by no means implies

Additional detail that may be confusing is the ability to "fit" more than 2 actors into some binary features.
This is simply syntactic sugar and these are internally computed as a conjunction of all pairs.

Finally, in case of asymmetrical features, the asymmetrical nature makes the contained actors different.
Because of this, we differentiate between them as **Actor** and **Target**, i.e.,

> Actor walks towards Target.

#### Speed

Speed is a unary feature. It describes the speed at which actors move.

> Anna walks.  
> Bob runs.  
> Charlie stands.

Additionally, 'move' stands for 'walk' OR 'run'
> Daniel moves.

#### (Change of) Direction

Direction is a unary feature. It describes how the direction of movement changes (w.r.t. previous movement).

> Anna walks straight.  
> Bob runs opposite.  
> Charlie moves left.

#### Distance

Distance is a symmetrical binary feature. It describes the distance between 2 actors. It has 2 forms which are functionally identical (with the difference of one not being able to contain more than 2 actors):
> Actor1 is <Distance> Actor2.  
> Actors are <Distance> each other.

> Anna is ___far from___ Bob.  
> Charlie is ___near to___ Anna.  
> Bob and Charlie are ___adjacent to___ each other.

In case of more actors than 2, the distance must hold for all. This rule holds for all pair features unless mentioned otherwise. For example:
> Anna, Bob and Charlie are far from each other.

is equivalent to

> Anna and Bob are far from each other  
> and Anna and Charlie are far from each other  
> and Bob and Charlie are far from each other.

#### Mutual Direction

Mutual direction is a symmetrical binary feature. It describes how actors are oriented (w.r.t. each other).

I.e., if 2 actors walk in opposite directions, their movement vectors hold ~180° angle.

> Anna and Bob walk in ___opposite directions___.  
> Anna and Charlie run ___independently / independent of each other___.  
> Bob and Charlie move ___in parallel___.

#### (Actual) Distance Change

Actual distance change is a symmetrical binary feature. It describes how the distance between actors changes.

> Anna and Bob walk ___towards___ each other.  
> Anna and Charlie walk ___alongside___ each other.  
> Bob and Charlie walk ___away from___ each other.

In contrast to **Distance**, this feature may not be used in the form

> ~~Anna walks towards Bob.~~

This is due to the fact that this syntax is used by **Intended Distance Change** described below.

#### Intended Distance Change

Intended distance change is an asymmetrical binary feature. It describes how the distance between Actor and Target 
changes should the Target not move.

> Anna walks ___towards___ Bob.  
> Bob runs ___away from___ Charlie.  
> Charlie moves ___alongside___ Anna.

This perhaps seemingly confusing feature aims to describe the Actor's intention rather than an actual state. For example, if
Actor follows Target but Target actively walks away from Actor, their **Actual Distance Change** may be constant (or 
even increasing), but **Intended Distance Change** will consistently show the Actor indeed follows the Target.

#### Relative Direction

Relative direction is an asymmetrical binary feature. It describes the angle at which Actor moves w.r.t. Target.
Formally, it's the angle between the movement vector of the Actor and the difference vector of Target from Actor.

> Anna moves ___straight to___ Bob.
> Bob walks ___to the left of___ Charlie.
> Charlie runs ___opposite to___ Anna.

### Logical connectors

As the name implies, the logical connectors are used to join multiple sub-queries using boolean-like connectors.

#### Conjunction

Conjunction will be matched to data only if all of its sub-queries hold. For example:

> Anna walks and Bob stands.

#### Disjunction

Disjunction will hold only if at least one of its sub-queries holds.

> Anna walks or Bob stands.

#### Negation

Negation contains only one sub-query. It essentially flips its truth value, matching only if its sub-query does not hold.

> not (Anna walks and Bob stands)

If it applies only to a single action, it can be incorporated more naturally:

> Anna does not run towards Bob.

### Restrictions

Restrictions can be used as filters, enforcing specific kinds of restrictions during the matching process.
Currently, 2 kinds of restrictions are recognized:

#### Time restriction

Time restrictions require action to be matched for a sufficient amount of time. They are defined by describing the
required time frame alongside an action:

> Anna walks ___for at least 30 seconds___.  
> Bob is adjacent to Charlie ___for between 1 and 3 minutes___.  
> Charlie must walk towards Anna ___for approximately 10 seconds___.

#### Confidence restriction

Confidence restriction imposes more strict thresholds for the action to be matched.
Currently, only one such restriction is defined - "must":

> Anna must walk towards Bob for at least 30 seconds.

Adding this will filter out matches, where Anna does not walk towards Bob as consistently.

This restriction is valuable, especially in cases where a query contains a conjunction with many actions, in which there
are some which are of higher importance. Alternatively, there may be some parts of a sequence which are crucial to take 
place. 

A good example is [our pickpocketing example](../examples/pickpocket.txt), where "must" is added to check where
Perp must be adjacent to Victim, as the scenario can play out in many ways not necessarily adhering to the query, but
without Perp and Victim coming into contact, there is little reason of suspecting that pickpocketing took place.

### Temporal connectors

We recognize a single temporal connector - sequence. It is defined by using "then" in the grammar and denotes temporal
succession of sub-queries it connects. For example, a query describing two people meeting and talking for some time 
before saying goodbye and leaving each on their own can be rewritten as:

> Anna and Bob are far from each other, then  
> Anna and Bob walk towards each other, then  
> Anna and Bob must be adjacent for each other  
>  and Anna and Bob stand for at least 30 seconds, then  
> Anna and Bob walk away from each other, then  
> Anna and Bob are far from each other.

This query consists of 5 sequentially connected sub-queries, each of which must takes place in its own disjunct time frame.

### Examples

Existing examples of other queries can be found in the folder `examples/`.

## Output - Results

The final set of results is saved as a CSV file where rows correspond to individual matches.

The columns of this CSV are dynamically generated based on the query used for processing:

- Columns 1..n contain IDs of individual actors of the query. Their order is defined by the order in which they appear in the query. Their identifiers are also present in the header.
- Columns n+1..n+m+1 contain timestamps at which sequentially successive sub-queries start. The last column is added to denote when the entire match ends.
- Columns n+m+2..n+m+3 contain nominator and denominator of the final confidence for the match. These confidences can be thought of as a fraction of "conforming time" / "matched time". Simply put, the higher, the better.

## Visualization

Visualization is the optional last step of the process. Once results are generated (or loaded if they already exist), the video previewer starts.

This previewer plays the footage of the provided video in the background while showing its time frame, where the match takes place.

Trajectories which have been matched are signified by colored dots, which are then connected to a legend regarding each trajectory.

The legend consists of the trajectory's role within the query, the action that's currently active, and its detected features.

The video previewer can be controlled by the following set of shortcuts:
- A or LeftArrow - rewind video by 5 seconds
- D or RightArrow - fast-forward video by 5 seconds
- Shift + A - rewind video to the start (of the detected instance)
- Shift + D - fast-forward by 30 seconds
- Space - Pause / Un-pause the video (other shortcuts do not work while the video is paused)
- N - Quit the preview and move to the next detected instance
- Q - Quit the preview entirely
- Tab - Switch between multiple levels of verbosity
  - Hidden - show only video footage
  - Textless - show only dots signifying individual actors
  - Simple - show dots and simple legend including name, action, and actor features
  - All - show dots and full legend including name, action, actor features, and features w.r.t. other actors
