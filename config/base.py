import os

from util.get_project_root import PROJECT_ROOT

# ============ 数据目录 ============
# 默认指向仓库内置的 sample_data 示例数据, 保证开箱即跑
# 真实使用时在 config/local.py 中覆盖为本机配置表目录:
#   RULE_DATA = r"D:\your\project\config\excel"
RULE_DATA = os.path.join(PROJECT_ROOT, 'sample_data')

# ============ 规则与配置表的依赖映射 ============
# {规则文件名: {用途: 文件名}}, 主表 key 固定为 'cfg'
# 存在规则依赖多个文件的情况时, 其余依赖文件自行命名 key, 与规则代码中取用一致
checkfile = {
    'item':   {'cfg': 'Item.xlsx'},
    'recipe': {'cfg': 'Recipe.xlsx'},
}

# ============ 业务检查配置(示例) ============
# 物品名称/描述中禁止出现的关键字
NAME_FORBIDDEN_KEYWORDS = ['测试']
DESC_FORBIDDEN_KEYWORDS = ['测试']
# 描述中允许出现上述关键字的完整短语白名单(命中即跳过)
DESC_KEYWORD_WHITELIST = []

# 出售货币白名单与售价预警阈值(阈值需乘以品质档位)
# 配置为空时, 相关规则会自动跳过
CURRENCY_SELL_LIMIT = {
    # '900001': 10000,
}

# 检查黑名单: 跳过检查的条目 ID 列表(临时豁免已知问题用)
CHECK_BLACKLIST = []
