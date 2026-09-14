import asyncio
import copy
import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import main


class BriefingTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.context = SimpleNamespace(
            response_id="resp_test",
            is_recovery=False,
            persisted_response=None,
            shutdown=asyncio.Event(),
            exit_for_recovery=AsyncMock(),
            get_input_text=AsyncMock(return_value="Assess battery recycling for a Swiss manufacturer."),
        )
        self.request = main.CreateResponse(input="Assess battery recycling.")
        self.cancellation = asyncio.Event()
        self.delay = patch.object(main, "DEMO_STAGE_DELAY_SECONDS", 0)
        self.crash = patch.object(main, "CRASH_AFTER", None)
        self.delay.start()
        self.crash.start()
        self.addCleanup(self.delay.stop)
        self.addCleanup(self.crash.stop)

    async def collect(self):
        return [event async for event in main.handler(self.request, self.context, self.cancellation)]

    async def test_sections_use_previous_results(self):
        calls = []

        async def generate(stage_index, user_request, sections):
            calls.append((stage_index, user_request, list(sections)))
            return f"Business output {stage_index}"

        with patch.object(main, "_generate_stage", side_effect=generate):
            events = await self.collect()
        output = events[-1]["response"]["output"]
        self.assertEqual(len(output), 3)
        self.assertEqual([len(call[2]) for call in calls], [0, 1, 2])
        self.assertIn("## Decision brief", output[-1]["content"][0]["text"])
        self.context.get_input_text.assert_awaited_once()

    async def test_recovery_reuses_sections_and_original_item_ids(self):
        stream = main.ResponseEventStream(response_id="resp_test", request=self.request)
        stream.emit_created()
        stream.emit_in_progress()
        list(stream.output_item_message("## Risk assessment\n\nSaved evidence gaps."))
        snapshot = copy.deepcopy(stream.response)
        original_id = snapshot["output"][0]["id"]
        self.context.is_recovery = True
        self.context.persisted_response = snapshot
        calls = []

        async def generate(stage_index, user_request, sections):
            calls.append((stage_index, list(sections)))
            return "Resumed business output"

        with patch.object(main, "_generate_stage", side_effect=generate):
            events = await self.collect()
        self.assertEqual([call[0] for call in calls], [1, 2])
        self.assertIn("Saved evidence gaps.", calls[0][1][0])
        self.assertEqual(events[-1]["response"]["output"][0]["id"], original_id)
        self.assertEqual(len(events[-1]["response"]["output"]), 3)

    async def test_steering_cancels_inflight_model_without_committing_it(self):
        entered = asyncio.Event()
        stopped = asyncio.Event()

        async def generate(*args):
            entered.set()
            try:
                await asyncio.Event().wait()
            finally:
                stopped.set()

        with patch.object(main, "_generate_stage", side_effect=generate):
            collection = asyncio.create_task(self.collect())
            await asyncio.wait_for(entered.wait(), timeout=2)
            self.cancellation.set()
            events = await asyncio.wait_for(collection, timeout=2)
        self.assertTrue(stopped.is_set())
        self.assertEqual(len(events[-1]["response"]["output"]), 1)
        self.assertIn("Work stopped", events[-1]["response"]["output"][0]["content"][0]["text"])

    async def test_pre_cancelled_turn_does_not_call_model(self):
        self.cancellation.set()
        with patch.object(main, "_generate_stage", new_callable=AsyncMock) as model:
            await self.collect()
        model.assert_not_called()

    async def test_shutdown_defers_to_recovery_without_completing(self):
        self.context.shutdown.set()
        with patch.object(main, "_generate_stage", new_callable=AsyncMock) as model:
            events = await self.collect()
        model.assert_not_called()
        self.context.exit_for_recovery.assert_awaited_once()
        self.assertFalse(any(event.get("type") == "response.completed" for event in events))

    async def test_model_error_propagates(self):
        with patch.object(main, "_generate_stage", side_effect=RuntimeError("model unavailable")):
            with self.assertRaisesRegex(RuntimeError, "model unavailable"):
                await self.collect()

    async def test_empty_request_is_rejected(self):
        self.context.get_input_text.return_value = " "
        with self.assertRaisesRegex(ValueError, "sourcing decision"):
            await self.collect()

    async def test_model_client_contract_and_incomplete_output(self):
        credential = AsyncMock()
        project = AsyncMock()
        client = AsyncMock()
        credential.__aenter__.return_value = credential
        project.__aenter__.return_value = project
        client.__aenter__.return_value = client
        response = SimpleNamespace(status="completed", output_text="  Conditional recommendation  ")
        client.responses.create.return_value = response
        with patch.dict(main.os.environ, {
            "FOUNDRY_PROJECT_ENDPOINT": "https://example.invalid/api/projects/test",
            "AZURE_AI_MODEL_DEPLOYMENT_NAME": "test-model",
        }), patch.object(main, "DefaultAzureCredential", return_value=credential), \
                patch.object(main, "AIProjectClient", return_value=project), \
                patch.object(project, "get_openai_client", new=Mock(return_value=client)):
            result = await main._generate_stage(2, "A sourcing decision", ["Evidence gaps"])
            self.assertEqual(result, "Conditional recommendation")
            arguments = client.responses.create.call_args.kwargs
            self.assertEqual(arguments["model"], "test-model")
            self.assertFalse(arguments["store"])
            self.assertEqual(json.loads(arguments["input"])["previous_sections"], ["Evidence gaps"])
            response.status = "incomplete"
            with self.assertRaisesRegex(RuntimeError, "incomplete"):
                await main._generate_stage(2, "A sourcing decision", [])


if __name__ == "__main__":
    unittest.main()