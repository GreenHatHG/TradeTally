import json
import pandas as pd
import plotly.express as px
import os

from sunburst.classify import classify_holding


# 创建旭日图数据结构
def create_sunburst_data(portfolio_data, verbose_classify=False):
    holdings = []

    # 处理统一格式的数据
    for item in portfolio_data.get('data', []):
        name = item.get('name', '')
        code = item.get('code', '')
        source_type = item.get('source_type', '未知')
        
        # 直接获取 market_value，不存在则报错
        if 'market_value' in item and item['market_value'] is not None:
            value = float(item['market_value'])
        else:
            print(f"错误: 项目 '{name}' (代码: {code}) 没有 market_value 数据，将被跳过")
            continue
        
        # 进行数据检查
        if value <= 0:
            print(f"错误: 项目 '{name}' (代码: {code}) 的市值为 {value}，无效")
            continue
            
        level1, level2, level3 = classify_holding(name, code, verbose=verbose_classify)
        
        # 打印最终分类结果
        print(f"分类结果: '{name}' (代码: {code}) => {level1}/{level2}/{level3}")
        
        holdings.append({
            'name': name,
            'code': code,
            'value': value,
            'level1': level1,
            'level2': level2,
            'level3': level3,
            'source': source_type  # 保存来源信息，便于后续分析
        })

    if not holdings:
        raise ValueError("没有找到任何有效的 market_value 数据，无法生成旭日图")
        
    return pd.DataFrame(holdings)

# 绘制旭日图
def plot_sunburst(df, output_file="portfolio_sunburst.html"):
    # 按层级聚合数据
    grouped_df = df.groupby(['level1', 'level2', 'level3']).agg({'value': 'sum'}).reset_index()

    # 计算每一层的百分比
    total_value = grouped_df['value'].sum()
    grouped_df['percentage'] = grouped_df['value'] / total_value * 100

    # 创建一个百分比数据字典，用于JavaScript
    percentages_dict = {}
    # 先处理所有完整路径（三级分类）
    for _, row in grouped_df.iterrows():
        # 构建完整路径ID
        id_path = '/'.join(filter(None, [row['level1'], row['level2'], row['level3']]))
        percentages_dict[id_path] = row['percentage']
        
        # 同时处理一级和二级路径
        if row['level1']:
            # 一级路径
            level1_path = row['level1']
            if level1_path not in percentages_dict:
                # 计算一级分类的百分比
                level1_percentage = grouped_df[grouped_df['level1'] == level1_path]['value'].sum() / total_value * 100
                percentages_dict[level1_path] = level1_percentage
            
            # 二级路径（如果存在）
            if row['level2']:
                level2_path = f"{row['level1']}/{row['level2']}"
                if level2_path not in percentages_dict:
                    # 计算二级分类的百分比
                    level2_filter = (grouped_df['level1'] == row['level1']) & (grouped_df['level2'] == row['level2'])
                    level2_percentage = grouped_df[level2_filter]['value'].sum() / total_value * 100
                    percentages_dict[level2_path] = level2_percentage

    # 可以添加这行代码以验证所有路径百分比
    print(f"已生成 {len(percentages_dict)} 个百分比映射")
    for path, percentage in sorted(percentages_dict.items()):
        print(f"路径: {path}, 百分比: {percentage:.1f}%")

    # 创建旭日图 - 使用更丰富的色彩方案
    fig = px.sunburst(
        grouped_df,
        path=['level1', 'level2', 'level3'],
        values='value',
        color='level1',
        color_discrete_sequence=px.colors.qualitative.Bold,
        hover_data=['percentage'],
        custom_data=['percentage', 'level3', 'level1']
    )

    # 恢复原始的文本模板，但确保百分比显示正确
    fig.update_traces(
        texttemplate='%{label} %{customdata[0]:.1f}%',
        hovertemplate='<b>%{label}</b><br>占比: %{customdata[0]:.2f}%<br>价值: %{value:,.0f}',
        insidetextorientation='radial',
        textfont=dict(size=16, family="Arial, sans-serif", color="white")
    )

    # 从外部文件读取 JavaScript 代码
    js_file_path = os.path.join(os.path.dirname(__file__), 'sunburst_chart.js')
    try:
        with open(js_file_path, 'r', encoding='utf-8') as js_file:
            js_code = js_file.read()
            # 注入Python计算的百分比数据
            js_code = js_code.replace('const pythonPercentages = JSON_DATA_FROM_PYTHON || {};', 
                               f'const pythonPercentages = {json.dumps(percentages_dict)} || {{}};')
    except FileNotFoundError:
        print(f"警告: JavaScript 文件 {js_file_path} 未找到，图表交互功能可能受限")
        js_code = ""

    fig.update_layout(
        title=dict(
            text="投资组合资产配置",
            font=dict(size=32, color="#333"),
            x=0.5,
            y=0.95
        ),
        font=dict(family="Arial, sans-serif", size=16),
        width=1200,
        height=1200,
        margin=dict(t=120, l=170, r=170, b=170),
        paper_bgcolor='rgb(250,250,250)',
        plot_bgcolor='rgb(250,250,250)',
        showlegend=True,
        legend=dict(font=dict(size=16))
    )

    # 添加响应式配置
    config = {
        'responsive': True,
        'displayModeBar': True,
        'displaylogo': False,
        'toImageButtonOptions': {
            'format': 'png',
            'filename': '投资组合旭日图',
            'height': 1200,
            'width': 1200,
            'scale': 2
        }
    }

    html_content = fig.to_html(config=config, include_plotlyjs='cdn')
    html_content = html_content.replace('</body>', js_code + '</body>')

    # 添加唯一ID给图表元素
    html_content = html_content.replace('<div id="plotly-html-element"', '<div id="sunburst-chart"')

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    return fig

# 打印投资组合摘要数据
def print_portfolio_summary(df):
    """打印投资组合的详细数据，包括各分类的市值和占比"""
    # 按层级聚合数据
    grouped_df = df.groupby(['level1', 'level2', 'level3']).agg({'value': 'sum'}).reset_index()

    # 计算每一层的百分比
    total_value = grouped_df['value'].sum()
    grouped_df['percentage'] = grouped_df['value'] / total_value * 100

    # 排序后的数据
    sorted_df = grouped_df.sort_values('value', ascending=False)

    # 打印总计
    print("\n===== 投资组合总览 =====")
    print(f"总市值: {total_value:,.2f}")
    print("\n")

    # 打印一级分类汇总
    print("===== 一级分类汇总 =====")
    level1_summary = df.groupby('level1')['value'].sum().sort_values(ascending=False)
    level1_percentage = level1_summary / total_value * 100
    for category, value in level1_summary.items():
        print(f"{category}: {value:,.2f} ({level1_percentage[category]:.2f}%)")
    print("\n")

    # 打印二级分类汇总
    print("===== 二级分类汇总 =====")
    level2_summary = df.groupby(['level1', 'level2'])['value'].sum().sort_values(ascending=False)
    for (cat1, cat2), value in level2_summary.items():
        percentage = value / total_value * 100
        print(f"{cat1} - {cat2}: {value:,.2f} ({percentage:.2f}%)")
    print("\n")

    # 打印所有详细持仓
    print("===== 详细持仓数据 =====")
    print(f"{'一级分类':<10} {'二级分类':<10} {'三级分类':<10} {'市值':>12} {'占比':>8}")
    print("-" * 60)
    for _, row in sorted_df.iterrows():
        print(f"{row['level1']:<10} {row['level2']:<10} {row['level3']:<10} {row['value']:>12,.2f} {row['percentage']:>7.2f}%")
    
    # 添加按分类的具体持仓明细
    print("\n===== 分类持仓明细 =====")
    # 按一级分类排序
    for level1, group1 in sorted(df.groupby('level1'), key=lambda x: x[1]['value'].sum(), reverse=True):
        level1_value = group1['value'].sum()
        level1_percentage = level1_value / total_value * 100
        print(f"\n## {level1} (总市值: {level1_value:,.2f}, 占比: {level1_percentage:.2f}%)")
        
        # 按二级分类排序
        for level2, group2 in sorted(group1.groupby('level2'), key=lambda x: x[1]['value'].sum(), reverse=True):
            level2_value = group2['value'].sum()
            level2_percentage = level2_value / total_value * 100
            print(f"\n### {level2} (市值: {level2_value:,.2f}, 占比: {level2_percentage:.2f}%)")
            
            # 按三级分类排序
            for level3, group3 in sorted(group2.groupby('level3'), key=lambda x: x[1]['value'].sum(), reverse=True):
                level3_value = group3['value'].sum()
                level3_percentage = level3_value / total_value * 100
                print(f"\n#### {level3} (市值: {level3_value:,.2f}, 占比: {level3_percentage:.2f}%)")
                
                # 打印该分类下的具体持仓
                print(f"{'名称':<20} {'代码':<10} {'市值':>12} {'占比':>8}")
                print("-" * 60)
                # 按市值排序具体持仓
                sorted_holdings = group3.sort_values('value', ascending=False)
                for _, holding in sorted_holdings.iterrows():
                    holding_percentage = holding['value'] / total_value * 100
                    print(f"{holding['name']:<20} {holding['code']:<10} {holding['value']:>12,.2f} {holding_percentage:>7.2f}%")

    return grouped_df  # 返回处理后的数据，可能对后续处理有用

# 主函数
def generate_portfolio_sunburst(input_data, output_html="portfolio_sunburst.html", print_summary=True, verbose_classify=False):
    """生成投资组合旭日图

    Args:
        input_data: 可以是JSON文件路径或直接的数据字典
        output_html: 输出HTML文件路径，默认为"portfolio_sunburst.html"
        print_summary: 是否打印投资组合摘要数据，默认为True
        verbose_classify: 是否打印详细的分类过程，默认为False

    Returns:
        plotly.graph_objects.Figure: 生成的旭日图对象
    """
    # 创建数据框
    df = create_sunburst_data(input_data, verbose_classify=verbose_classify)

    # 打印投资组合摘要
    if print_summary:
        print_portfolio_summary(df)

    # 绘制并返回旭日图
    fig = plot_sunburst(df, output_html)

    return fig