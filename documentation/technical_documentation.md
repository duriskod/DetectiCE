Technical Documentation
===

DetectiCE is an application responsible for finding user-defined behavioral patterns within video footage. 
It has been developed as a proof-of-concept implementation of an algorithm for detecting complex events.

This implementation has been built on top of an existing actively developed research project for video analysis - 
Videolytics. It uses its central database as a source of input data.

This document contains an overview of the issue at hand, key ideas of the DetectiCE algorithm, and how it tackles 
the problem, its high-level architecture, and its components.

# Prerequisites and environment

DetectiCE is a CLI application written in Python 3. It requires a working version of Python 3 interpreter (developed 
and tested in version 3.12), and a set of modules frozen in [requirements.txt](../requirements.txt), installable via 
the pip's command `pip install -r requirements.txt`.

As mentioned in the introduction, this application has been developed as a part of the Videolytics system, specifically 
its database. This naturally means the input data - video trajectories and features - are expected in the form 
as described by the module responsible for their generation - TraGeD. For more information regarding this format 
and the entire process of extracting features from trajectories in video footage, 
see [TraGeD thesis](https://dspace.cuni.cz/handle/20.500.11956/181573).

With that in mind, it is entirely possible to connect to a different database with an identical structure of relevant 
tables. Alternatively, even changes in DB structure can be accommodated by altering the connector folder of 
this project.

# Application Overview

This algorithm utilizes an algorithm-based approach to detect behavior on so-called semantically enriched trajectories 
using a process similar to pattern matching. Behavioral patterns used for search can be custom-made using restricted 
context-free grammar. Queries conforming to this grammar are encoded into behavioral templates. These are then applied 
to ordered tuples of trajectories enriched with their feature info.

The final output is a set of trajectory tuples where behavior was detected, along with timestamps where each step of 
the pattern took place, and a value signifying a confidence level that this detection is correct.

An optional post-processing step is a visualization of the results using the underlying video footage as a background, 
which is overlaid by the detected trajectories and their features in real-time.

## Queries

Queries are used to describe the desired behavior in a user-friendly, readable manner. They need to conform to custom
context-free grammar as described in the [railway diagram](./behavior_grammar.html).

The general idea of the queries is to describe uniquely named actors, and their actions (i.e., A **walks**, B **moves 
towards** C, C **is far from** D, ...), which can be recursively joined using logical operators (i.e., and, or, not), 
conditioned by time restrictions (i.e., X walks for at least 30 seconds) or priority restrictions (i.e., a **must** 
walk), and perhaps most importantly by connectors signifying temporal succession (i.e., A walks, **then** A runs).

### Internal representation - Behavioral Template

After successfully parsing an incoming query, the query is encoded into a so-called **behavioral template**. 
This template contains a tree-like structure encoding the requirements of the query, able to be later called with 
a tuple of trajectories to determine whether they contain an instance of the desired behavior.

In this behavioral tree, leaf nodes denote individual actions, and internal nodes serve as connectors (logical, 
restricting, and sequential). Notably, the internal nodes may have an arity greater than 2.

## Semantically enriched trajectories

While the detailed formal definition can be found in the thesis, we mention here the conceptual idea of trajectories 
and their semantic representations:

- A **detection** is a detection of an object of interest in a single video frame. Its properties include the frame at 
which it was taken, the corresponding timestamp, position within the frame, and dimensions of its bounding box.
- A **trajectory** is a temporally conjoined set of detections across a set of frames. Gaps are permitted but 
a trajectory may not have multiple detections in a single frame.
- A **semantic representation of a trajectory** is a set of time frames with each time frame containing additional 
information regarding the extracted features of the trajectory. In our specific case, this information includes 
the speed of the trajectory at that time frame and the change of direction.

The specific way the semantic representation is implemented in the database is in the form of **blocks** and 
**descriptors**. Simply put, each block specifies a time frame in which the semantic representation of a trajectory 
is homogenous, meaning the values of features for that trajectory don't change throughout the block. Descriptors 
are then connected to blocks, giving specific values for each kind of feature that is defined.

The extension proposed as a part of this thesis was a semantic representation for pairs of trajectories in a similar 
fashion:

- A **time-aligned detection pair** is a pair of distinct detections within the same frame.
- A **trajectory pair** is simply a pair of trajectories. Notably, we only take interest in those pairs, which overlap 
during some time frame.
- A **semantic representation of a trajectory pair** is analogous to that of trajectories, except it consists namely 
of time frames where both trajectories are present, as otherwise we are unable to compute tuple features. These 
features include qualities such as distance between trajectories, change of this distance, mutual as well as 
one-sided direction, etc.

The implementation of this representation is also done in the same way, using **tuple blocks** and **tuple 
descriptors**. One notable detail here is that features can be asymmetrical, and so we differentiate roles in these 
pairs - **actor** and **target**.

# Project structure

```
behavior/
  data/
    tests/
    agent.py        - Agent and AgentTuple - wrappers around blocks of trajectories and their features
    block.py        - Block - a base class for the internal representation of blocks and their features
    confidence.py   - Confidence - tuple-like structure signifying "fuzzy trueness" 
    enums.py        - Enums used throughout, most importantly those describing feature values
    single_block.py - SingleBlock, inheriting Block for case of singular trajectory blocks
    time_frame.py   - TimeFrame, used to signify optionally bounded time frame (with convenience methods)
    tuple_block.py  - TupleBlock, inheriting Block for case of tuple blocks for trajectory tuples
    variable.py     - BehaviorVariable, a way to give unique identifiers to actors in query and bind them to 
                      specific trajectories during computation
                      
  node/
    base.py        - BehaviorNode - base class for all behavioral nodes
    elementary.py  - ElementaryNode - base class for all elementary nodes (i.e., those matching specific 
                     features). Namely, these are:
                     - StateNode - checks single block features
                     - ActorTargetStateNode - checks asymmetrical tuple block features
                     - MutualStateNode - checks symmetrical tuple block features
    factory.py     - behavioral factory - a set of convenience functions for constructing pre-configured nodes
    logic.py       - LogicNode - base class for all logical nodes, namely ConjunctionNode, DisjunctionNode and NegationNode
    optimize.py    - function responsible for optimizing behavioral trees by removing redundancy and suboptimal structures
    restriction.py - RestrictingNode - base class for all restrictive nodes, namely TimeRestrictingNode and ConfidenceRestrictingNode
    sequential.py  - SequentialNode - node encoding temporal succession of its sub-nodes
  time_graph/
    layer.py      - TimeGraphLayer - base class for time-graph layers produced by nodes, namely:
                    - DenseTimeGraphLayer - produced by ElementaryNode
                    - LambdaTimeGraphLayer - produced by logical and restriction nodes
                    - ContractedTimeGraphLayer - produced by SequentialNode
    time_graph.py - TimeGraph - class used as an intermediate step when computing confidences of a sequential node
    types.py      - set of helper type aliases
  configuration.py - Configuration - holding configurable parameters of a run
  grammar.py       - custom parser and lexer used in parsing behvioral queries
  template.py      - BehavioralTemplate - a wrapper class around the behavioral tree. Responsible for iterating input 
                     trajectories, processing them, and finding detections.
connector/
  loader.py        - BehaviorLoader - responsible for loading necessary data from database
  provider.py      - BehaviorProvider - contains factory methods for setting up presets, such as videos with the 
                     appropriate generation of the feature data
preview/
  video_previewer.py      - VideoPreviewer - class responsible for previewing resulting CSV files of behavior detection in
                            video playbacks

preprocessing/ - partial copy of a detached branch (detached/preprocessing) which contains a stand-alone program
                 for generating tuple features and tuple blocks and storing them into the database
                 
sql/ - contains functions which were created for the purpose of DetectiCE
  get_behavior_data.sql - Function for collecting block data for pre-processing. Includes raw data such as detection positions.
  get_behavior_features.sql - Function for collecting all blocks within a video with their feature values.
  get_tuple_behavior_features.sql - Similar function for collecting all tuple blocks with their feature values.
  get_block_bounds.sql - Function for collecting spatial information regarding blocks. This is used during visualization
                         mostly for debugging purposes.
                         
  timegraph_visualizer.py - set of functions to visualize the time graph processing, mostly used during debugging
main.py - entry-point, contains the top-most logic of setting up the provider, loading data, passing query to grammar,
          letting the template process data, writing results to file and finally starting a preview
```

# Process in detail

Using the general idea of the process from previous sections, we can now introduce individual steps in greater detail:

## Parsing query

Source: [/behavior/grammar.py](../behavior/grammar.py)

Parsing of the input query is done using Python's SLY package. Thanks to the definition of a custom Lexer and Parser, 
the output of this process is a constructed behavioral tree, which is then passed into a new BehavioralTemplate instance.

## Behavioral Template construction

Source: [/behavior/template.py](../behavior/template.py)

During the construction of the behavioral template, 2 important steps take place:

### Behavioral Tree optimization

Source: [/behavior/node/optimize.py - optimize_node](../behavior/node/optimize.py)

The behavioral tree at this point is unoptimized with potentially redundant nodes. An easy example is the binary 
nature of grammar. `A and B and C` will be parsed as a nesting of 2 conjunctions. To remedy this, the tree is passed 
through an `optimize_node` function, which recursively applies a set of fixed rules to reduce the tree until no more 
changes can be made. These rules include but are not limited to flattening identical nested nodes or filtering 
redundant nodes.

### Actor-temporal requirements

Source: [/behavior/node/base.py - BehaviorNode.get_sequence_info](../behavior/node/base.py)

One unfortunate aspect of our algorithm is its theoretical time complexity. Namely, regardless of the complexity of 
the internal decision algorithm (i.e., whether a tuple of trajectories contains an instance of behavior), we need to make 
this decision for each possible tuple of trajectories. This complexity naturally grows exponentially with the number 
of unique actors in the query.

As a result, it is crucial to implement efficient and performant pre-emptive filtering. There are many possible 
approaches to this filtering, but our solution uses the fact that each action needs some minimal time to take place, 
either specified explicitly by a time restricting node or implicitly by some pre-configured value.

Using a simple example, should be set the implicit minimal time requirement per action to 3 seconds, if we consider 
a query containing 3 successive actions (i.e., "A walks, then A stands, then A runs"), we can filter out trajectories, 
which have a duration of less than 9 seconds.

This approach of course only works if each set of concurrent actions contains all actors. For example, a query "A walks, 
then A walks towards B, then A is adjacent to B" again has accumulated an implicit time requirement of 9 seconds, but 
those only apply to "A". "B" must only be present 6 of those seconds.

With these issues in mind, we see we need to consider not only the time restrictions but also specific actors to whom 
they apply. This set of requirements is returned by `BehaviorNode.get_sequence_info`, which returns a list of tuples, 
each tuple specifying "which actors need to be present for how long".

This information can then be used within BehaviorTemplate for quick decisions on whether trajectories can be ignored 
straight away. We call this property "viability" and implement it in `BehaviorTemplate.check_viability`. 

Inside, we try to find whether we can find successive time frames, where trajectories are defined for sufficient time, 
in accordance with the actor-temporal requirement info.

## Behavior search

Source: [/behavior/template.py - BehaviorTemplate.search](../behavior/template.py)

The search of the behavioral pattern is run using a set of semantically enriched trajectories - Agents (and their 
AgentTuples). This set usually equals to that of a whole video.

This whole set is iterated by selecting individual n-tuples, where n is equal to the template's arity (number of unique 
actors in the query). Each n-tuples is first checked for viability, and if it passes, it moves on to the core decision 
process.

## Behavior process

Source: [/behavior/template.py - BehaviorTemplate.process](../behavior/template.py)

When a specific n-tuple is being processed, each of the n trajectories is bound to one agent, in the order they are 
passed into the function.

As these trajectories (and their tuples) are made up of blocks with different features, and all blocks have arbitrary 
time frames, we wish to align these times to be able to process the data in a manner similar to a sliding window. 
Additionally, we want this sliding window to be homogeneous, similar to how individual blocks are, as it makes it much 
easier to work with it. Thus, our only option is to subdivide these blocks as any joining may lead to a violation of 
homogeneity.

### Granularization

Source: [/behavior/data/block.py - Block.granulate](../behavior/data/block.py)

The process of generating sliding windows we call granularization. While the algorithm may seem complicated, the general
idea is quite simple. Take incoming lists of temporally successive blocks (i.e., blocks per trajectory, tuple blocks per 
trajectory pair), and generate sliding windows, where each sliding window starts at the end time of the previous one 
(or the first possible timestamp in the first iteration), and ends at the earliest next bounding time (i.e., any start or 
end time of a block).

Once sliding windows are created, these windows are passed inside the behavioral tree. Each node is responsible for how much
is it satisfied during specific time frames / ranges of windows. We call this measure Confidence and define as follows

#### Confidence

Source: [/behavior/data/confidence.py - Confidence](../behavior/data/confidence.py)

Confidence is a fuzzy measure of trueness. Because we expect noisy or outright missing data at places, we cannot use 
booleans. We need a more fuzzy measure. There is a possibility of using a float in range <0;1> essentially specifying 
"percentage of truth", but we have moved this concept one step further by encoding the time into its value.

Specifically, we define confidence as a tuple (m, a) which essentially serves as a fraction m/a, with a fraction's value 
bounded by 0 <= m/a <= 1. This way, the confidence (m, a) conceptually conveys the information of "(m)atching seconds of 
total (a)ll seconds", which holds both the fuzzy trueness value as well as information regarding time. This is useful 
when trying to avoid short matches caused by noise, and more importantly, prefer longer matches with some noise to much 
shorter matches with no noise.

We additionally define "special" confidences:
- Impartial: c = (0,0) - treated as an additively neutral element. It has "truth value" of 0
- Impossible: c = (C,inf) - with C being any positive real value. This confidence is mostly only added by nodes such 
as restriction nodes to signify a check has failed and computation for this specific time frame can be ended prematurely.
- Absolute: c = (inf, inf) - is the opposite of Impossible and has a truth value of 1. It is used to signify that some time 
frame is necessarily a match. Currently, this specific value serves no use but is conceptually sound if there comes 
a reason for such override value.

Source: [/behavior/data/confidence.py - ConfidenceComparer](../behavior/data/confidence.py)

To make this work, we implement a ConfidenceComparer - a comparer that takes in convex parameter t. Using this 
parameter, two confidences are compared by combining
- accuracy-based comparer - considers fraction m/a
- reliability-based comparer - considers only m

By using this comparer with low (but non-negligible) t, we obtain an ordering of confidences that is still mainly 
determined by their fractional value, but is skewed in apparent cases (i.e., ranking 99/100 higher than 3/3).

### Confidence computation

Source: [/behavior/node/base.py - BehaviorNode.compute_graph_layer](../behavior/node/base.py)

Each node is then responsible for computing its confidence levels for all ranges of windows. For example, a StateNode 
checking Speed equal to WALK will produce confidence (t/t) for a window of time t where trajectory indeed WALKS, 
and (0/t) where it RUNS or STANDS. Similarly, for a list of 20 windows of total time 15s, where trajectory WALKS for 8 
of these windows of total time 5s, the resulting confidence will be (8/15).

Naturally, it is wasteful to compute all of these values eagerly, as many of them won't be ever used. To fix this we 
use so-called TimeGraphLayers (the name will become apparent in the later section), which compute the confidence matrix 
dynamically:
- Dense TGL - keeps confidence per window, sums confidence for a set of windows on-demand, memoizes results
- Lambda TGL - holds a Callable, calls on-demand (i.e., in restriction nodes, the check is made within callable, and if 
passes, calls an underlying Layer)
- Contracted TGL - created by contracting a TimeGraph as mentioned below

### Issue of sequence

Source: [/behavior/node/sequential.py - SequentialNode.compute_graph_layer](../behavior/node/sequential.py)

The computation of the confidence matrix is easy to do in case of most nodes. The one node which isn't as trivial is 
a sequential node. This comes from the fact that in order to compute the confidence of a sequential node for a set of 
windows, one must consider how to distribute these windows between its sequentially successive sub-nodes. For example, 
when a tree corresponding to a query "A walks, then A runs, then A stands" computes its confidence for a set of 
20 windows, it needs to find the confidence as the aggregated confidence of the optimal distribution of these windows. 
Even in this trivial case of 20 windows and 3 sub-nodes, this results in (19 "gaps" over 2 "boundaries") = 
171 of possible distributions.

To solve this issue, we introduce an intermediate step in the computation of the confidence matrix for sequential nodes - 
time graphs.

### Time Graph

Source: [/behavior/time_graph/time_graph.py - TimeGraph.compute](../behavior/time_graph/time_graph.py)

Time graph is a structure with the goal of finding the optimal distribution of windows in-between sub-nodes of 
a sequential node.

It has the form of a grid-like directed acyclic graph. The rows of vertices create boundaries between individual nodes. 
The columns of vertices similarly make up boundaries between windows. All edges then flow from a vertex to one in 
the next row and "anywhere to the right", and their weight is set by the confidence from the confidence matrix of 
the sub-node for the specific set of windows the edge spans through.

After all this is constructed, the process is easy. We can simply iterate row by row, left to right. Each node will 
have a set of the best remembered incoming paths along with their confidences. Once they come to turn, their remembered 
paths are extended by the outgoing edge and are sent to the target vertex. This vertex will merge these new incoming 
paths with any of its existing paths.

One important note here is the way confidences are aggregated. During the computation of all other types of nodes, 
confidences are either averaged, min-ed or max-ed. This is because of their concurrent nature. In case of time graphs, 
the confidence is computed sequentially. I.e., a path containing 4 edges signifies 4 successive sub-behaviors taking 
place without overlap. Our selected way to define sum in this case is in the form of a **mediant**, which is defined 
as the fraction of the sum of nominators over the sum of denominators. Formally:
a/b (+) c/d = (a+c)/(b+d).

This definition fits with our understanding of the confidence itself: "matched time" / "all time". The mediant also 
has a neat property, with it being bound by the original fractions. In other words, the mediant of any confidences will 
be confidence with value in-between them. This additionally keeps it bounded in the range of [0; 1].

Once this process is finished, vertices in the bottom layer hold information on any "good" (w.r.t. configuration) paths, 
with each of these paths signifying an optimal distribution of windows.

### Collecting Time Graph paths

Source: [/behavior/time_graph/time_graph.py - TimeGraph.__backtrack](../behavior/time_graph/time_graph.py)

Once the processing of a time graph is complete, we obtain a set of optimal confidences for our confidence matrix, 
denoted by individual paths in the time graph. These can be obtained by simply taking all vertices in the bottom layer, 
and use their memory to backtrack all of their paths, keeping track of traversed nodes during the process.

When complete, these nodes specify the distribution of windows between sub-nodes, and most importantly can form 
the confidence matrix. Specifically, these confidences are wrapped inside a `ContractedTimeGraphLayer`, which has 
the added functionality of remembering the entire paths.

## Results

Source: [/main.py - save_paths](../main.py)

After the search ends, a set of matches with the highest confidences (w.r.t. our configured comparer) is returned. 
These contain n-tuple of trajectory IDs in fixed order, specifying their mapping to individual actors; the set of 
timestamps bounding individual sub-behaviors within the root sequential node (with an additional timestamp specifying 
the end of the whole match); and finally nominator and denominator of the computed confidence of the path.

## Visualization

Source: [/preview/video_previewer.py - VideoPreviewer](../preview/video_previewer.py)

There is an option for visualizing the produced set of results. These are visualized by default (unless flag '-C' 
is present).

The visualizer is a simple class using OpenCV library to playback a video footage with overlaid information regarding 
matched trajectories, their names, currently on-going sub-behavior (as denoted by timestamps from the time graph 
computation), and extracted features.

# Configuration

Source: [/behavior/configuration.py](../behavior/configuration.py)

Configuration is a set of globally set parameters altering the process:
- min confidence - a threshold below which confidences are stopped early
- max memory - max amount of paths remembered by each vertex in a time graph
- conjunction strategy - how confidences are computed in conjunction. Current supported strategies are average and 
minimum
- confidence coefficient - coefficient used in comparer configuration. When set to 0, comparer is purely confidence-based. When set to 1, it is purely reliability-based.

# Usage

The program can be run by simply running `main.py`:

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

# Testing

Due to the complex nature of the functionality of individual nodes, extensive unit tests are put in place to ensure 
the correctness of the codebase. These tests are written using Python's built-in unittest package and can be run from 
CLI by running

```commandline
python -m unittest discover -s path\to\DetectiCE -t path\to\DetectiCE
```
in Windows, or for Linux as
```bash
python3 -m unittest discover -s path/to/DetectiCE -t path/to/DetectiCE
```
