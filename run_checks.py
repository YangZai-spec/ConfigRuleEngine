import os
import sys
import importlib
import importlib.util
import glob
import traceback
import time
from pathlib import Path

# 添加当前目录到系统路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

REQUIRED_DEPS = {
    'pandas': 'pandas',
    'openpyxl': 'openpyxl',
    'pydantic': 'pydantic',
}


def check_dependencies():
    '''
    启动前检查运行依赖。
    缺少依赖时, 规则模块会在 import 阶段失败, 但报错会被吞成一句 "加载模块失败",
    排查成本很高, 因此在这里提前拦截并给出明确提示。
    '''
    missing = []
    for mod, pkg in REQUIRED_DEPS.items():
        try:
            __import__(mod)
        except ImportError:
            missing.append(pkg)

    if missing:
        print("=" * 60)
        print("缺少运行依赖: " + ", ".join(missing))
        print("请先安装依赖后再运行:")
        print("    pip install -r requirements.txt")
        print("    pip install " + " ".join(missing))
        print("=" * 60)
        sys.exit(2)


try:
    from util.commontools import get_logger, runRules
    USE_LOGGER = True
except ImportError:
    USE_LOGGER = False

    class SimpleLogger:
        def __init__(self, name):
            self.name = name

        def info(self, msg):
            print(f"[INFO] {msg}")

        def warning(self, msg):
            print(f"[WARNING] {msg}")

        def error(self, msg):
            print(f"[ERROR] {msg}")

        def debug(self, msg):
            print(f"[DEBUG] {msg}")

    def get_simple_logger(name):
        return SimpleLogger(name)

    logger = get_simple_logger(__name__)
else:
    logger = get_logger(__name__)


def discover_rule_classes(rule_dir="rule", pattern="*.py", exclude_patterns=None):
    """
    发现指定目录下所有符合条件的规则文件
    """
    if exclude_patterns is None:
        exclude_patterns = []

    rule_path = os.path.join(current_dir, rule_dir)
    if not os.path.exists(rule_path):
        logger.error(f"规则目录不存在: {rule_path}")
        return []

    # 查找所有匹配的规则文件
    rule_files = glob.glob(os.path.join(rule_path, pattern))
    filtered_files = []
    for file in rule_files:
        filename = os.path.basename(file)
        should_exclude = any(exclude_pattern in filename for exclude_pattern in exclude_patterns)
        if not should_exclude:
            filtered_files.append(file)

    logger.info(f"发现 {len(filtered_files)} 个规则文件:")
    for file in filtered_files:
        logger.info(f"  - {os.path.basename(file)}")

    return filtered_files


def load_rule_module(file_path):
    '''
    加载规则模块, 返回 (module, error_msg):
    - 成功: (module, None)
    - 失败: (None, 具体原因)  原因会写进汇总报告, 便于直接定位(如缺少依赖/语法错误)
    '''
    try:
        module_name = os.path.splitext(os.path.basename(file_path))[0]
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None:
            msg = f"无法加载模块规格: {file_path}"
            logger.error(msg)
            return None, msg

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        logger.debug(f"成功加载模块: {module_name}")
        return module, None

    except Exception as e:
        msg = f"{type(e).__name__}: {e}"
        logger.error(f"加载模块 {file_path} 时发生错误: {msg}")
        return None, msg


def find_rule_class(module):
    """在模块中查找规则类"""
    if module is None:
        return None

    # 查找模块中所有以大写字母开头的类
    rule_classes = []
    for attr_name in dir(module):
        attr = getattr(module, attr_name)

        # 检查是否是类且不是内置类
        if (isinstance(attr, type) and
                not attr_name.startswith('_') and
                attr.__module__ == module.__name__):

            # 检查类是否有检查方法
            has_check_methods = any(
                method.startswith("Check_") for method in dir(attr)
            )

            if has_check_methods:
                rule_classes.append(attr)

    if len(rule_classes) == 0:
        logger.warning(f"模块 {module.__name__} 中没有找到包含Check_方法的规则类")
        return None

    # 如果有多个类，选择第一个
    if len(rule_classes) > 1:
        logger.warning(f"模块 {module.__name__} 中找到多个规则类，使用第一个: {rule_classes[0].__name__}")

    return rule_classes[0]


def run_single_rule_simple(rule_instance, output_file=None):
    try:
        from util.commontools import runRules
        errors = runRules(rule_instance, output_file)
        return True, errors
    except Exception as e:
        logger.error(f"运行规则失败: {str(e)}")
        return False, None


def generate_summary(results, summary_path):
    """总结报告"""
    try:
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("规则检查总结报告\n")
            f.write(f"生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 60 + "\n\n")

            success_count = sum(1 for r in results if r.get('success', False))
            total_count = len(results)

            f.write(f"检查统计:\n")
            f.write(f"  总计规则文件: {total_count} 个\n")
            f.write(f"  成功运行: {success_count} 个\n")
            f.write(f"  失败运行: {total_count - success_count} 个\n")
            if total_count:
                f.write(f"  成功率: {success_count/total_count*100:.1f}%\n\n")

            f.write("详细结果:\n")
            for i, result in enumerate(results, 1):
                class_name = result.get('class', '未知')
                f.write(f"{i}. {result['file']} ({class_name})\n")

                if result.get('success'):
                    if result.get('error_count', 0) > 0:
                        f.write(f"   发现 {result['error_count']} 个错误\n")
                    else:
                        f.write(f"   所有检查已完成\n")

                    if result.get('output_file'):
                        f.write(f"   检查报告: {os.path.basename(result['output_file'])}\n")
                else:
                    error_msg = result.get('error', '未知错误')
                    f.write(f"   失败原因: {error_msg}\n")

            f.write("\n" + "=" * 60 + "\n")

        logger.info(f"总结报告已生成: {summary_path}")

    except Exception as e:
        logger.error(f"生成总结报告失败: {str(e)}")


def run_all_rules(output_dir="reports", summary_file="check_summary.txt"):
    """
    运行所有规则检查
    """
    # 使用脚本所在目录作为基准，确保输出目录在项目目录下
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, output_dir)

    logger.info("=" * 60)
    logger.info("开始运行所有规则检查")
    logger.info("=" * 60)

    # 创建输出目录
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        logger.info(f"创建输出目录: {output_dir}")

    # 发现所有规则文件
    rule_files = discover_rule_classes(
        rule_dir="rule",
        pattern="*.py",
        exclude_patterns=["__init__.py", "__pycache__", "test_*.py"]
    )

    if not rule_files:
        logger.error("没有找到规则文件，检查结束")
        return False

    # 运行每个规则
    results = []

    for file_path in rule_files:
        file_name = os.path.basename(file_path)
        logger.info(f"\n{'='*40}")
        logger.info(f"处理规则文件: {file_name}")
        logger.info(f"{'='*40}")

        try:
            module, load_err = load_rule_module(file_path)
            if module is None:
                results.append({
                    'file': file_name,
                    'success': False,
                    'error': f'加载模块失败 -> {load_err}'
                })
                continue

            rule_class = find_rule_class(module)
            if rule_class is None:
                results.append({
                    'file': file_name,
                    'success': False,
                    'error': '未找到规则类'
                })
                continue

            try:
                rule_instance = rule_class()
            except Exception as e:
                results.append({
                    'file': file_name,
                    'class': rule_class.__name__,
                    'success': False,
                    'error': f'实例化失败: {e}'
                })
                continue

            # 运行规则检查
            output_file = os.path.join(output_dir, f"{file_name.replace('.py', '')}_report.txt")
            logger.info(f"运行检查，输出到: {os.path.basename(output_file)}")

            success, check_results = run_single_rule_simple(rule_instance, output_file)

            if success:
                logger.info(f"规则检查完成")

                # 分析结果
                error_count = 0
                if isinstance(check_results, dict):
                    error_count = len(check_results)
                elif hasattr(check_results, '__len__'):
                    error_count = len(check_results)

                if error_count > 0:
                    logger.info(f"  发现 {error_count} 个问题")
                else:
                    logger.info(f"所有检查通过")

            else:
                logger.error(f"规则检查失败")

            # 保存结果
            results.append({
                'file': file_name,
                'class': rule_class.__name__,
                'success': success,
                'error_count': error_count if success else 0,
                'output_file': output_file if success else None,
                'results': check_results if success else None
            })

        except Exception as e:
            logger.error(f"处理文件时发生未预期的错误: {str(e)}")
            logger.debug(traceback.format_exc())
            results.append({
                'file': file_name,
                'success': False,
                'error': f'处理文件失败: {e}'
            })

    # 生成总结报告
    summary_path = os.path.join(output_dir, summary_file)
    print(summary_path)
    generate_summary(results, summary_path)

    logger.info("\n" + "=" * 60)
    logger.info("规则检查完成")
    logger.info("=" * 60)

    return all(result.get('success', False) for result in results)


def main():
    check_dependencies()

    success = run_all_rules()

    if success:
        logger.info("所有规则检查成功完成")
        sys.exit(0)
    else:
        logger.warning("部分规则检查失败，请查看详细报告")
        sys.exit(1)


if __name__ == "__main__":
    main()
