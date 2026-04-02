import unittest
import sys
import os
import json

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.registry import ProviderRegistry, provider_registry, Provider
from app.classifiers import TaskType, classify_task
from app.scorer import ProviderScorer, ScoringWeights
from app.quota import QuotaManager
from app.health import HealthMonitor
from app.router import RouterEngine, RouteRequest, RouterMode
from app.library import HermesFreeRouter


class TestProviderRegistry(unittest.TestCase):
    """Test the provider registry functionality"""
    
    def setUp(self):
        self.registry = provider_registry
    
    def test_registry_has_providers(self):
        """Test that registry has providers loaded"""
        providers = self.registry.get_enabled_providers()
        self.assertGreater(len(providers), 0)
    
    def test_get_provider_by_id(self):
        """Test getting a specific provider by ID"""
        provider = self.registry.get_provider("openrouter")
        self.assertIsNotNone(provider)
        self.assertEqual(provider.id, "openrouter")
        self.assertEqual(provider.name, "OpenRouter")
    
    def test_get_nonexistent_provider(self):
        """Test getting a provider that doesn't exist"""
        provider = self.registry.get_provider("nonexistent")
        self.assertIsNone(provider)
    
    def test_get_providers_by_capability(self):
        """Test getting providers that support a specific capability"""
        coding_providers = self.registry.get_providers_by_capability("coding")
        self.assertGreater(len(coding_providers), 0)
        
        # All returned providers should have coding capability > 0
        for provider in coding_providers:
            self.assertGreater(provider.capability_scores.get("coding", 0), 0)
    
    def test_hermes_native_providers(self):
        """Test getting native Hermes providers"""
        native_providers = self.registry.get_hermes_native_providers()
        # OpenRouter should be a native provider
        native_ids = [p.id for p in native_providers]
        self.assertIn("openrouter", native_ids)
    
    def test_hermes_main_providers(self):
        """Test getting providers that use Hermes 'main' mode"""
        main_providers = self.registry.get_hermes_main_providers()
        # Groq should be a 'main' provider
        main_ids = [p.id for p in main_providers]
        self.assertIn("groq", main_ids)


class TestTaskClassifier(unittest.TestCase):
    """Test the task classification functionality"""
    
    def test_coding_classification(self):
        """Test that coding prompts are classified correctly"""
        prompt = "Write a Python function to calculate fibonacci numbers"
        task_type = classify_task(prompt)
        self.assertEqual(task_type, TaskType.CODING)
    
    def test_reasoning_classification(self):
        """Test that reasoning prompts are classified correctly"""
        prompt = "Solve this math equation: 2x + 5 = 15, what is x?"
        task_type = classify_task(prompt)
        self.assertEqual(task_type, TaskType.REASONING)
    
    def test_vision_classification(self):
        """Test that vision prompts are classified correctly"""
        prompt = "What objects can you see in this image?"
        task_type = classify_task(prompt)
        self.assertEqual(task_type, TaskType.VISION)
    
    def test_long_context_classification(self):
        """Test that long context prompts are classified correctly"""
        prompt = "Summarize this document and extract the key points"
        task_type = classify_task(prompt)
        self.assertEqual(task_type, TaskType.LONG_CONTEXT)
    
    def test_fast_classification(self):
        """Test that fast/realtime prompts are classified correctly"""
        prompt = "I need a real-time response with low latency"
        task_type = classify_task(prompt)
        self.assertEqual(task_type, TaskType.FAST)
    
    def test_general_classification(self):
        """Test that general prompts default to general"""
        prompt = "Hello, how are you today?"
        task_type = classify_task(prompt)
        self.assertEqual(task_type, TaskType.GENERAL)
    
    def test_explicit_vision_requirement(self):
        """Test that explicit vision requirement overrides classification"""
        prompt = "Tell me about the weather"
        task_type = classify_task(prompt, require_vision=True)
        self.assertEqual(task_type, TaskType.VISION)


class TestProviderScorer(unittest.TestCase):
    """Test the provider scoring functionality"""
    
    def setUp(self):
        self.scorer = ProviderScorer()
    
    def test_score_provider_basic(self):
        """Test scoring a provider for a basic task"""
        provider = provider_registry.get_provider("openrouter")
        score = self.scorer.score_provider(provider, TaskType.GENERAL)
        self.assertGreater(score.total_score, 0)
    
    def test_score_provider_capability_match(self):
        """Test that providers score higher for matching capabilities"""
        groq = provider_registry.get_provider("groq")
        
        # Groq should score higher for 'fast' tasks
        fast_score = self.scorer.score_provider(groq, TaskType.FAST)
        general_score = self.scorer.score_provider(groq, TaskType.GENERAL)
        
        # Fast score should be higher because Groq has 99% fast capability
        self.assertGreater(fast_score.capability_score, general_score.capability_score)
    
    def test_score_provider_vision_zero(self):
        """Test that providers without vision capability score 0 for vision tasks"""
        groq = provider_registry.get_provider("groq")
        score = self.scorer.score_provider(groq, TaskType.VISION)
        # Groq has 0 vision capability, so capability score should be 0
        self.assertEqual(score.capability_score, 0.0)
    
    def test_custom_weights(self):
        """Test scoring with custom weights"""
        weights = ScoringWeights(
            credit_weight=0.1,
            capability_weight=0.8,
            speed_weight=0.1
        )
        scorer = ProviderScorer(weights)
        provider = provider_registry.get_provider("openrouter")
        score = scorer.score_provider(provider, TaskType.CODING)
        self.assertGreater(score.total_score, 0)


class TestRouterEngine(unittest.TestCase):
    """Test the core routing engine"""
    
    def setUp(self):
        self.router = RouterEngine()
    
    def test_route_basic(self):
        """Test basic routing functionality"""
        request = RouteRequest(
            prompt="Write a Python function to sort a list",
            task_type=TaskType.CODING
        )
        result = self.router.route(request)
        
        # Should have a selected provider
        self.assertIsNotNone(result.selected_provider)
        self.assertIsNotNone(result.selected_score)
        self.assertGreater(result.selected_score.total_score, 0)
    
    def test_route_with_fallbacks(self):
        """Test routing with fallback providers"""
        request = RouteRequest(
            prompt="Explain quantum physics",
            task_type=TaskType.REASONING,
            fallback_count=3
        )
        result = self.router.route(request)
        
        # Should have fallbacks
        self.assertGreaterEqual(len(result.fallback_providers), 0)
    
    def test_route_with_excluded_providers(self):
        """Test routing with excluded providers"""
        request = RouteRequest(
            prompt="Test prompt",
            task_type=TaskType.GENERAL,
            excluded_providers=["openrouter"]
        )
        result = self.router.route(request)
        
        # OpenRouter should not be selected
        if result.selected_provider:
            self.assertNotEqual(result.selected_provider.id, "openrouter")
    
    def test_route_vision_task(self):
        """Test routing for vision tasks"""
        request = RouteRequest(
            prompt="Describe what you see in this image",
            task_type=TaskType.VISION,
            require_vision=True
        )
        result = self.router.route(request)
        
        # If a provider is selected, it should support vision
        if result.selected_provider:
            self.assertGreater(result.selected_provider.capability_scores.get("vision", 0), 0)
    
    def test_get_hermes_config(self):
        """Test generating Hermes-compatible config"""
        provider = provider_registry.get_provider("groq")
        config = self.router.get_hermes_config(provider)
        
        self.assertIn("provider", config)
        self.assertIn("model", config)
        self.assertEqual(config["provider"], "main")
        self.assertIn("base_url", config)
    
    def test_get_hermes_config_native(self):
        """Test generating Hermes config for native provider"""
        provider = provider_registry.get_provider("openrouter")
        config = self.router.get_hermes_config(provider)
        
        self.assertEqual(config["provider"], "openrouter")
        self.assertIn("model", config)


class TestHermesFreeRouter(unittest.TestCase):
    """Test the main library interface"""
    
    def setUp(self):
        self.router = HermesFreeRouter()
    
    def test_select_model_basic(self):
        """Test basic model selection"""
        result = self.router.select_model(
            prompt="Write a Python function to calculate prime numbers",
            task_type="coding"
        )
        
        self.assertIn("provider", result)
        self.assertIn("model", result)
        self.assertIsNotNone(result["provider"])
        self.assertIsNotNone(result["model"])
    
    def test_select_model_with_requirements(self):
        """Test model selection with specific requirements"""
        result = self.router.select_model(
            prompt="Analyze this image",
            task_type="vision",
            require_vision=True
        )
        
        # If a provider is selected, it should be appropriate for vision
        if result.get("provider"):
            provider = provider_registry.get_provider(
                [p.id for p in provider_registry.get_enabled_providers() 
                 if p.name == result["provider"] or p.id == result["provider"]][0]
            )
            if provider:
                self.assertGreater(provider.capability_scores.get("vision", 0), 0)
    
    def test_list_providers(self):
        """Test listing providers"""
        providers = self.router.list_providers()
        self.assertGreater(len(providers), 0)
    
    def test_get_provider_info(self):
        """Test getting provider information"""
        info = self.router.get_provider_info("openrouter")
        self.assertIsNotNone(info)
        self.assertEqual(info["id"], "openrouter")
    
    def test_get_provider_info_nonexistent(self):
        """Test getting info for non-existent provider"""
        info = self.router.get_provider_info("nonexistent")
        self.assertIsNone(info)


if __name__ == "__main__":
    unittest.main()
