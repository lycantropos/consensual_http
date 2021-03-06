import string
import time
from asyncio import (get_event_loop,
                     sleep)
from operator import add
from typing import (Any,
                    List,
                    Sequence,
                    Tuple)

from consensual.raft import Processor
from hypothesis import strategies
from hypothesis.strategies import SearchStrategy

from .raft_node import RaftNode
from .utils import MAX_RUNNING_NODES_COUNT

data_objects = strategies.data()
heartbeats = strategies.floats(1, 2)
hosts = strategies.just('localhost')
ports_ranges_starts = strategies.integers(4000, 4500)
ports_ranges_lengths = strategies.integers(100, 500)


def to_ports_range(start: int, length: int) -> Sequence[int]:
    assert start > 0
    assert length >= MAX_RUNNING_NODES_COUNT
    return range(start, start + length)


ports_ranges = strategies.builds(to_ports_range,
                                 ports_ranges_starts,
                                 ports_ranges_lengths)
random_seeds = strategies.integers()


def asyncio_waiting_processor(parameters: float) -> None:
    loop = get_event_loop()
    (loop.create_task
     if loop.is_running()
     else loop.run_until_complete)(sleep(parameters))


def waiting_processor(parameters: float) -> None:
    time.sleep(parameters)


plain_paths_letters = strategies.characters(
        whitelist_categories=['Ll', 'Lu', 'Nd', 'Nl', 'No']
)
paths_infixes_letters = plain_paths_letters | strategies.sampled_from(
        string.whitespace + '!"#$&\'()*+,-./:;<=>?@[\\]^_`|~'
)
paths_infixes = strategies.text(paths_infixes_letters,
                                min_size=1)


def to_longer_actions(strategy: SearchStrategy[str]) -> SearchStrategy[str]:
    return strategies.builds(add, strategy, paths_infixes)


plain_actions = strategies.text(plain_paths_letters,
                                min_size=1)
actions = (plain_actions
           | strategies.builds(add,
                               strategies.recursive(plain_actions,
                                                    to_longer_actions),
                               plain_actions))
processors_parameters = {waiting_processor: strategies.floats(-10, 10),
                         asyncio_waiting_processor: strategies.floats(-10, 10)}
processors = strategies.sampled_from(list(processors_parameters))
processors_dicts = strategies.dictionaries(keys=actions,
                                           values=processors)
running_nodes_parameters = strategies.tuples(hosts, ports_ranges,
                                             processors_dicts, random_seeds)
running_nodes_parameters_lists = strategies.lists(
        running_nodes_parameters,
        min_size=1,
        max_size=MAX_RUNNING_NODES_COUNT
)


def to_log_arguments(action_with_processor: Tuple[str, Processor]
                     ) -> SearchStrategy[Tuple[str, Any]]:
    action, processor = action_with_processor
    return strategies.tuples(strategies.just(action),
                             processors_parameters[processor])


def to_log_arguments_lists(node: RaftNode
                           ) -> SearchStrategy[List[Tuple[str, Any]]]:
    return strategies.lists(
            (strategies.sampled_from(list(node.processors.items()))
             .flatmap(to_log_arguments))
            if node.processors
            else strategies.nothing()
    )
