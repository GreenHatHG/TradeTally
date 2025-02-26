from models import InvestmentInfo


def parse_haitong_stock_data(ocr_results):
    """
    处理海通证券OCR结果并整理成结构化数据

    参数:
        ocr_results: RapidOCR返回的原始结果列表

    返回:
        整理后的股票数据列表，每个元素包含一支股票的完整信息
    """
    # 第一步：找出图像边界
    if not ocr_results:
        return []

    # 计算图像边界
    min_x = min(min(coord[0] for coord in item[0]) for item in ocr_results)
    max_x = max(max(coord[0] for coord in item[0]) for item in ocr_results)
    min_y = min(min(coord[1] for coord in item[0]) for item in ocr_results)
    max_y = max(max(coord[1] for coord in item[0]) for item in ocr_results)

    image_width = max_x - min_x
    image_height = max_y - min_y

    # 第二步：过滤掉非股票相关的OCR结果
    filtered_results = []
    stock_area_detected = False
    stock_area_top = 0
    stock_area_bottom = max_y

    # 找出股票区域的开始和结束位置
    for item in ocr_results:
        coords, text, confidence = item
        if "当前持仓" in text or "股票/市值" in text:
            stock_area_top = max(stock_area_top, max(coord[1] for coord in coords))
            stock_area_detected = True
        elif "以上是全部" in text and stock_area_detected:
            stock_area_bottom = min(coord[1] for coord in coords)
            break

    # 如果没有找到明确的股票区域，使用图像的中间区域作为估计
    if not stock_area_detected:
        stock_area_top = min_y + image_height * 0.3  # 大约从图像30%高度开始
        stock_area_bottom = min_y + image_height * 0.9  # 到图像90%高度结束

    # 过滤位于股票区域的结果
    for item in ocr_results:
        coords, text, confidence = item
        # 获取中心点y坐标
        center_y = sum(coord[1] for coord in coords) / len(coords)

        # 排除明显的标题和导航栏
        skip_keywords = ["总资产", "股票/市值", "持仓/可用", "下滑查看", "当前持仓",
                         "查看盈亏", "以上是全部", "当日预估", "浮动盈亏", "股票", "理财"]
        if any(keyword in text for keyword in skip_keywords):
            continue

        # 只保留位于股票列表区域的结果
        if stock_area_top <= center_y <= stock_area_bottom:
            filtered_results.append(item)

    # 第三步：按照y坐标排序
    filtered_results.sort(key=lambda x: sum(coord[1] for coord in x[0]) / len(x[0]))

    # 第四步：根据数据特征和相对位置进行分类
    stock_data = []
    current_y_center = 0

    # 动态计算y阈值 - 根据文本高度的平均值
    text_heights = [max(coord[1] for coord in item[0]) - min(coord[1] for coord in item[0])
                    for item in filtered_results]
    y_threshold = sum(text_heights) / len(text_heights) * 1.5 if text_heights else 50

    # 计算水平分区 - 将宽度分为几个区域
    x_sections = [
        min_x + image_width * 0.25,  # 大约25%宽度位置
        min_x + image_width * 0.5,   # 大约50%宽度位置
        min_x + image_width * 0.75   # 大约75%宽度位置
    ]

    temp_data = {}

    for item in filtered_results:
        coords, text, confidence = item
        # 计算文本框中心点
        center_x = sum(coord[0] for coord in coords) / len(coords)
        center_y = sum(coord[1] for coord in coords) / len(coords)

        # 如果y坐标差距大于阈值，认为是新的股票数据开始
        if abs(center_y - current_y_center) > y_threshold:
            if temp_data and len(temp_data) > 0:
                stock_data.append(temp_data)
                temp_data = {}
            current_y_center = center_y

        # 根据x坐标的相对位置和内容特征判断数据类型
        # 第一区域 (左侧) - 股票名称或市值
        if center_x < x_sections[0]:
            if any('\u4e00' <= ch <= '\u9fff' for ch in text):  # 包含中文字符
                temp_data['name'] = text
            elif '.' in text and text.replace('.', '').replace('-', '').isdigit():  # 数字+小数点
                temp_data['market_value'] = text

        # 第二区域 (中左) - 持仓数量
        elif x_sections[0] <= center_x < x_sections[1] and text.replace(',', '').isdigit():  # 纯数字
            temp_data['shares'] = text

        # 第三区域 (中右) - 市价和成本价
        elif x_sections[1] <= center_x < x_sections[2] and '.' in text:
            # 根据y位置来区分市价和成本价
            if 'price' not in temp_data:
                temp_data['price'] = text  # 市价
            else:
                temp_data['cost_price'] = text  # 成本价

        # 第四区域 (右侧) - 盈亏
        elif center_x >= x_sections[2]:
            # 盈亏金额通常是数字加小数点，可能有正负号
            if '.' in text and '%' not in text:
                # 检查是否是数字（可能有正负号）
                number_text = text.replace('.', '').replace('-', '').replace('+', '')
                if number_text.isdigit():
                    temp_data['profit_amount'] = text  # 盈亏金额
            # 盈亏比例通常带有百分号，如 -4.67%
            elif '%' in text:
                temp_data['profit_rate'] = text  # 盈亏比例

    # 添加最后一组数据
    if temp_data and len(temp_data) > 0:
        stock_data.append(temp_data)

    # 第五步：整理数据，将分散的信息按股票合并
    organized_stocks = []
    i = 0
    while i < len(stock_data):
        current = stock_data[i]

        # 检查是否有下一条记录，以及下一条是否可能是同一支股票的附加信息
        if i + 1 < len(stock_data):
            next_item = stock_data[i + 1]
            # 如果当前记录有股票名称，下一条没有，但有市值或其他信息
            if 'name' in current and 'name' not in next_item:
                # 合并两条记录
                merged = {**current}
                # 复制下一条记录中的所有其他字段
                for key, value in next_item.items():
                    if key not in merged:
                        merged[key] = value
                organized_stocks.append(merged)
                i += 2  # 跳过下一条，因为已经合并
                continue

        # 如果没有合并，则直接添加当前记录
        organized_stocks.append(current)
        i += 1

    # 第六步：后处理，构建统一格式的投资信息
    results = []
    for stock in organized_stocks:
        # 跳过不完整的记录
        if not ('name' in stock and ('shares' in stock or 'market_value' in stock)):
            continue

        try:
            investment = InvestmentInfo()
            investment.name = stock.get('name', '未知')

            # 处理数值转换
            if 'shares' in stock:
                investment.quantity = int(stock['shares'].replace(',', ''))
            if 'price' in stock:
                investment.current_price = float(stock['price'])
            if 'cost_price' in stock:
                investment.cost_price = float(stock['cost_price'])
            if 'market_value' in stock:
                investment.market_value = float(stock['market_value'])
            if 'profit_amount' in stock:
                investment.profit_amount = float(stock['profit_amount'])
            if 'profit_rate' in stock and '%' in stock['profit_rate']:
                # 去掉百分号并转换为小数
                rate_str = stock['profit_rate'].replace('%', '')
                investment.profit_ratio = float(rate_str) / 100

            results.append(investment.to_dict())
        except Exception as e:
            print(f"处理海通证券数据时出错: {str(e)}, 数据: {stock}")

    return results
