from collections import defaultdict

from behavior import Agent
from connector.provider import BehaviorProvider
from preprocessing.connector.data_loader import DataBehaviorLoader
from preprocessing.data.data_agent import DataAgent


class DataBehaviorProvider(BehaviorProvider):
    agents: dict[int, Agent]
    fps: int

    @staticmethod
    def from_db(connection, camera: int, generation: int, model: int):
        loader = DataBehaviorLoader(connection, camera, generation, model)
        return DataBehaviorProvider.__from_behavior_loader(loader)

    @staticmethod
    def __from_behavior_loader(loader: DataBehaviorLoader):
        provider = DataBehaviorProvider()
        data = [item for item in loader.data()]

        data_by_traj = defaultdict(list)
        for record in data:
            data_by_traj[record['trajectory']].append(record)

        provider.fps = loader.fps

        provider.agents = {key: DataAgent.from_block_data(key, val) for key, val in data_by_traj.items()}
        return provider
