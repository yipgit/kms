import unittest
import asyncio
from src.pipeline.core import Pipeline, PipelineStep

class MockStep(PipelineStep):
    def __init__(self, suffix):
        self.suffix = suffix
    
    async def process(self, data):
        return data + self.suffix

class ErrorStep(PipelineStep):
    async def process(self, data):
        raise ValueError("Boom")

class TestPipelineCore(unittest.IsolatedAsyncioTestCase):
    async def test_pipeline_flow(self):
        pipeline = Pipeline()
        pipeline.add_step(MockStep("A"))
        pipeline.add_step(MockStep("B"))
        
        result = await pipeline.run("Start")
        self.assertEqual(result, "StartAB")

    async def test_pipeline_error(self):
        pipeline = Pipeline()
        pipeline.add_step(MockStep("A"))
        pipeline.add_step(ErrorStep())
        
        with self.assertRaises(ValueError):
            await pipeline.run("Start")
