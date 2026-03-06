from abc import ABC, abstractmethod
from typing import Any, List, TypeVar, Generic
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')
U = TypeVar('U')

class PipelineStep(ABC):
    """Abstract base class for a pipeline step."""
    
    @abstractmethod
    async def process(self, data: Any) -> Any:
        """Process the data and return the transformed data."""
        pass

class Pipeline:
    """Manages a sequence of processing steps."""
    
    def __init__(self):
        self.steps: List[PipelineStep] = []

    def add_step(self, step: PipelineStep):
        self.steps.append(step)
        return self

    async def run(self, data: Any) -> Any:
        """Run the data through all steps in order."""
        current_data = data
        for step in self.steps:
            try:
                current_data = await step.process(current_data)
            except Exception as e:
                logger.error(f"Error in pipeline step {step.__class__.__name__}: {e}")
                raise
        return current_data
