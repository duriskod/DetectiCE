from .base import BehaviorNode
from .logic import ConjunctionNode, DisjunctionNode, NegationNode, LogicalNode
from .restriction import TimeRestrictingNode
from .sequential import SequentialNode

from ..data import RelativeTimeFrame


def optimize_node(node: BehaviorNode) -> BehaviorNode:
    """
    Optimization function used to optimize behavioral tree. This optimization may deform original node and its subtree.
    :param node: Node to be optimized.
    :return: Potentially altered node.
    """

    is_changed = False
    node.children = [optimize_node(child) for child in node.children]

    if isinstance(node, SequentialNode):
        for i, child in enumerate(node.children):
            if isinstance(child, SequentialNode):
                # Flattening sequential nesting
                node.children[i:i + 1] = child.children
                node.name = node.name or child.name
                is_changed = True
                print("Applied optimization: SEQ1 > SEQ2 ~~> SEQ")

    if isinstance(node, TimeRestrictingNode):
        child = node.children[0]
        if isinstance(child, TimeRestrictingNode):
            # TIME > TIME ~~> intersection
            #     TimeRestriction( TimeRestriction ( Elementary, 5, 20), 10, 25)
            # ~~> TimeRestriction( Elementary, 10, 20)
            intersected_timeframe = node.time_requirement.intersect(child.time_requirement)
            is_changed = True
            print("Applied optimization: TIME > TIME ~~> INTERSECTED")
            node = TimeRestrictingNode(child.children[0], intersected_timeframe, name=node.name or child.name)

    if isinstance(node, ConjunctionNode):
        intersected_timeframe = RelativeTimeFrame()
        for i, child in enumerate(node.children):
            # AND > TIME ~~> intersection TIME > AND
            #     "Matej walks towards Rene for at least 5 seconds and Rene walks towards Matej for at least 10 seconds"
            # ~~> "(Matej walks towards Rene and Rene walks towards Matej) for at least 10 seconds"
            if isinstance(child, TimeRestrictingNode):
                intersected_timeframe = intersected_timeframe.intersect(child.time_requirement)
                node.children[i] = child.children[0]

            if isinstance(child, ConjunctionNode):
                # Flattening conjunction nesting
                node.children[i:i + 1] = child.children
                is_changed = True
                print("Applied optimization: CONJ1 > CONJ2 ~~> CONJ")

        if intersected_timeframe != RelativeTimeFrame():
            is_changed = True
            print("Applied optimization: AND > TIME ~~> INTERSECTED > AND")
            node = TimeRestrictingNode(node, intersected_timeframe, name=node.name)

    if isinstance(node, DisjunctionNode):
        for i, child in enumerate(node.children):
            if isinstance(child, DisjunctionNode):
                # Flattening disjunction nesting
                node.children[i:i + 1] = child.children
                node.name = node.name or child.name
                is_changed = True
                print("Applied optimization: DISJ1 > DISJ2 ~~> DISJ")

    if isinstance(node, LogicalNode):
        for i in range(len(node.children) - 1):
            for j in range(len(node.children) - 1, i, -1):
                if node.children[i] == node.children[j]:
                    # Removing identical nodes
                    node.children.pop(j)
                    is_changed = True
                    print("Applied optimization: LOGIC > (NODE, NODE) ~~> LOGIC > (NODE)")

    if isinstance(node, LogicalNode):
        is_conjunction = isinstance(node, ConjunctionNode)
        children_to_delete = []
        for i in range(len(node.children)):
            for j in range(len(node.children)):
                if i == j:
                    continue

                if node.children[i].is_subset(node.children[j]):
                    if is_conjunction:
                        # In conjunction, remove node with less information
                        children_to_delete.append(i)
                    else:
                        # In disjunction, remove node with more information
                        children_to_delete.append(j)

        if children_to_delete:
            node.children = [child for i, child in enumerate(node.children) if i not in children_to_delete]
            is_changed = True
            print("Applied optimization: LOGIC > (NODE, SUBSET_NODE) ~~> LOGIC > (NODE)")

    if isinstance(node, NegationNode):
        # Removal of double negative
        child = node.children[0]
        if isinstance(child, NegationNode):
            grandchild = child.children[0]
            grandchild.name = grandchild.name or node.name
            node = grandchild
            is_changed = True
            print("Applied optimization: NEG1 > NEG2 > NODE ~~> NODE")

    if is_changed:
        node = optimize_node(node)

    return node
