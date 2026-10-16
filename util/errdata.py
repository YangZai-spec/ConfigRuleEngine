from pydantic import BaseModel
from typing import Union, Dict, Any, Literal, Optional


class errdict(BaseModel):
    '''
    存放错误信息字典
    '''
    errname: str|int
    errinfo: list[str]


class errdata(BaseModel):
    '''
    存放单条错误信息
    '''
    erritemid: str|int
    errinfo: Union[str, Dict[str,str], list[str|int], errdict]


class allerrs(BaseModel):
    '''
    一条规则的完整检查结果: 规则名 + 错误列表 + 警告列表
    errs 为必须修复的问题; warns 为建议人工复核的疑点
    '''
    rulename: str
    errs: list[errdata] = []
    warns: list[errdata] = []
