'''
示例规则 2: 配方表跨表引用检查

演示通用能力中最常用的一类规则——跨表引用存在性检查:
配方表中出现的物品 ID, 必须都能在物品表中找到。
投入/产出列表采用 "ID|数量;ID|数量" 的复合格式, 由 GetItemandNum 解析。
'''
import os
import sys
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))
from util.logger import get_logger
from util.commontools import CheckVal, GetItemandNum, check_column_inclusion, runRules
from data.base_table import ItemTable, RecipeTable
from util.errdata import errdata, allerrs
from config import CHECK_BLACKLIST

logger = get_logger(__name__)


class RecipeChecker(RecipeTable):
    '''组合物品表数据, 对配方表做引用与数值检查'''

    def __init__(self, **kwargs):
        super().__init__()
        # 配方规则依赖物品表数据, 组合进来
        self.items = ItemTable(self.cfgdatadir).item
        self.blackid = list(CHECK_BLACKLIST)

    def _parse_list_field(self, val):
        '''解析 "ID:num;ID:num" 复合字段, 格式非法时抛出 ValueError'''
        if not CheckVal(val):
            return {}
        return GetItemandNum(val)

    def Check_RecipeItemsExist(self):
        '''
        配方中引用的全部物品 ID 必须存在于物品表
        '''
        rule_errs = allerrs(rulename='配方引用的物品必须存在于物品表')

        item_ids_set = set(self.items.index.astype(str))

        for rowdata in self.recipe.itertuples():
            idx = rowdata.Index
            recipename = rowdata.C配方名称
            if idx in self.blackid:
                logger.info("配方ID %s %s 位于检查黑名单中, 跳过检查！", idx, recipename)
                continue

            for field, fieldname in ((rowdata.D投入物品列表, '投入'), (rowdata.E产出物品列表, '产出')):
                try:
                    items = self._parse_list_field(field)
                except ValueError as e:
                    err_data = errdata(erritemid=idx, errinfo=f'配方 {recipename} 的{fieldname}列表格式非法: {e}')
                    rule_errs.errs.append(err_data)
                    continue

                for itemid in items:
                    if itemid not in item_ids_set:
                        err_data = errdata(erritemid=idx, errinfo=f'配方 {recipename} 的{fieldname}物品 {itemid} 在物品表中不存在!')
                        rule_errs.errs.append(err_data)

        return rule_errs

    def Check_RecipeNumValid(self):
        '''
        配方投入/产出数量必须为非负整数(格式非法即报错)
        '''
        rule_errs = allerrs(rulename='配方投入/产出数量必须合法')

        for rowdata in self.recipe.itertuples():
            idx = rowdata.Index
            recipename = rowdata.C配方名称
            if idx in self.blackid:
                logger.info("配方ID %s %s 位于检查黑名单中, 跳过检查！", idx, recipename)
                continue

            for field, fieldname in ((rowdata.D投入物品列表, '投入'), (rowdata.E产出物品列表, '产出')):
                try:
                    items = self._parse_list_field(field)
                except ValueError as e:
                    err_data = errdata(erritemid=idx, errinfo=f'配方 {recipename} 的{fieldname}数量配置非法: {e}')
                    rule_errs.errs.append(err_data)
                    continue

                for itemid, num in items.items():
                    if num < 0:
                        err_data = errdata(erritemid=idx, errinfo=f'配方 {recipename} 的{fieldname}物品 {itemid} 数量为 {num}, 不应为负!')
                        rule_errs.errs.append(err_data)

        return rule_errs

    def Check_RecipeEmpty(self):
        '''
        已启用的配方, 投入与产出不允许同时为空
        '''
        rule_errs = allerrs(rulename='已启用配方的投入与产出不允许同时为空')

        for rowdata in self.recipe.itertuples():
            idx = rowdata.Index
            recipename = rowdata.C配方名称
            if idx in self.blackid:
                logger.info("配方ID %s %s 位于检查黑名单中, 跳过检查！", idx, recipename)
                continue

            inputs = CheckVal(rowdata.D投入物品列表)
            outputs = CheckVal(rowdata.E产出物品列表)
            if not inputs and not outputs:
                err_data = errdata(erritemid=idx, errinfo=f'配方 {recipename} 已启用, 但投入与产出均为空!')
                rule_errs.errs.append(err_data)

        return rule_errs

    def Check_RecipeUnlockLevel(self):
        '''
        配方解锁等级必须为非负数
        '''
        rule_errs = allerrs(rulename='配方解锁等级必须为非负数')

        for rowdata in self.recipe.itertuples():
            idx = rowdata.Index
            recipename = rowdata.C配方名称
            if idx in self.blackid:
                logger.info("配方ID %s %s 位于检查黑名单中, 跳过检查！", idx, recipename)
                continue

            level = rowdata.G解锁等级
            if not CheckVal(level, 0):
                err_data = errdata(erritemid=idx, errinfo=f'配方 {recipename} 的解锁等级 {level} 配置非法!')
                rule_errs.errs.append(err_data)

        return rule_errs


if __name__ == '__main__':
    bc = RecipeChecker()
    runRules(bc)
