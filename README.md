# ConfigRuleEngine · 配置表规则检查引擎

一套面向游戏策划配置表的**插件式自动化检查引擎**：把"人工盯表"变成"规则自动跑"。

在游戏研发中，策划配置表（物品 / 配方 / 商店 / 掉落 / 活动……）数量多、交叉引用复杂，人工检查极易漏掉"引用了不存在的 ID""数值配置越界""同类配置不一致"这类问题。本项目用一套通用的规则引擎把它们全部交给代码：

- **插件式规则**：每条业务规则是一个 `Check_` 前缀方法的 Python 类，放入 `rule/` 目录即被自动发现并执行，新增规则**零框架改动**
- **自动发现 + 动态加载**：引擎扫描规则目录、动态 import、自动识别规则类，无需注册表
- **统一报告**：逐规则明细报告 + 汇总报告，错误分级（`errs` 必须修复 / `warns` 建议复核）
- **开箱即跑**：内置示例配置表（预埋 6 处典型错误），clone 下来 3 条命令看到完整检查效果

## 架构

```
                ┌──────────────────────────────────────────┐
                │              run_checks.py               │
                │   规则发现 → 动态加载 → 逐规则执行 → 报告  │
                └───────┬──────────────────┬───────────────┘
                        │ 自动扫描          │ 调用
                        ▼                  ▼
              ┌────────────────┐   ┌──────────────────────┐
              │    rule/       │   │       util/          │
              │  item.py       │   │  commontools.py      │
              │  recipe.py     │   │  (跨表引用/空值/数值   │
              │  your_rule.py  │   │   等通用检查原语)      │
              └───────┬────────┘   │  errdata.py (错误模型)│
                      │ 继承        │  logger / transjson  │
                      ▼            └──────────────────────┘
              ┌────────────────┐
              │     data/      │   ┌──────────────────────┐
              │  base_table.py │   │      config/         │
              │ (表读取基类:    │   │  base.py (目录/映射/  │
              │  跳说明行/过滤  │   │  阈值/黑白名单)       │
              │  启用行/ID索引) │   │  local.py (个人覆盖)  │
              └───────┬────────┘   └──────────────────────┘
                      │ 读取
                      ▼
              ┌────────────────┐        ┌──────────────────┐
              │  sample_data/  │        │  monitor/        │
              │  Item.xlsx     │        │  tapd_monitor.py │
              │  Recipe.xlsx   │        │ (模块变更监控+    │
              │ (可换成真实表)  │        │  webhook 通知)   │
              └────────────────┘        └──────────────────┘
```

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 生成示例配置表(预埋 6 处典型配置错误)
python sample_data/make_sample.py

# 3. 运行全部检查
python run_checks.py
```

检查结果输出到 `reports/` 目录：每个规则一份明细报告（`*_report.txt`），外加一份汇总报告 `check_summary.txt`。

### 常见报错排查

| 现象 | 原因 | 处理 |
|---|---|---|
| 提示「缺少运行依赖: pandas / openpyxl / pydantic」 | 依赖未安装或装到了别的 Python 环境 | `pip install -r requirements.txt`；多版本环境用 `python -m pip install -r requirements.txt` 确保装进当前解释器 |
| 汇总报告里「加载模块失败 -> ModuleNotFoundError: ...」 | 规则模块 import 的依赖缺失 | 按提示安装对应包；本项目启动时会做依赖预检，正常情况下不会走到这里 |
| 汇总报告里「加载模块失败 -> SyntaxError: ...」 | 新增的规则文件有语法错误 | 直接单跑该模块定位：`python rule/你的规则.py` |
| 「未找到包含 Check_ 方法的规则类」 | 规则类里没有 `Check_` 前缀方法，或方法名写错 | 检查方法命名，参考 `rule/item.py` |
| 报告里所有规则都 PASS 但明显应该有问题 | 数据目录没指对，读到的是空的 | 检查 `config/local.py` 里的 `RULE_DATA` 路径 |

### 接入真实配置表

```bash
cp config/local.py.example config/local.py
# 编辑 local.py, 把 RULE_DATA 指向真实策划表目录
```

## 如何新增一条规则

三步，不需要碰任何框架代码：

```python
# rule/my_check.py —— 放入 rule/ 目录即生效
from data.base_table import ItemTable
from util.errdata import errdata, allerrs

class MyChecker(ItemTable):          # 1. 继承对应的数据模型(自动获得表数据)

    def Check_Something(self):       # 2. 方法以 Check_ 前缀命名
        '''规则名写在 docstring 里(打印在报告中)'''
        rule_errs = allerrs(rulename='规则名')
        # 3. 遍历数据, 问题进 errs, 疑点进 warns
        for row in self.item.itertuples():
            if row.S物品品质 > 5:
                rule_errs.errs.append(errdata(erritemid=row.Index,
                                              errinfo=f'品质越界: {row.S物品品质}'))
        return rule_errs
```

引擎执行时会自动发现该文件、识别规则类、按代码书写顺序执行全部 `Check_` 方法。

### 规则编写约定

| 约定 | 说明 |
|---|---|
| `Check_` 前缀 | 只有该前缀的方法会被当作规则执行 |
| docstring | 即规则名，直接打印在报告中 |
| `OrderedMeta` | 数据模型基类自带，保证规则按书写顺序执行 |
| `allerrs` 返回值 | `errs` = 必须修复；`warns` = 建议人工复核 |
| `checkfile` 映射 | 规则依赖的表文件在 `config/base.py` 中声明 |

## 内置通用检查原语（util/commontools.py）

写新规则时直接组合这些原语，避免重复造轮子：

| 原语 | 用途 |
|---|---|
| `check_column_inclusion()` | **跨表引用存在性**：源表引用的 ID 是否都存在于目标表 |
| `check_columns_not_empty()` | 批量空值检查，错误信息自动带行号列名 |
| `GetItemandNum()` | 解析 `ID|数量;ID|数量` 复合格式 |
| `CheckVal()` | 判定配置值有效（处理 NaN / 空串 / 数值下限） |
| `is_increasing()` | 列表递增校验（等级梯度、数值曲线） |
| `remove_common_kv_pairs()` | 批量配置差异提取（过滤相同字段，只留差异项） |
| `runRules()` | 单规则调试执行器 |

另有 `transjson.py`：把编辑器导出的 json（带 BOM、字段名含括号）转成 DataFrame / dict。

## 数据模型层（data/base_table.py）

针对策划 Excel 表的常见约定做了统一处理，新表只需声明表头即可复用：

- 表头不在第 1 行（前置说明区），`skiprows` 统一跳过
- 首列为**启用标记**列，带 `*` 的行才生效，读取时自动过滤
- ID 类字段统一转字符串，避免被 pandas 读成 float
- 自动按 ID 列建行索引

## 缺陷管理联动（monitor/tapd_monitor.py）

可选组件：监控缺陷管理系统（TAPD）工作空间的模块变更，与本地快照 diff，新增/移除模块时通过 webhook 推送通知——用于在模块结构变化时及时提醒测试同学维护用例映射。

```bash
export TAPD_API_USER=xxx
export TAPD_API_PASSWORD=xxx
export TAPD_WORKSPACE_ID=xxx
export WEBHOOK_URL=xxx        # 可选
python monitor/tapd_monitor.py
```

配合系统定时任务（crontab / 任务计划程序）即可实现周期监控。所有凭据走环境变量，不落仓库。

## 设计说明

- **为什么是插件式**：检查规则随版本频繁增删，"加规则 = 加文件"让非框架维护者也能安全贡献规则
- **为什么错误分级**：`errs`（确定性错误，阻断）与 `warns`（疑似问题，人工复核）分离，避免误报淹没真问题
- **为什么阈值/黑白名单进配置**：业务阈值随版本调整，规则代码保持稳定
- **报告为纯文本**：方便 diff、归档和贴入缺陷单

## 目录结构

```
ConfigRuleEngine/
├── run_checks.py            # 引擎入口: 规则发现 → 加载 → 执行 → 报告
├── requirements.txt
├── config/                  # 配置层(目录映射/阈值/黑白名单 + 个人覆盖)
├── data/                    # 数据模型层(表读取基类 + 各表模型)
├── rule/                    # 规则插件目录(新增规则放这里)
├── util/                    # 通用工具(检查原语/错误模型/日志/json转换)
├── sample_data/             # 示例配置表 + 生成脚本(预埋错误)
└── monitor/                 # 可选: TAPD 模块变更监控
```

## 声明

本项目为通用能力演示版本：所有数据均为虚构示例，不包含任何真实项目信息。
