'''
示例规则 1: 物品表通用检查

演示的规则编写约定:
1. 规则类继承数据模型类(获得表数据), 并以 OrderedMeta 保证执行顺序;
2. 检查方法以 Check_ 前缀命名, docstring 即规则名(会打印在报告中);
3. 每个检查方法返回 allerrs 对象, 错误进 errs, 疑点进 warns。
'''
import os
import sys
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))
from util.logger import get_logger
from util.commontools import CheckVal, runRules
from data.base_table import ItemTable
from util.errdata import errdata, allerrs
from config import NAME_FORBIDDEN_KEYWORDS, DESC_FORBIDDEN_KEYWORDS, DESC_KEYWORD_WHITELIST, CURRENCY_SELL_LIMIT, CHECK_BLACKLIST

logger = get_logger(__name__)


class ItemChecker(ItemTable):

    def __init__(self, **kwargs):
        super().__init__()
        self.blackid = list(CHECK_BLACKLIST)

    def Check_ItemName(self):
        '''
        检查物品名称不应包含禁用关键字
        '''
        rule_errs = allerrs(rulename='物品名称不应包含禁用关键字')
        for rowdata in self.item.itertuples():
            idx = rowdata.Index
            itemname = rowdata.C物品名称
            if idx in self.blackid:
                logger.info("物品ID %s %s 位于检查黑名单中, 跳过检查！", idx, itemname)
                continue

            for kw in NAME_FORBIDDEN_KEYWORDS:
                if kw in str(itemname):
                    err_data = errdata(erritemid=idx, errinfo=f'物品 {itemname} 名称包含禁用关键字 "{kw}"!')
                    rule_errs.errs.append(err_data)

        return rule_errs

    def Check_ItemDesc(self):
        '''
        检查物品描述不应包含禁用关键字(支持白名单短语豁免)
        '''
        rule_errs = allerrs(rulename='物品描述不应包含禁用关键字')
        for rowdata in self.item.itertuples():
            idx = rowdata.Index
            itemname = rowdata.C物品名称
            if idx in self.blackid:
                logger.info("物品ID %s %s 位于检查黑名单中, 跳过检查！", idx, itemname)
                continue

            itemdesc = str(rowdata.D物品描述)
            for kw in DESC_FORBIDDEN_KEYWORDS:
                if kw not in itemdesc:
                    continue
                # 白名单短语命中则跳过
                if any(ok in itemdesc for ok in DESC_KEYWORD_WHITELIST):
                    logger.info("物品ID %s %s 的描述包含白名单短语, 跳过检查！", idx, itemname)
                    continue
                err_data = errdata(erritemid=idx, errinfo=f'物品 {itemname} 的描述信息 {itemdesc} 包含禁用关键字 "{kw}"!')
                rule_errs.errs.append(err_data)

        return rule_errs

    def Check_ItemPrice(self):
        '''
        检查物品出售价格合理性(按货币类型配置阈值, 阈值需乘以品质档位)
        '''
        rule_errs = allerrs(rulename='物品售价超过阈值')
        if not CURRENCY_SELL_LIMIT:
            logger.warning("未配置 CURRENCY_SELL_LIMIT, 跳过本规则!")
            return rule_errs

        for rowdata in self.item.itertuples():
            idx = rowdata.Index
            itemname = rowdata.C物品名称
            if idx in self.blackid:
                logger.info("物品ID %s %s 位于检查黑名单中, 跳过检查！", idx, itemname)
                continue

            if not CheckVal(rowdata.M能否出售):
                logger.info("物品ID %s %s 配置为不可出售, 跳过检查！", idx, itemname)
                continue

            itemprice = rowdata.P出售获得物品数量
            item_costtype = str(rowdata.N出售获得物品ID)
            if item_costtype not in CURRENCY_SELL_LIMIT:
                err_data = errdata(erritemid=idx, errinfo=f'物品 {itemname} 的出售货币 {item_costtype} 不在白名单中!')
                rule_errs.errs.append(err_data)
                continue

            itemlv = rowdata.S物品品质
            if not CheckVal(itemlv):
                logger.warning("物品ID %s %s 未配置品质值, 强行按品质1处理！", idx, itemname)
                itemlv = 1

            if itemprice > itemlv * CURRENCY_SELL_LIMIT[item_costtype]:
                err_data = errdata(erritemid=idx, errinfo=f'物品 {itemname}, 品质 {int(itemlv)} 的出售所得 {itemprice} 超过阈值!')
                rule_errs.errs.append(err_data)

        return rule_errs

    def Check_WarehouseLimit(self):
        '''
        配置了仓库上限的物品, 必须同时配置超量转换的目标条目
        '''
        rule_errs = allerrs(rulename='存在上限配置的物品必须有超量转换配置')

        for rowdata in self.item.itertuples():
            idx = rowdata.Index
            itemname = rowdata.C物品名称
            if idx in self.blackid:
                logger.info("物品ID %s %s 位于检查黑名单中, 跳过检查！", idx, itemname)
                continue

            warehouseLimit = rowdata.J物品仓库数量上限
            # 上限 >= 1 才视为 "配置了仓库上限", 0/空/NaN 均视为未配置
            if not CheckVal(warehouseLimit, 1):
                logger.info("物品ID %s %s 未配置仓库上限, 跳过检查！", idx, itemname)
                continue

            iOverConvertItemID = rowdata.W超量转换物品ID
            if not CheckVal(iOverConvertItemID, 0):
                err_data = errdata(erritemid=idx, errinfo=f'物品 {itemname} 未配置超量转换条目, 或配置错误!')
                rule_errs.errs.append(err_data)

        return rule_errs

    def Check_WarehouseLimit_ConvertNum(self):
        '''
        存在超量转换配置的物品, 转换数量必须大于等于0
        '''
        rule_errs = allerrs(rulename='存在超量转换配置的物品, 转换数量必须大于等于0')

        for rowdata in self.item.itertuples():
            idx = rowdata.Index
            itemname = rowdata.C物品名称
            if idx in self.blackid:
                logger.info("物品ID %s %s 位于检查黑名单中, 跳过检查！", idx, itemname)
                continue

            warehouseLimit = rowdata.J物品仓库数量上限
            # 上限 >= 1 才视为 "配置了仓库上限", 0/空/NaN 均视为未配置
            if not CheckVal(warehouseLimit, 1):
                logger.info("物品ID %s %s 未配置仓库上限, 跳过检查！", idx, itemname)
                continue

            iOverConvertItemNum = rowdata.Y超量转换物品数量
            if not CheckVal(iOverConvertItemNum, 0):
                err_data = errdata(erritemid=idx, errinfo=f'物品 {itemname} 未配置超量转换数量, 或数值错误!')
                rule_errs.errs.append(err_data)

        return rule_errs

    @staticmethod
    def _NormalizeNonFungibleVal(val):
        '''
        将 "是否非同质化" 类字段的值归一化: NaN/None/空 与 0 视为相同, 统一返回 0, 其余非 0 值返回 1
        '''
        if val is None:
            return 0
        if isinstance(val, float) and val != val:  # NaN
            return 0
        if isinstance(val, str):
            val = val.strip()
            if val == '' or val.lower() in ('nan', 'none', 'null'):
                return 0
        try:
            return 0 if float(val) == 0 else 1
        except (TypeError, ValueError):
            return val

    def Check_AttrConsistencyInType(self):
        '''
        同一类型下的所有条目, 其同质化属性配置必须一致(以多数值为预期, 少数派报错)
        '''
        rule_errs = allerrs(rulename='同一类型下的条目同质化属性必须一致')

        typecol = 'E物品类型ID'
        nftcol = 'U是否非同质化道具'
        if typecol not in self.item.columns or nftcol not in self.item.columns:
            logger.warning('物品表中不存在 %s 或 %s 列, 跳过检查！', typecol, nftcol)
            return rule_errs

        # 按类型归集条目: {类型ID: [(条目ID, 条目名称, 类型描述, 归一化后的属性值), ...]}
        typeitems = {}
        for rowdata in self.item.itertuples():
            idx = rowdata.Index
            itemname = getattr(rowdata, 'C物品名称', '')
            if idx in self.blackid:
                logger.info("物品ID %s %s 位于检查黑名单中, 跳过检查！", idx, itemname)
                continue

            itemtype = getattr(rowdata, typecol, None)
            if itemtype is None or (isinstance(itemtype, float) and itemtype != itemtype) or str(itemtype).strip() == '':
                logger.info("物品ID %s %s 未配置类型, 跳过检查！", idx, itemname)
                continue
            itemtype = str(itemtype).strip()

            nftflag = self._NormalizeNonFungibleVal(getattr(rowdata, nftcol, None))
            typedesc = getattr(rowdata, 'F类型描述', '')
            typeitems.setdefault(itemtype, []).append((idx, itemname, typedesc, nftflag))

        for itemtype, items in typeitems.items():
            # 统计该类型下出现过的属性值, NaN 与 0 已归一化为 0
            flagcnt = {}
            for _, _, _, flag in items:
                flagcnt[flag] = flagcnt.get(flag, 0) + 1

            if len(flagcnt) <= 1:
                continue

            # 以该类型下出现次数最多的值作为预期值, 其余配置不一致的条目全部记录为错误
            expectedflag = None
            for flag, cnt in flagcnt.items():
                if expectedflag is None or cnt > flagcnt[expectedflag]:
                    expectedflag = flag
            typedesc = items[0][2]
            for idx, itemname, _, flag in items:
                if flag == expectedflag:
                    continue
                err_data = errdata(erritemid=idx,
                                   errinfo=f'条目 {itemname} 所属类型 {itemtype}_{typedesc} 下所有条目的同质化属性应保持一致, 预期为 {expectedflag}, 但该条目配置为 {flag}, 请检查!')
                rule_errs.errs.append(err_data)

        return rule_errs


if __name__ == '__main__':
    bc = ItemChecker()
    runRules(bc)
