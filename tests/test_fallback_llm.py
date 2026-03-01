"""
Tests for fallback LLM chain.
Verifies automatic failover to backup LLM on rate limits and provider errors.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch, MagicMock


class TestInvokeWithFallback:
    """Test _invoke_with_fallback behavior in both agents."""

    @pytest.fixture
    def mock_settings(self):
        """Patch settings for testing."""
        with patch('core.planner.settings') as mock_s:
            mock_s.GROQ_API_KEY = "test-key"
            mock_s.LLM_MODEL = "test-model"
            mock_s.LLM_TEMPERATURE = 0.1
            mock_s.ENABLE_LLM_FALLBACK = True
            mock_s.FALLBACK_LLM_MODEL = "fallback-model"
            mock_s.FALLBACK_LLM_API_KEY = "fallback-key"
            mock_s.MAX_AGENT_STEPS = 10
            mock_s.ENABLE_SELF_CORRECTION = True
            mock_s.MAX_CORRECTION_ATTEMPTS = 2
            mock_s.AGENT_HISTORY_LENGTH = 5
            yield mock_s

    @pytest.fixture
    def mock_agent(self, mock_settings):
        """Create a DynamicAutomationAgent with mocked LLMs."""
        with patch('core.planner.ChatGroq') as MockChatGroq:
            # Create distinct mock LLM instances
            primary_llm = AsyncMock()
            fallback_llm = AsyncMock()
            MockChatGroq.side_effect = [primary_llm, fallback_llm]
            
            from core.planner import DynamicAutomationAgent
            agent = DynamicAutomationAgent()
            agent.llm = primary_llm
            agent._fallback_llm = fallback_llm
            agent._using_fallback = False
            
            return agent, primary_llm, fallback_llm

    def test_primary_llm_success(self, mock_agent):
        """Should use primary LLM when it succeeds."""
        agent, primary, fallback = mock_agent
        
        mock_response = Mock()
        mock_response.content = "response"
        primary.ainvoke = AsyncMock(return_value=mock_response)
        
        result = asyncio.get_event_loop().run_until_complete(
            agent._invoke_with_fallback([{"role": "user", "content": "test"}])
        )
        
        assert result == mock_response
        primary.ainvoke.assert_called_once()
        fallback.ainvoke.assert_not_called()
    
    def test_fallback_on_rate_limit(self, mock_agent):
        """Should switch to fallback on 429 rate limit."""
        agent, primary, fallback = mock_agent
        
        primary.ainvoke = AsyncMock(side_effect=Exception("429 Too Many Requests"))
        fallback_response = Mock()
        fallback_response.content = "fallback response"
        fallback.ainvoke = AsyncMock(return_value=fallback_response)
        
        result = asyncio.get_event_loop().run_until_complete(
            agent._invoke_with_fallback([{"role": "user", "content": "test"}])
        )
        
        assert result == fallback_response
        assert agent._using_fallback is True

    def test_fallback_on_server_error(self, mock_agent):
        """Should switch to fallback on 500 server error."""
        agent, primary, fallback = mock_agent
        
        primary.ainvoke = AsyncMock(side_effect=Exception("500 Internal Server Error"))
        fallback_response = Mock()
        fallback_response.content = "fallback response"
        fallback.ainvoke = AsyncMock(return_value=fallback_response)
        
        result = asyncio.get_event_loop().run_until_complete(
            agent._invoke_with_fallback([{"role": "user", "content": "test"}])
        )
        
        assert result == fallback_response
        assert agent._using_fallback is True

    def test_fallback_on_quota_exceeded(self, mock_agent):
        """Should switch to fallback on quota error."""
        agent, primary, fallback = mock_agent
        
        primary.ainvoke = AsyncMock(side_effect=Exception("quota exceeded"))
        fallback_response = Mock()
        fallback_response.content = "fallback response"
        fallback.ainvoke = AsyncMock(return_value=fallback_response)
        
        result = asyncio.get_event_loop().run_until_complete(
            agent._invoke_with_fallback([{"role": "user", "content": "test"}])
        )
        
        assert result == fallback_response

    def test_no_fallback_on_non_provider_error(self, mock_agent):
        """Should re-raise non-provider errors without trying fallback."""
        agent, primary, fallback = mock_agent
        
        primary.ainvoke = AsyncMock(side_effect=ValueError("Invalid JSON"))
        
        with pytest.raises(ValueError, match="Invalid JSON"):
            asyncio.get_event_loop().run_until_complete(
                agent._invoke_with_fallback([{"role": "user", "content": "test"}])
            )
        
        fallback.ainvoke.assert_not_called()

    def test_both_llms_fail(self, mock_agent):
        """Should raise fallback error when both fail."""
        agent, primary, fallback = mock_agent
        
        primary.ainvoke = AsyncMock(side_effect=Exception("429 rate limit"))
        fallback.ainvoke = AsyncMock(side_effect=Exception("Fallback also failed"))
        
        with pytest.raises(Exception, match="Fallback also failed"):
            asyncio.get_event_loop().run_until_complete(
                agent._invoke_with_fallback([{"role": "user", "content": "test"}])
            )

    def test_no_fallback_configured(self, mock_agent):
        """Should re-raise provider error when no fallback is configured."""
        agent, primary, _ = mock_agent
        agent._fallback_llm = None
        
        primary.ainvoke = AsyncMock(side_effect=Exception("429 rate limit"))
        
        with pytest.raises(Exception, match="429 rate limit"):
            asyncio.get_event_loop().run_until_complete(
                agent._invoke_with_fallback([{"role": "user", "content": "test"}])
            )

    def test_primary_recovery(self, mock_agent):
        """Should switch back to primary when it recovers."""
        agent, primary, fallback = mock_agent
        agent._using_fallback = True  # Simulate previous failover
        
        mock_response = Mock()
        mock_response.content = "primary is back"
        primary.ainvoke = AsyncMock(return_value=mock_response)
        
        result = asyncio.get_event_loop().run_until_complete(
            agent._invoke_with_fallback([{"role": "user", "content": "test"}])
        )
        
        assert result == mock_response
        assert agent._using_fallback is False  # Switched back


class TestCreateFallbackLLM:
    """Test _create_fallback_llm factory."""

    def test_no_fallback_when_disabled(self):
        """Should return None when fallback is disabled."""
        with patch('core.planner.settings') as mock_s:
            mock_s.GROQ_API_KEY = "test-key"
            mock_s.LLM_MODEL = "test-model"
            mock_s.ENABLE_LLM_FALLBACK = False
            mock_s.FALLBACK_LLM_MODEL = "fallback-model"
            mock_s.FALLBACK_LLM_API_KEY = "fallback-key"
            mock_s.MAX_AGENT_STEPS = 10
            mock_s.ENABLE_SELF_CORRECTION = True
            mock_s.MAX_CORRECTION_ATTEMPTS = 2
            mock_s.AGENT_HISTORY_LENGTH = 5
            
            with patch('core.planner.ChatGroq') as MockChatGroq:
                MockChatGroq.return_value = Mock()
                from core.planner import DynamicAutomationAgent
                agent = DynamicAutomationAgent()
                assert agent._fallback_llm is None

    def test_no_fallback_when_model_empty(self):
        """Should return None when fallback model is empty."""
        with patch('core.planner.settings') as mock_s:
            mock_s.GROQ_API_KEY = "test-key"
            mock_s.LLM_MODEL = "test-model"
            mock_s.ENABLE_LLM_FALLBACK = True
            mock_s.FALLBACK_LLM_MODEL = ""
            mock_s.FALLBACK_LLM_API_KEY = ""
            mock_s.MAX_AGENT_STEPS = 10
            mock_s.ENABLE_SELF_CORRECTION = True
            mock_s.MAX_CORRECTION_ATTEMPTS = 2
            mock_s.AGENT_HISTORY_LENGTH = 5
            
            with patch('core.planner.ChatGroq') as MockChatGroq:
                MockChatGroq.return_value = Mock()
                from core.planner import DynamicAutomationAgent
                agent = DynamicAutomationAgent()
                assert agent._fallback_llm is None
