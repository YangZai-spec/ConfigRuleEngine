'''提供一些通用工具函数'''
import sys
import os
from pathlib import Path

import pandas as pd

from config import RULE_DATA, checkfile
from util.errdata import allerrs
from util.logger import get_logger

logger = get_logger()


# 定义一个元类, 用来记录 check 规则类中规则的顺序
# 脚本执行规则检查的时候, 期望能按代码中规则的顺序执行, 默认 dir() 获取的顺序不符合预期
class OrderedMeta(type):
    def __new__(cls, name, bases, classdict):
        classdict['__ordered__'] = [key for key in classdict.keys() if callable(classdict[key])]
        return type.__new__(cls, name, bases, classdict)


def calculate_length(text):
    '''
    一个粗略的计算字符串长度的方法, 把双字节计为长度2, 单字节长度1
    '''
    length = 0
    for char in text:
        # 双字节字符指 Unicode 码位 > 255 的字符（简化规则）
        if ord(char) > 255:
            length += 2
        else:
            length += 1
    return length


def myprint(k, v, printtype, output=sys.stdout):
    sp = ": "
    tabkey = '--- '
    if printtype <= 1:
        print(f"{k}{sp}{v}", file=output)
    elif printtype == 2:
        print(f"{k}{sp}", file=output)
        for m in v:
            print(f"{tabkey}{m}", file=output)
    elif printtype == 3:
        print(f"{k}{sp}", file=output)
        for m in v:
            print(f"{tabkey}{m}{sp}", file=output)
            print(tabkey*2+str(v[m]), file=output)


def GetprinttypeAndPint(dic, output=sys.stdout):
    '''按检查结果的类型选择合适的打印格式输出'''
    assert isinstance(dic, (dict, allerrs)), "传入参数类型非法"
    dictype = 0
    if isinstance(dic, allerrs):
        dic = dic.model_dump()
        dictype = 1

    if not dic:
        print('PASS', file=output)
        return

    if dictype == 1:
        if not dic['errs'] and not dic['warns']:
            print('PASS', file=output)
            return

    printtype = 0
    for k in dic:
        if isinstance(dic[k], (str, int)):
            printtype = 1
        elif isinstance((dic[k]), list):
            printtype = 2
        elif isinstance(dic[k], (dict, tuple)):
            printtype = 3
        myprint(k, dic[k], printtype, output)


def CheckVal(val, min_val=None):
    '''
    判定配置值是否有效:
    val 可能为 np.nan 或空字符串, 此时返回 False;
    如果为整数或浮点数, 无 min_val 时大于等于 0 返回 True, 有 min_val 时大于等于 min_val 返回 True;
    非空字符串返回 True, 其余情况返回 False
    '''
    if isinstance(val, str):
        return True if val else False
    if isinstance(val, (int, float)):
        if min_val is None:
            return val >= 0
        return val >= min_val
    return False


def get_filelst_indir(dirpath, pattern, skipfiles=None):
    '''
    获取指定目录下的文件列表, 当 skipfiles 非空时, 将排除其中的文件
    pattern 类似通配符表达式
    返回列表成员为 pathlike 对象列表, 包含完整路径, 如需纯文件名, 可取其 name 属性
    pattern 大小写不敏感, 不递归子文件夹, 如需要可修改 glob 为 rglob
    '''
    path = Path(dirpath)
    # 使用glob方法查找当前目录下所有匹配的文件, 不遍历子目录, 大小写不敏感
    filelist = list(path.glob(pattern))
    return [f for f in filelist if f not in skipfiles] if skipfiles else filelist


def GetItemandNum(pfdata, itemsplit=';', cfgsplit='|'):
    '''
    解析配置表中类似 '10001:5;10002:5;' 的 "ID:数量" 复合格式, 解析为 {id: num} 的字典
    num 的语义在不同字段下不相同, 可能为数量、产量、权重等, 此处要求必须为整数(允许负值代表特殊语义, 如 -1 代表不限量)
    id 一律以字符串类型存储
    itemsplit: 拆分不同条目的字符, 第一层
    cfgsplit: 拆分条目与其配置值的字符, 第二层
    '''
    pfdict = {}
    if not CheckVal(pfdata):
        return pfdict
    pf = pfdata.split(itemsplit)
    num = 0
    for _p in pf:
        if _p:
            num += 1
            pi = _p.split(cfgsplit)
            if len(pi) == 2:
                if pi[1].lstrip('+-').isdigit():
                    pfdict[str(pi[0])] = int(pi[1])
                else:
                    raise ValueError(f'传送数值格式非法, 传入内容为 {pfdata}')
            else:
                raise ValueError(f'传送数值格式非法, 传入内容为 {pfdata}')
    if num != len(pfdict):
        logger.error(f"数据转换错误, 可能为 key 值有重复, 传入的字典为 {pfdict}, {num=}")
    return pfdict


def remove_common_kv_pairs(series):
    '''
    传入的 series 为 "ID 为 index, 配置信息(字典)为内容" 的 series
    将各个配置信息中 key 与 value 都一致的部分去除, 仅保留差异部分
    典型用途: 同类配置批量比对时, 过滤掉完全相同的字段, 只留差异项
    '''
    # 获取所有字典共有的键
    common_keys = set.intersection(*[set(d.keys()) for d in series])

    # 筛选需要删除的键（所有字典中值完全相同的键）
    keys_to_remove = []
    for key in common_keys:
        if series.apply(lambda d: d[key]).nunique() == 1:
            keys_to_remove.append(key)

    # 构建新Series
    return series.apply(lambda d: {k: v for k, v in d.items() if k not in keys_to_remove})


def is_increasing(lst, equ=0):
    '''
    判断列表是否递增, equ 为 0 则为大于等于(允许相等), 不为 0 则必须严格大于
    '''
    assert isinstance(lst, list), "传入数据类型只能为list类型"
    return all(lst[i] <= lst[i + 1] for i in range(len(lst) - 1)) if equ == 0 else all(lst[i] < lst[i + 1] for i in range(len(lst) - 1))


def get_checkfile(filekey):
    '''根据规则名取其依赖的配置文件路径, 依赖关系在 config/base.py 的 checkfile 中配置'''
    filename = checkfile.get(filekey, '')
    assert filename and isinstance(filename, dict), f"规则 {filekey} 检查依赖的配置文件传入错误, 请检查 config/base.py 文件中的 checkfile 配置!"
    return {k: os.path.join(RULE_DATA, v) for k, v in filename.items()}


def check_column_inclusion(source_df, target_df, source_col=None, target_col=None, source_name="源表", target_name="目标表", item_desc_col=None, desc_prefix="", print_missing=True, print_exists=True):
    """
    检查源表的列值是否都存在于目标表的列中（跨表引用存在性检查）

    参数:
    ----------
    source_df : DataFrame
        源表，要检查的数据
    target_df : DataFrame
        目标表，被检查是否包含的数据
    source_col : str, optional
        源表的列名，如果为None则使用索引
    target_col : str, optional
        目标表的列名，如果为None则使用索引
    source_name : str, optional
        源表名称，用于错误信息
    target_name : str, optional
        目标表名称，用于错误信息
    item_desc_col : str, optional
        条目描述列名，用于输出更详细的错误信息
    desc_prefix : str, optional
        描述前缀，用于区分不同类型的条目
    print_missing : bool, optional
        是否打印不存在的数据
    print_exists : bool, optional
        是否打印存在的数据

    返回:
    -------
    dict
        {
            'missing': Dict[str, str],  # 不存在的项 {ID: 错误信息}
            'exists': List[str],        # 存在的项 [ID1, ID2, ...]
        }
    """
    if source_col is None:
        source_ids = source_df.index.tolist()
    else:
        source_ids = source_df[source_col].astype(str).tolist()

    if target_col is None:
        target_ids_set = set(target_df.index.astype(str))
    else:
        target_ids_set = set(target_df[target_col].astype(str))

    missing_dict = {}
    exists_list = []

    print(f"\n{'='*60}")
    print(f"开始检查: {source_name} → {target_name}")

    for source_id in source_ids:
        source_id_str = str(source_id)

        item_desc = "未知名称"
        if item_desc_col and source_col:
            try:
                if source_col is None:
                    row = source_df.loc[source_id]
                else:
                    row = source_df[source_df[source_col] == source_id].iloc[0]

                if hasattr(row, item_desc_col) and item_desc_col in row:
                    item_desc = str(row[item_desc_col])
            except:
                item_desc = "未知名称"
        elif item_desc_col and source_col is None:
            try:
                row = source_df.loc[source_id]
                if hasattr(row, item_desc_col) and item_desc_col in row:
                    item_desc = str(row[item_desc_col])
            except:
                item_desc = "未知名称"

        if source_id_str not in target_ids_set:
            error_msg = f"{desc_prefix}{source_name}配置条目 {source_id_str} ({item_desc}), 在{target_name}中不存在!"
            missing_dict[source_id_str] = error_msg

            if print_missing:
                print(f"不存在: {source_id_str} ({item_desc})")
        else:
            exists_list.append(source_id_str)

            if print_exists:
                print(f"存在: {source_id_str} ({item_desc})")

    total_count = len(source_ids)
    missing_count = len(missing_dict)
    exists_count = len(exists_list)

    print(f"   总计检查: {total_count} 项")
    if total_count:
        print(f"   存在: {exists_count} 项 ({exists_count/total_count*100:.1f}%)")
        print(f"   不存在: {missing_count} 项 ({missing_count/total_count*100:.1f}%)")
    print(f"{'='*60}")

    return {
        'missing': missing_dict,
        'exists': exists_list
    }


def check_columns_not_empty(df, table_name, errdict, columns=None, exclude_columns=None, check_index=True):
    """
    检查表格中指定列是否不为空，错误信息累加到 errdict 中
    columns: 指定检查的列, 默认检查所有列
    exclude_columns: 指定不检查的列, 默认不排除任何列
    """
    def is_empty(val):
        if val is None:
            return True
        if isinstance(val, float) and pd.isna(val):
            return True
        if isinstance(val, str) and val.strip() == '':
            return True
        return False

    if check_index:
        for idx, index_value in enumerate(df.index):
            if is_empty(index_value):
                key = f"{table_name}_index_{idx}"
                errdict[key] = f"{table_name}[第{idx}行索引为空]"

    check_cols = columns if columns else df.columns.tolist()
    if exclude_columns:
        check_cols = [col for col in check_cols if col not in exclude_columns]

    for rowdata in df.itertuples():
        for col in check_cols:
            cell_value = getattr(rowdata, col, None)
            row_idx = rowdata.Index

            if is_empty(cell_value):
                key = f"{table_name}_{row_idx}_{col}"
                errdict[key] = f"{table_name}[第{row_idx}行列'{col}'为空]"

    return errdict


def runRules(ruleclass, outtxt=None):
    '''调试工具: 执行单个规则类下全部 Check_ 前缀的检查方法并输出结果'''
    rulekey = "Check_"
    ruledict = {}

    checkrules = ruleclass.__ordered__

    for fun in checkrules:
        if fun.startswith(rulekey):
            ruledict[fun] = getattr(ruleclass, fun)

    if not ruledict:
        print(f"指定class实例中并未包含有 {rulekey} 命名的方法, 请检查是否传入了正确的class实例")
        return

    output = sys.stdout
    if outtxt:
        output = open(outtxt, 'w', encoding="utf8")

    for f in ruledict:
        print(f'\n规则: {ruledict[f].__doc__}==========================', file=output)
        err = ruledict[f]()
        GetprinttypeAndPint(err, output)
        print("\n"+"-"*80, file=output)

    if outtxt:
        output.close()

    print("Done!")
