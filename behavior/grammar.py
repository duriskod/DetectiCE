import re
import sys
from datetime import timedelta

from .data import AgentVariable, Speed, DistanceChange, Direction, MutualDirection, Distance, RelativeTimeFrame
from .node import (BehaviorNode, StateNode, TimeRestrictingNode, ConjunctionNode, ActorTargetStateNode, NegationNode,
                   DisjunctionNode, SequentialNode, MutualStateNode, Factory, ConfidenceRestrictingNode)
from sly import Lexer, Parser

sys.path.insert(0, '../../..')


class QueryError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class BehaviorLexer(Lexer):
    tokens = {
        THEN, MUST,
        IS, WALK, RUN, STAND, MOVE,
        STRAIGHT, LEFT, RIGHT, OPPOSITE,
        TOWARDS, FROM, WITH,
        MUT_PARALLEL, MUT_INDEPENDENT, MUT_OPPOSITE,
        FAR, NEAR, ADJACENT,
        AT_LEAST, AT_MOST, APPROX, BETWEEN, FOR,
        AND, OR, NOT,
        TIME_UNIT,
        LPAR, RPAR,
        EACH_OTHER,
        NUMBER, LABEL, ACTOR
    }
    ignore = ' ,\t.'

    # Temporal connectors
    THEN = r'then'

    # Confidence restrictions
    MUST = r'must'

    # Bounds
    AT_LEAST = r'at least'
    AT_MOST = r'at most'
    APPROX = r'approximately|about|cca'
    FOR = r'for'
    BETWEEN = r'between'

    # Actions
    IS = r'is|are|be'
    WALK = r'walk(s)?'
    RUN = r'run(s)?'
    STAND = r'stand(s)?'
    MOVE = r'move(s)?'

    # Absolute direction
    STRAIGHT = r'straight'
    LEFT = r'(to the )?left( of)?'
    RIGHT = r'(to the )?right( of)?'
    OPPOSITE = r'opposite( to)?'

    # Relative direction
    TOWARDS = r'towards'
    FROM = r'from|away from'
    WITH = r'with|alongside'

    # Mutual direction
    MUT_PARALLEL = r'in parallel|in the same direction'
    MUT_INDEPENDENT = r'independent(ly| of each other)'
    MUT_OPPOSITE = r'in opposite directions'

    # Relative distance
    FAR = r'far from'
    NEAR = r'near to|near'
    ADJACENT = r'adjacent to'

    # Logical connectors
    AND = r'and'
    OR = r'or'
    NOT = r'not|do not|does not'
    # OF = r'of'
    # TO = r'to'

    # Precedence
    LPAR = r'\('
    RPAR = r'\)'

    TIME_UNIT = r'seconds|minutes|hours'

    EACH_OTHER = r'each other'

    # Variable tokens
    NUMBER = r'\d+'
    LABEL = r'\[[a-zA-Z_][a-zA-Z0-9_ ]*\]'
    ACTOR = r'[a-zA-Z_][a-zA-Z0-9_]*'

    # Ignored pattern
    ignore_newline = r'\n+'

    # Extra action for newlines
    def ignore_newline(self, t):
        self.lineno += t.value.count('\n')

    def error(self, t):
        print("Illegal character '%s'" % t.value[0])
        self.index += 1


class BehaviorParser(Parser):
    tokens = BehaviorLexer.tokens

    # debugfile = 'parser.out'

    def get_agent(self, name: str) -> AgentVariable:
        if name not in self.agents:
            self.agents[name] = AgentVariable(name)
        return self.agents[name]

    def get_actor_name(self, actors: list[AgentVariable], i: int | None = None) -> str:
        if i is None:
            return ', '.join([actor.name for actor in actors])
        return actors[i].name

    precedence = (
        ('left', THEN),
        ('right', LABEL),
        ('left', OR),
        ('left', AND),
        ('right', NOT),
    )

    def error(self, token):
        if token is None:
            raise QueryError(f"Unexpected EOF")
        raise QueryError(f"Encountered invalid token '{token.value}' at position [{token.lineno}, {token.index}]")

    def __init__(self):
        self.agents: dict[str, AgentVariable] = {}

    # region Behavior ::= (Behavior (THEN|AND|OR)|NOT) Behavior  |  LPAR Behavior RPAR  |  Action TimeSpanBounds?

    @_('LABEL behavior')
    def behavior(self, p):
        print(f"Labelling {p.behavior} with {p.LABEL}.")
        p.behavior.name = p.LABEL
        return p.behavior

    @_('behavior THEN behavior')
    def behavior(self, p):
        return SequentialNode(p.behavior0, p.behavior1)

    @_('behavior AND behavior')
    def behavior(self, p):
        return ConjunctionNode([p.behavior0, p.behavior1])

    @_('behavior OR behavior')
    def behavior(self, p):
        return DisjunctionNode([p.behavior0, p.behavior1])

    @_('NOT behavior')
    def behavior(self, p):
        return NegationNode(p.behavior)

    @_('LPAR behavior RPAR optional_timespan_bounds')
    def behavior(self, p):
        node = p.behavior
        if p.optional_timespan_bounds is not None:
            node = TimeRestrictingNode(p.behavior, p.optional_timespan_bounds)
        return node

    @_('action optional_timespan_bounds')
    def behavior(self, p):
        node = p.action

        if p.optional_timespan_bounds is not None:
            node = TimeRestrictingNode(p.action, p.optional_timespan_bounds)
        return node

    # endregion

    # region Action ::= actors optional_negation ... STAND | IS | moving_speed ... ACTOR | EACH_OTHER
    @_('actors optional_priority optional_negation STAND')
    def action(self, p):
        node = StateNode(p.actors, speed=Speed.STAND)
        if p.optional_negation:
            node = NegationNode(node)
        if p.optional_priority:
            node = ConfidenceRestrictingNode(node)
        return node

    @_('actors optional_priority IS optional_negation relative_distance ACTOR',
       'actors optional_priority IS optional_negation relative_distance EACH_OTHER')
    def action(self, p):
        actors = [*p.actors]
        if hasattr(p, 'ACTOR'):
            actors.append(self.get_agent(p.ACTOR))

        node = MutualStateNode(actors, distance=p.relative_distance)

        if p.optional_negation:
            node = NegationNode(node)
        if p.optional_priority:
            node = ConfidenceRestrictingNode(node)

        if hasattr(p, 'EACH_OTHER') and len(p.actors) <= 1:
            raise QueryError(f"Multiple actors required in 'each other' action: '{node}'")

        return node

    @_('actors optional_priority optional_negation STAND relative_distance ACTOR',
       'actors optional_priority optional_negation STAND relative_distance EACH_OTHER')
    def action(self, p):
        actors = [*p.actors]
        if hasattr(p, 'ACTOR'):
            actors.append(self.get_agent(p.ACTOR))

        node = ConjunctionNode([
            StateNode(p.actors, speed=Speed.STAND),
            MutualStateNode(actors, distance=p.relative_distance)
        ])

        if p.optional_negation:
            node = NegationNode(node)
        if p.optional_priority:
            node = ConfidenceRestrictingNode(node)

        if hasattr(p, 'EACH_OTHER') and len(p.actors) <= 1:
            raise QueryError(f"Multiple actors required in 'each other' action: '{node}'")

        return node

    @_('actors optional_priority optional_negation moving_speed')
    def action(self, p):
        node = Factory.MovingState(p.actors, p.moving_speed)
        if p.optional_negation:
            node = NegationNode(node)
        if p.optional_priority:
            node = ConfidenceRestrictingNode(node)
        return node

    @_('actors optional_priority optional_negation moving_speed absolute_direction')
    def action(self, p):
        node = Factory.MovingState(p.actors, speeds=p.moving_speed, direction=p.absolute_direction)
        if p.optional_negation:
            node = NegationNode(node)
        if p.optional_priority:
            node = ConfidenceRestrictingNode(node)
        return node

    @_('actors optional_priority optional_negation moving_speed absolute_direction ACTOR')
    def action(self, p):
        node = ConjunctionNode([
            Factory.MovingState(p.actors, p.moving_speed),
            *[ActorTargetStateNode([actor, self.get_agent(p.ACTOR)],
                                   relative_direction=p.absolute_direction)
              for actor in p.actors]
        ])
        if p.optional_negation:
            node = NegationNode(node)
        if p.optional_priority:
            node = ConfidenceRestrictingNode(node)
        return node

    @_('actors optional_priority optional_negation moving_speed mutual_direction')
    def action(self, p):
        node = ConjunctionNode([
            Factory.MovingState(p.actors, p.moving_speed),
            MutualStateNode(p.actors, mutual_direction=p.mutual_direction)
        ])
        # node = MutualStateNode(p.actors, mutual_direction=p.mutual_direction)
        if p.optional_negation:
            node = NegationNode(node)
        if p.optional_priority:
            node = ConfidenceRestrictingNode(node)

        if len(p.actors) <= 1:
            raise QueryError(f"Multiple actors required in action: '{node}'")

        return node

    @_('actors optional_priority optional_negation moving_speed relative_direction EACH_OTHER')
    def action(self, p):
        intent_dist, _ = p.relative_direction
        node = ConjunctionNode([
            Factory.MovingState(p.actors, p.moving_speed),
            MutualStateNode(p.actors, distance_change=intent_dist)
        ])
        if p.optional_negation:
            node = NegationNode(node)
        if p.optional_priority:
            node = ConfidenceRestrictingNode(node)

        if hasattr(p, 'EACH_OTHER') and len(p.actors) <= 1:
            raise QueryError(f"Multiple actors required in 'each other' action: '{node}'")

        return node

    @_('actors optional_priority optional_negation moving_speed relative_direction ACTOR')
    def action(self, p):
        intent_dist, relative_dir = p.relative_direction
        target = self.get_agent(p.ACTOR)
        node = ConjunctionNode([
            Factory.MovingState(p.actors, p.moving_speed),
            *[ActorTargetStateNode([actor, target],
                                   intended_distance_change=intent_dist,
                                   relative_direction=relative_dir)
              for actor in p.actors]
        ])
        if p.optional_negation:
            node = NegationNode(node)
        if p.optional_priority:
            node = ConfidenceRestrictingNode(node)
        return node

    # endregion

    # region OptionalPriority ::= MUST?
    @_('MUST')
    def optional_priority(self, p):
        return True

    @_('empty')
    def optional_priority(self, p):
        return False

    # endregion

    # region OptionalNegation ::= NOT?
    @_('NOT')
    def optional_negation(self, p):
        return True

    @_('empty')
    def optional_negation(self, p):
        return False

    # endregion

    # region MovingSpeed ::= (WALK | RUN | MOVE)
    @_('WALK')
    def moving_speed(self, p):
        return Speed.WALK

    @_('RUN')
    def moving_speed(self, p):
        return Speed.RUN

    @_('MOVE')
    def moving_speed(self, p):
        return [Speed.WALK, Speed.RUN]

    # endregion

    # region AbsoluteDirection ::= (LEFT|STRAIGHT|RIGHT|OPPOSITE)
    @_('LEFT')
    def absolute_direction(self, p):
        return Direction.LEFT

    @_('STRAIGHT')
    def absolute_direction(self, p):
        return Direction.STRAIGHT

    @_('RIGHT')
    def absolute_direction(self, p):
        return Direction.RIGHT

    @_('OPPOSITE')
    def absolute_direction(self, p):
        return Direction.OPPOSITE

    # endregion

    # region RelativeDirection ::= (TOWARDS | FROM | WITH)
    @_('TOWARDS')
    def relative_direction(self, p):
        return DistanceChange.DECREASING, Direction.STRAIGHT

    @_('FROM')
    def relative_direction(self, p):
        return DistanceChange.INCREASING, Direction.OPPOSITE

    @_('WITH')
    def relative_direction(self, p):
        return DistanceChange.CONSTANT, None

    # endregion

    # region MutualDirection (PARALLEL | INDEPENDENT | OPPOSITE)
    @_('MUT_PARALLEL')
    def mutual_direction(self, p):
        return MutualDirection.PARALLEL

    @_('MUT_INDEPENDENT')
    def mutual_direction(self, p):
        return MutualDirection.INDEPENDENT

    @_('MUT_OPPOSITE')
    def mutual_direction(self, p):
        return MutualDirection.OPPOSITE

    # endregion

    # region RelativeDistance ::= (FAR | NEAR | ADJACENT)
    @_('FAR')
    def relative_distance(self, p):
        return Distance.FAR

    @_('NEAR')
    def relative_distance(self, p):
        return Distance.NEAR

    @_('ADJACENT')
    def relative_distance(self, p):
        return Distance.ADJACENT

    # endregion

    # region TimeSpan Bounds ::= (FOR (AT_LEAST|AT_MOST|APPROX) NUMBER TIME_UNIT)?
    @_('FOR timespan_bounds')
    def optional_timespan_bounds(self, p):
        return p.timespan_bounds

    @_('empty')
    def optional_timespan_bounds(self, p):
        return None

    @_('AT_LEAST timespan')
    def timespan_bounds(self, p):
        return RelativeTimeFrame(minimal=p.timespan)

    @_('AT_MOST timespan')
    def timespan_bounds(self, p):
        return RelativeTimeFrame(maximal=p.timespan)

    @_('APPROX timespan')
    def timespan_bounds(self, p):
        return RelativeTimeFrame(minimal=0.8 * p.timespan, maximal=1.2 * p.timespan)

    @_('BETWEEN timespan AND timespan')
    def timespan_bounds(self, p):
        return RelativeTimeFrame(minimal=p.timespan0, maximal=p.timespan1)

    @_('BETWEEN NUMBER AND NUMBER TIME_UNIT')
    def timespan_bounds(self, p):
        min_bound = timedelta(**{p.TIME_UNIT: int(p.NUMBER0)})
        max_bound = timedelta(**{p.TIME_UNIT: int(p.NUMBER1)})
        return RelativeTimeFrame(minimal=min_bound, maximal=max_bound)

    @_('NUMBER TIME_UNIT')
    def timespan(self, p):
        return timedelta(**{p.TIME_UNIT: int(p.NUMBER)})

    # endregion

    # region Actors ::= (Actors AND)? Actor
    @_('actors AND ACTOR')
    def actors(self, p):
        p.actors.append(self.get_agent(p.ACTOR))
        return p.actors

    @_('actors ACTOR')
    def actors(self, p):
        p.actors.append(self.get_agent(p.ACTOR))
        return p.actors

    @_('ACTOR')
    def actors(self, p):
        return [self.get_agent(p.ACTOR)]

    # endregion

    @_('')
    def empty(self, p):
        return None


def parse_behavior(text: str) -> BehaviorNode:
    lexer = BehaviorLexer()
    parser = BehaviorParser()
    return parser.parse(lexer.tokenize(text))


if __name__ == '__main__':
    lexer = BehaviorLexer()
    parser = BehaviorParser()
    while True:
        try:
            text = input(' > ')
        except EOFError:
            break
        if text:
            parsed = parser.parse(lexer.tokenize(text))
            print(parsed)
