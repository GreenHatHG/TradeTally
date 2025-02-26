from pprint import pprint

from PIL import Image
from rapidocr_onnxruntime import RapidOCR
import re
import argparse
import os
from datetime import datetime

from parsers.fund_e import parse_fund_data
from parsers.haitong import parse_haitong_stock_data
from parsers.huabao import parse_huabao_stock_data


# 自动检测渠道类型
def detect_channel(lines):
    """自动检测OCR文本渠道类型（华宝证券、海通证券或基金e账户）"""
    # 检查是否包含华宝证券特征
    huabao_features = [
        any(".SH" in line or ".SZ" in line for line in lines),
        any("成本/现价" in line for line in lines),
        any("证券/市值" in line for line in lines),
        any("持仓/可用" in line for line in lines),
        any("华宝" in line for line in lines)
    ]
    
    # 检查是否包含海通证券格式特征
    haitong_features = [
        any("当前持仓" in line for line in lines),
        any("以上是全部" in line for line in lines),
        any("股票/市值" in line for line in lines) or any("持仓/可用" in line for line in lines),
        any("盈亏/盈亏比" in line for line in lines),
        any("海通" in line for line in lines)
    ]
    
    # 检查是否包含基金e账户特征
    fund_e_features = [
        any("持有份额" in line and i+1 < len(lines) and "参考净值" in lines[i+1] for i, line in enumerate(lines)),
        any("筛选" in line for line in lines),
        any(re.search(r'[（\(]\d{6}[）\)]', line) for line in lines),  # 基金代码格式
        any("基金e账户" in line for line in lines)
    ]
    
    # 统计特征匹配数
    huabao_score = sum(huabao_features)
    haitong_score = sum(haitong_features)
    fund_e_score = sum(fund_e_features)
    
    # 根据特征匹配数决定类型
    max_score = max(huabao_score, haitong_score, fund_e_score)
    
    if max_score == huabao_score and huabao_score > 0:
        return "huabao"  # 华宝证券
    elif max_score == haitong_score and haitong_score > 0:
        return "haitong"  # 海通证券
    elif max_score == fund_e_score and fund_e_score > 0:
        return "fund_e"  # 基金e账户
    else:
        # 如果无法确定，检查更多特定特征
        if any("持仓" in line for line in lines) and any("盈亏" in line for line in lines):
            # 进一步区分华宝和海通
            if any("以上是全部" in line for line in lines):
                return "haitong"
            else:
                return "huabao"
        elif any("资产情况" in line for line in lines):
            return "fund_e"
        else:
            return None  # 无法确定渠道

def process_image(image_path, channel='auto'):
    """处理单个图片"""
    try:
        # 检查图片尺寸
        img = Image.open(image_path)
        width, height = img.size
        max_side = max(width, height)
        
        # 仅根据图片尺寸决定OCR引擎配置
        if max_side > 5000:
            print(f"使用大图片模式进行OCR (尺寸: {width}x{height})")
            engine = RapidOCR(max_side_len=100000)
        else:
            print(f"使用普通模式进行OCR (尺寸: {width}x{height})")
            engine = RapidOCR()
        
        # OCR识别
        ocr_result, _ = engine(image_path)
        if not ocr_result:
            print(f"图片 {image_path} OCR识别失败或无文本")
            return None, None
        
        text_lines = [x[1] for x in ocr_result]
        
        # 自动检测渠道
        if channel == 'auto':
            detected_channel = detect_channel(text_lines)
            if not detected_channel:
                print(f"无法确定图片 {image_path} 的渠道")
                return None, None
            channel = detected_channel
        
        # 根据渠道解析数据
        if channel == 'huabao':
            parsed_data = parse_huabao_stock_data(text_lines)
        elif channel == 'haitong':
            parsed_data = parse_haitong_stock_data(ocr_result)
        else:  # channel == 'fund_e'
            parsed_data = parse_fund_data(text_lines)
        
        return channel, parsed_data
    except Exception as e:
        print(f"处理图片 {image_path} 时出错: {str(e)}")
        return None, None

def process_images(image_path, batch=False, channel='auto'):
    """
    API函数：处理图像并返回结果数据
    
    参数:
        image_path: 图片路径或文件夹
        batch: 是否批量处理
        channel: 渠道类型
        
    返回:
        解析后的投资组合数据
    """
    # 创建统一的返回结果结构
    result = {
        'data': [],  # 统一数据存储键
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'sources': [],
        'summary': {
            'total_count': 0
        }
    }
    
    # 检查图片路径是否存在
    if not os.path.exists(image_path):
        print(f"错误: 路径不存在 {image_path}")
        return result
    
    # 存储原始channel参数
    original_channel = channel
    
    # 处理批量模式
    if batch or os.path.isdir(image_path):
        if not os.path.isdir(image_path):
            print(f"错误: 批量处理需要指定文件夹路径")
            return result
        
        image_files = [f for f in os.listdir(image_path) 
                      if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))]
        
        if not image_files:
            print(f"文件夹 {image_path} 中没有找到图片文件")
            return result
        
        print(f"开始批量处理 {len(image_files)} 张图片...")
        
        for img_file in image_files:
            img_path = os.path.join(image_path, img_file)
            print(f"处理图片: {img_file}")
            
            # 使用不同的变量名接收返回值
            detected_channel, parsed_data = process_image(img_path, original_channel)
            
            if detected_channel and parsed_data:
                # 为每条数据添加来源标识并添加到统一数据中
                for item in parsed_data:
                    item['source_type'] = detected_channel
                    result['data'].append(item)
                result['sources'].append(img_file)
                print(f"  - 解析了 {len(parsed_data)} 条{detected_channel}数据")
            else:
                print(f"  - 跳过 {img_file}")
        
        # 动态生成汇总信息
        generate_summary(result)
        
        print(f"\n批量处理完成:")
        for source_type, count in result['summary'].items():
            if source_type != 'total_count':
                print(f"- {source_type}数据: {count} 条")
        
        return result
    
    # 单文件处理模式
    else:
        print(f"处理图片: {image_path}")
        detected_channel, parsed_data = process_image(image_path, original_channel)
        
        if detected_channel and parsed_data:
            file_name = os.path.basename(image_path)
            # 为每条数据添加来源标识并添加到统一数据中
            for item in parsed_data:
                item['source_type'] = detected_channel
                result['data'].append(item)
            result['sources'].append(file_name)
            
            # 动态生成汇总信息
            generate_summary(result)
            
            print(f"成功解析 {len(parsed_data)} 条{detected_channel}数据")
            
            return result
        else:
            print("处理失败")
            return result

def generate_summary(result):
    """根据data动态生成汇总信息"""
    # 初始化汇总信息
    summary = {'total_count': len(result['data'])}
    
    # 按来源类型统计数量
    source_counts = {}
    for item in result['data']:
        source_type = item['source_type']
        source_counts[source_type] = source_counts.get(source_type, 0) + 1
    
    # 更新汇总信息
    summary.update({f"{source}_count": count for source, count in source_counts.items()})
    
    # 更新结果中的汇总信息
    result['summary'] = summary

def main(args=None):
    if args is None:
        parser = argparse.ArgumentParser(description='解析股票和基金持仓截图')
        parser.add_argument('--channel', choices=['huabao', 'haitong', 'fund_e', 'auto'], default='auto', 
                            help='渠道类型: huabao(华宝证券), haitong(海通证券), fund_e(基金e账户) 或 auto(自动检测)')
        parser.add_argument('--image', required=True, help='图片路径或包含多张图片的文件夹')
        parser.add_argument('--output', help='输出JSON文件路径')
        parser.add_argument('--batch', action='store_true', help='批量处理文件夹中的图片')
        
        args = parser.parse_args()
    
    # 调用API函数
    result = process_images(
        image_path=args.image,
        batch=args.batch,
        channel=args.channel
    )
    
    return result

if __name__ == "__main__":
    result = main()
    pprint(result)
