#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
缺陷管理系统模块变更监控（通用版）

定期拉取指定工作空间的模块列表, 与本地快照做 diff:
- 新增模块 → 通知
- 删除模块 → 通知
- 无变化 → 静默

变更时向 webhook 推送消息(消息体兼容常见 IM 机器人的 text 格式)。
所有敏感配置通过环境变量注入, 不落仓库:

    TAPD_API_USER      # API 账号(company_api_user)
    TAPD_API_PASSWORD  # API 密码
    TAPD_WORKSPACE_ID  # 要监控的工作空间 ID
    WEBHOOK_URL        # 通知 webhook 地址(可选, 未配置时仅打印)
    SNAPSHOT_FILE      # 本地快照文件路径(默认 ./modules.txt)
"""

import os
import sys
from typing import Set

import requests


class ModuleChangeMonitor:
    """缺陷管理系统模块变更监控器"""

    API_BASE = "https://api.tapd.cn"

    def __init__(self, api_user: str, api_password: str, workspace_id: str,
                 webhook_url: str = "", snapshot_file: str = "./modules.txt") -> None:
        self.auth = (api_user, api_password)
        self.workspace_id = workspace_id
        self.webhook_url = webhook_url
        self.snapshot_file = snapshot_file

    # ---------- 远端数据 ----------

    def get_remote_modules(self) -> Set[str]:
        """拉取远端模块列表(自动分页)"""
        modules: Set[str] = set()
        page = 1
        while True:
            resp = requests.get(
                f"{self.API_BASE}/modules",
                auth=self.auth,
                params={"workspace_id": self.workspace_id, "limit": 200, "page": page},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json().get("data", [])
            if not data:
                break
            for module_data in data:
                modules.add(module_data["Module"]["name"])
            if len(data) < 200:
                break
            page += 1
        return modules

    # ---------- 本地快照 ----------

    def get_local_modules(self) -> Set[str]:
        """读取本地模块快照, 文件不存在时返回空集"""
        try:
            with open(self.snapshot_file, 'r', encoding='utf-8') as file:
                return set(line.strip() for line in file if line.strip())
        except FileNotFoundError:
            print(f'本地快照 {self.snapshot_file} 不存在, 将创建新文件')
            return set()

    def save_local_modules(self, modules: Set[str]) -> None:
        """保存模块快照到本地"""
        with open(self.snapshot_file, 'w', encoding='utf-8') as file:
            file.write('\n'.join(sorted(modules)))

    # ---------- 通知 ----------

    def notify(self, message: str) -> None:
        """推送变更通知, 未配置 webhook 时仅打印"""
        print(message)
        if not self.webhook_url:
            print("(未配置 WEBHOOK_URL, 仅打印不推送)")
            return
        payload = {"msgtype": "text", "text": {"content": message}}
        try:
            resp = requests.post(self.webhook_url, json=payload, timeout=30)
            resp.raise_for_status()
            print("通知已推送")
        except requests.RequestException as e:
            print(f"通知推送失败: {e}", file=sys.stderr)

    # ---------- 主流程 ----------

    def check_once(self) -> bool:
        """执行一次检查, 有变更返回 True"""
        remote = self.get_remote_modules()
        local = self.get_local_modules()

        added = remote - local
        removed = local - remote

        if not added and not removed:
            print(f"模块无变化, 共 {len(remote)} 个")
            return False

        lines = [f"[模块变更通知] workspace {self.workspace_id}"]
        if added:
            lines.append("新增模块: " + ", ".join(sorted(added)))
        if removed:
            lines.append("移除模块: " + ", ".join(sorted(removed)))
        self.notify("\n".join(lines))

        self.save_local_modules(remote)
        return True


def main():
    api_user = os.environ.get("TAPD_API_USER", "")
    api_password = os.environ.get("TAPD_API_PASSWORD", "")
    workspace_id = os.environ.get("TAPD_WORKSPACE_ID", "")
    webhook_url = os.environ.get("WEBHOOK_URL", "")
    snapshot_file = os.environ.get("SNAPSHOT_FILE", "./modules.txt")

    if not (api_user and api_password and workspace_id):
        print("请先设置环境变量: TAPD_API_USER / TAPD_API_PASSWORD / TAPD_WORKSPACE_ID", file=sys.stderr)
        sys.exit(1)

    monitor = ModuleChangeMonitor(api_user, api_password, workspace_id, webhook_url, snapshot_file)
    monitor.check_once()


if __name__ == '__main__':
    main()
