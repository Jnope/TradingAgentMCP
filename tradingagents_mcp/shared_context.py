"""
MCP 进程级共享上下文

启动时初始化 LLM 一次，所有 Tool 共享复用。
"""

import logging
import os
from typing import Dict, Optional

from tradingagents.dataflows.config import set_config
from tradingagents.llm_clients import create_llm_client
from tradingagents.graph.trading_graph import TradingAgentsGraph

logger = logging.getLogger(__name__)

_shared_ctx: Optional["SharedContext"] = None


class SharedContext:
    """MCP 进程级共享上下文，启动时初始化一次"""

    def __init__(self, config: dict):
        self.config = config
        set_config(config)

        os.makedirs(
            config["data_cache_dir"],
            exist_ok=True,
        )

        provider = config.get("llm_provider", "openai")
        backend_url = config.get("backend_url")

        deep_client = create_llm_client(
            provider=provider,
            model=config["deep_think_llm"],
            base_url=backend_url,
        )
        quick_client = create_llm_client(
            provider=provider,
            model=config["quick_think_llm"],
            base_url=backend_url,
        )

        self.deep_thinking_llm = deep_client.get_llm()
        self.quick_thinking_llm = quick_client.get_llm()

        self._graph_cache: Dict[tuple, TradingAgentsGraph] = {}

        logger.info(
            "SharedContext 初始化完成: provider=%s, deep=%s, quick=%s",
            config.get("llm_provider"),
            config.get("deep_think_llm"),
            config.get("quick_think_llm"),
        )

    def get_graph(self, analysts: list[str], config: dict = None):
        """按 analysts 组合获取/缓存 TradingAgentsGraph

        同一 analysts 组合复用 Graph 实例，避免重复初始化。
        config 中的 max_debate_rounds / max_risk_discuss_rounds 等运行时参数
        通过 ConditionalLogic 在 propagate 时动态生效（见 TradingAgentsGraph）。
        """
        from tradingagents.graph.conditional_logic import ConditionalLogic

        cfg = config or self.config

        key = tuple(sorted(analysts))
        if key not in self._graph_cache:
            self._graph_cache[key] = TradingAgentsGraph(
                selected_analysts=analysts,
                debug=False,
                config=cfg,
            )
            logger.info("SharedContext: 创建并缓存 Graph(analysts=%s)", analysts)
        else:
            logger.info("SharedContext: 复用已缓存 Graph(analysts=%s)", analysts)
            cached = self._graph_cache[key]
            if config:
                cached.config.update(config)
                cached.conditional_logic = ConditionalLogic(
                    max_debate_rounds=config.get("max_debate_rounds", 1),
                    max_risk_discuss_rounds=config.get("max_risk_discuss_rounds", 1),
                )
        return self._graph_cache[key]

    def invalidate(self):
        """清除 Graph 缓存，下次 get_graph 时重建"""
        self._graph_cache.clear()
        logger.info("SharedContext: Graph 缓存已清除")


def get_shared_ctx() -> SharedContext:
    """获取/创建 SharedContext 单例

    首次调用时创建，后续复用。配置变化时需调用 invalidate_shared_ctx()。
    """
    global _shared_ctx
    if _shared_ctx is None:
        from tradingagents_mcp.validators import build_config

        _shared_ctx = SharedContext(build_config())
    return _shared_ctx


def invalidate_shared_ctx():
    """清除 SharedContext 单例，下次 get_shared_ctx 时重建"""
    global _shared_ctx
    _shared_ctx = None
    logger.info("SharedContext 单例已清除")
