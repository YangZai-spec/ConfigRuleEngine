# 加载公共配置
from .base import *

# 尝试加载个人配置（有就覆盖，没有就跳过）
# local.py 不入库, 见 local.py.example
try:
    from .local import *
except ImportError:
    pass
