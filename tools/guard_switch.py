"""Hermes 二次开发 — 安全审查机制总开关（本机定制，2026-10-15）。

开关放在 **config.yaml**，不放 `.env`、也不新增 `HERMES_*` 环境变量
（仓库的 code-health 规则 HX002 明确要求行为开关走 config.yaml）：

    security:
      guards_enabled: false    # false = 关闭全部安全审查（本 fork 的默认形态）
                               # true  = 恢复 Hermes 原版行为

切换方式（改完需重启进程/新开会话才生效，与 ``security.redact_secrets`` 同语义）：

    hermes config set security.guards_enabled true      # 回滚到原版
    hermes config set security.guards_enabled false     # 全放行

设计说明：所有补丁点只调用 ``guards_disabled()`` 做一次早返回，不在各处硬编码
True/False，因此恢复原版行为只需改这一个配置项，无需回滚代码。配置在进程内
只读一次（``_CACHE``），避免在 terminal / file 热路径上反复解析 YAML。
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_CACHE: bool | None = None

_TRUTHY = frozenset({"1", "true", "yes", "on", "enable", "enabled", "y", "t"})


def _coerce(raw: object) -> bool:
    """把配置值强制成布尔；缺失/无法识别一律视为「关闭审查」。"""
    if raw is None:
        return False
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() in _TRUTHY


def guards_enabled() -> bool:
    """True = 保留 Hermes 原版安全审查；False = 全部放行（本机默认）。"""
    global _CACHE
    if _CACHE is None:
        try:
            from hermes_cli.config import load_config_readonly

            cfg = load_config_readonly() or {}
            raw = (cfg.get("security") or {}).get("guards_enabled")
        except Exception:
            # 有意的兜底边界：这个函数在 terminal / file 写入等热路径上被调用，
            # 配置读取失败绝不能把整个调用链打挂。按本 fork 的既定形态全放行，
            # 但保留 traceback 便于排查（code-health BLE001 的要求）。
            logger.exception("guard_switch: 读取 security.guards_enabled 失败，按「全放行」处理")
            raw = False
        _CACHE = _coerce(raw)
    return _CACHE


def guards_disabled() -> bool:
    """True 时短路所有安全审查（本机默认）。"""
    return not guards_enabled()
