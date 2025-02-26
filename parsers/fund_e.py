import re

from models import InvestmentInfo


def parse_fund_data(lines):
    """解析基金e账户的OCR文本"""
    results = []

    # 找到筛选之后的起始位置
    start_idx = 0
    for idx, line in enumerate(lines):
        if '筛选' in line:
            start_idx = idx + 1
            break

    # 从筛选之后开始处理
    i = start_idx

    while i < len(lines):
        # 寻找标准模式的开始（持有份额、参考净值、资产情况连续三行）
        if (i+2 < len(lines) and
                lines[i].strip() == '持有份额' and
                lines[i+1].strip() == '参考净值' and
                lines[i+2].strip() == '资产情况'):

            # 确认接下来的三行是否为数值
            if i+5 < len(lines) and all(re.match(r'^[\d,\.]+$', lines[i+3+k].strip()) for k in range(3)):
                try:
                    # 提取数值部分
                    holding = float(lines[i+3].strip().replace(',', ''))
                    nav = float(lines[i+4].strip().replace(',', ''))
                    asset = float(lines[i+5].strip().replace(',', ''))

                    # 向上查找基金名称和代码
                    j = i - 1
                    name_parts = []
                    fund_code = ""

                    # 跳过可能的空行
                    while j >= 0 and not lines[j].strip():
                        j -= 1

                    # 检查上一行是否是数值（上一个基金的资产情况）
                    if j >= 0 and re.match(r'^[\d,\.]+$', lines[j].strip()):
                        # 继续向上查找，直到找到"资产情况"行
                        asset_line_found = False
                        for k in range(j-1, max(0, j-5), -1):
                            if k >= 0 and lines[k].strip() == '资产情况':
                                j = k - 1  # 从"资产情况"行的上一行开始查找
                                asset_line_found = True
                                break

                        if not asset_line_found:
                            j -= 3  # 如果找不到"资产情况"行，假设上一个基金占用了3行数据

                    # 收集基金名称，直到找到上一个基金的资产情况数值
                    while j >= 0:
                        line = lines[j].strip()

                        # 如果遇到数值行或标准的字段名称，停止收集
                        if (re.match(r'^[\d,\.]+$', line) or
                                line in ['持有份额', '参考净值', '资产情况']):
                            break

                        # 查找基金代码
                        code_match = re.search(r'[（\(](\d{6})[）\)]', line)
                        if code_match and not fund_code:
                            fund_code = code_match.group(1)

                            # 获取代码前的文本作为名称的一部分
                            prefix = line[:code_match.start()].strip()
                            if prefix:
                                name_parts.insert(0, prefix)
                        elif line:  # 如果行不为空
                            name_parts.insert(0, line)

                        j -= 1

                    # 组合并清理基金名称
                    fund_name = ' '.join(name_parts).strip()

                    # 清理基金名称中可能存在的页面头部信息
                    fund_name = re.sub(r'.*筛选\s*', '', fund_name)
                    fund_name = re.sub(r'.*数据日期[：:][^，。]*', '', fund_name)
                    fund_name = re.sub(r'\s+', '', fund_name).replace('(', '（')

                    # 修复基金名称中的常见问题
                    fund_name = re.sub(r'联\s+接', '联接', fund_name)
                    fund_name = re.sub(r'投\s+资', '投资', fund_name)

                    # 创建统一的投资信息对象
                    investment = InvestmentInfo()
                    investment.name = fund_name
                    investment.code = fund_code
                    investment.quantity = holding
                    investment.current_price = nav
                    investment.market_value = asset
                    results.append(investment.to_dict())

                    # 跳过已处理的行
                    i += 6
                    continue
                except ValueError:
                    pass

        i += 1

    return results