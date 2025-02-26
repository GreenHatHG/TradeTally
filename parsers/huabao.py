from models import InvestmentInfo


def parse_huabao_stock_data(lines):
    """解析华宝证券持仓的OCR文本"""
    # 清理空行和非数据行
    filtered = [line.strip() for line in lines if line.strip() not in
                ("买入", "卖出", "撤单", "持仓", "查询", "证券/市值", "成本/现价", "持仓/可用", "累计盈亏", "仓位")]

    # 定位数据起始位置（第一个包含".SH"或".SZ"的行）
    data_start = next((i for i, line in enumerate(filtered) if ".SH" in line or ".SZ" in line), 0) - 4

    # 按10个字段为一组切割数据
    stock_blocks = []
    current_block = []
    for line in filtered[data_start:]:
        current_block.append(line)
        if len(current_block) == 10:
            stock_blocks.append(current_block)
            current_block = []

    # 解析数据结构
    results = []
    for block in stock_blocks:
        try:
            investment = InvestmentInfo()
            investment.name = block[0]
            investment.cost_price = float(block[1])
            investment.quantity = int(block[2])
            investment.profit_amount = float(block[3])
            investment.code = block[4]
            investment.position_ratio = round(float(block[5].strip("%")) / 100, 4)
            investment.current_price = float(block[6])
            investment.profit_ratio = round(float(block[8].strip("%")) / 100, 4)
            investment.market_value = float(block[9])
            results.append(investment.to_dict())
        except Exception as e:
            print(f"解析华宝数据失败: {block}，错误: {str(e)}")

    return results
