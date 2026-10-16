import os
import sys
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))
import pandas as pd
from util.logger import get_logger
from util.commontools import OrderedMeta
from config import RULE_DATA

logger = get_logger(__name__)


class BaseTable(metaclass=OrderedMeta):
    '''
    通用配置表读取基类。

    针对策划 Excel 表的常见约定做了统一处理:
    - 表头不在第 1 行(前面有若干行说明), 通过 skiprows 跳过;
    - 首列为 "启用标记" 列, 带 * 号的行才是生效配置, 读取时统一过滤;
    - ID 类字段统一以字符串类型存储, 避免 pandas 把数字 ID 读成 float。

    子类按自身表的列结构定义 titles / dtypes, 调用 read_table() 即可拿到
    已过滤、已按 ID 建索引的 DataFrame。
    '''

    # 子类覆盖: 表头定义(与列一一对应)
    titles = None
    # 子类覆盖: 需要按字符串读取的列名集合
    str_cols = ()
    # 子类覆盖: 启用标记列名
    enable_col = 'A启用标记'

    def __init__(self, cfgdatadir=None):
        if cfgdatadir is None:
            self.cfgdatadir = RULE_DATA
        else:
            self.cfgdatadir = cfgdatadir

    def read_table(self, filename, sheet_name=0, usecols=None, skiprows=8):
        '''
        读取一张约定格式的配置表:
        - 跳过前 skiprows 行说明文字, 使用自定义表头
        - 只保留启用标记列为 * 的生效行(同时过滤表头行与未启用行)
        - 按 self.str_cols 指定列强制转 str
        - 以第一个 "B" 开头的列(通常是 ID 列)作为行索引
        '''
        assert self.titles is not None, "子类必须定义 titles 表头"

        df = pd.read_excel(os.path.join(self.cfgdatadir, filename),
                           sheet_name=sheet_name,
                           skiprows=skiprows,
                           header=None,
                           usecols=usecols,
                           names=self.titles,
                           engine="openpyxl")

        # 只保留启用标记为 * 的行(字母表头行与未启用行一并过滤)
        df = df[df[self.enable_col] == '*'].reset_index(drop=True)

        # ID 类列统一转字符串
        for col in self.str_cols:
            if col in df.columns:
                df[col] = df[col].astype(str)

        # 以第一个 B 开头的列作为索引(约定 B 列为条目 ID)
        id_cols = [c for c in df.columns if str(c).startswith('B')]
        if id_cols:
            df = df.set_index(id_cols[0])
        return df


# ============================================================================
# 示例数据模型: 物品表
# 列结构来自常见的策划物品表约定, 按需增删
# ============================================================================
class ItemTable(BaseTable):
    '''物品表数据模型: Item.xlsx / sheet: ItemNode'''

    titles = [
        'A启用标记', 'B物品ID', 'C物品名称', 'D物品描述', 'E物品类型ID', 'F类型描述',
        'G物品二级类型ID', 'H二级类型描述', 'I单元格显示数量上限', 'J物品仓库数量上限',
        'K是否隐藏', 'L能否使用', 'M能否出售', 'N出售获得物品ID', 'O出售获得物品描述',
        'P出售获得物品数量', 'Q物品标签', 'R物品图片', 'S物品品质',
        'T是否开启专属展示', 'U是否非同质化道具', 'V获取方式列表',
        'W超量转换物品ID', 'X转换物品描述', 'Y超量转换物品数量',
    ]
    str_cols = ('B物品ID', 'E物品类型ID', 'G物品二级类型ID', 'N出售获得物品ID', 'W超量转换物品ID')

    def __init__(self, cfgdatadir=None):
        super().__init__(cfgdatadir)
        self.item = self.read_table('Item.xlsx', sheet_name='ItemNode', usecols='A:Y')


# ============================================================================
# 示例数据模型: 配方表
# ============================================================================
class RecipeTable(BaseTable):
    '''配方表数据模型: Recipe.xlsx / sheet: RecipeNode'''

    titles = [
        'A启用标记', 'B配方ID', 'C配方名称', 'D投入物品列表', 'E产出物品列表',
        'F配方类型', 'G解锁等级',
    ]
    str_cols = ('B配方ID',)

    def __init__(self, cfgdatadir=None):
        super().__init__(cfgdatadir)
        self.recipe = self.read_table('Recipe.xlsx', sheet_name='RecipeNode', usecols='A:G')
