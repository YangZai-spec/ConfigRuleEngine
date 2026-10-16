import pandas as pd
import json
import re


# 识别两个非数字字符之间的连字符, 避免误杀负号
hyphen_pattern = re.compile(r'(?<=[^\d\s])-(?=[^\d\s])')

def trans_brackets(instr):
    '''
    编辑器导出的 json 文件中, 字段名称中含有括号字符, 无法作为合法变量访问
    需要先转换一下, 规则如下:
    1. 字符串内的括号(全半角), 一律替换为下划线_
    2. 连接在字符串中间的 - 号会替换为_, 但数字前的不做处理(因为负号也有意义)
    3. 部分字符串开头就有的括号将不做替换, 直接删除
    '''
    trans_table = str.maketrans({
        '(': '_',
        ')': '_',
        '（': '_',
        '）': '_',
    })
    # 先将连字符转换为_, 通过正则避免误杀负号
    instr = hyphen_pattern.sub('_', instr)
    # 有 0-100 这样的数字范围情况, 也需要替换一下, 上面的正则不能覆盖
    instr = re.sub(r'(?<=\d)-(?=\d)', "_", instr)
    # 将左右括号转换为下划线_
    instr_notbrack = instr.translate(trans_table)
    # 将单词开头的下划线剔除, 在json字符串中都是用双引号开头的
    return instr_notbrack.replace('"_', '"')


def json2df(jsfile, needkey=None, needtrans=0):
    '''
    将编辑器转出的 json 文件转换为 pandas 的 dataframe
    编辑器转出的 json 为 utf8 with bom 格式
    因 json 中冗余数据太多, 直接转换 dataframe 会失败, 通常需要通过 needkey 关键字筛选需要处理的部分.
    needtrans 如不为0, 则对二维表转置输出
    '''
    with open(jsfile, 'r', encoding='utf-8-sig') as fs:
        content = fs.read()
        content = trans_brackets(content)
    data = json.loads(content)
    if needkey:
        assert needkey in data, f"指定的key {needkey} 在 {jsfile} 中不存在!"
        data = data[needkey]
    df = pd.DataFrame(data)
    # 需要转置一下, 以ID为行索引
    return df.T if needtrans else df


def json2dic(jsfile, needkey=None, keepkey=None):
    '''
    将编辑器转出的 json 文件转换为 dict
    编辑器转出的 json 为 utf8 with bom 格式
    needkey: json中需要保留的字段
    keepkey: 如果不为空, 则需要是一个列表, 最终输出的dict, 仅保留key值位于该列表中的数据
    '''
    with open(jsfile, 'r', encoding='utf-8-sig') as fs:
        content = fs.read()
        content = trans_brackets(content)
    data = json.loads(content)
    if needkey:
        assert needkey in data, f"指定的key {needkey} 在 {jsfile} 中不存在!"
        data = data[needkey]
    if keepkey:
        data = {k: data[k] for k in keepkey if k in data}
    return data
