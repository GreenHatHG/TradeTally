import argparse
import json
import os

from models import InvestmentInfo
from ocr import process_images
from sunburst.sunburst import generate_portfolio_sunburst


def main():
    """整合OCR图像处理和旭日图生成的主函数"""
    parser = argparse.ArgumentParser(description='处理投资组合图片并生成资产配置旭日图')
    parser.add_argument('--image', help='图片路径或包含多张图片的文件夹')
    parser.add_argument('--output_html', default='portfolio_sunburst.html', help='输出HTML文件路径')
    parser.add_argument('--batch', action='store_true', help='批量处理文件夹中的图片')
    parser.add_argument('--channel', choices=['huabao', 'haitong', 'fund_e', 'auto'],
                        default='auto', help='渠道类型: huabao(华宝证券), haitong(海通证券), fund_e(基金e账户) 或 auto(自动检测)')
    parser.add_argument('--save_ocr', default='ocr_result.json', help='保存OCR结果的JSON文件路径')
    parser.add_argument('--use_saved_ocr', action='store_true', help='使用已保存的OCR结果，不重新处理图像')
    parser.add_argument('--cash', type=float, default=0, help='添加现金资产数额（单位：元）')
    parser.add_argument('--cash_name', default='现金', help='现金资产的名称')

    args = parser.parse_args()

    # 尝试使用保存的OCR结果
    use_saved_ocr = args.use_saved_ocr and os.path.exists(args.save_ocr)

    # 如果无法使用保存的结果，检查是否提供了图片路径
    if not use_saved_ocr and not args.image:
        print("错误: 找不到保存的OCR结果文件，且未提供图片路径")
        return

    # 获取OCR结果：从文件加载或处理图像
    if use_saved_ocr:
        print(f"正在加载保存的OCR结果: {args.save_ocr}")
        with open(args.save_ocr, 'r', encoding='utf-8') as f:
            ocr_result = json.load(f)
    else:
        if args.use_saved_ocr and not os.path.exists(args.save_ocr):
            print(f"警告: 找不到保存的OCR结果文件 {args.save_ocr}，将重新进行OCR识别")

        # 调用OCR进行图像处理
        print("正在处理图像并提取投资组合数据...")
        ocr_result = process_images(
            image_path=args.image,
            batch=args.batch,
            channel=args.channel
        )

        # 保存OCR结果到文件
        with open(args.save_ocr, 'w', encoding='utf-8') as f:
            json.dump(ocr_result, f, ensure_ascii=False, indent=2)
        print(f"OCR结果已保存至: {args.save_ocr}")

    # 检查是否成功提取数据
    if not ocr_result or ocr_result['summary']['total_count'] == 0:
        print("无法生成旭日图: 未提取到有效投资数据")
        return

    small_value_items = [x for x in ocr_result['data'] if x['market_value'] <= 100]
    print("过滤市场价值小于或等于100的项目：")
    for item in small_value_items:
        print(item)
    ocr_result['data'] = [x for x in ocr_result['data'] if x['market_value'] > 100]

    # 添加现金资产（如果有指定）
    if args.cash > 0:
        cash_item = InvestmentInfo(name=args.cash_name, market_value=args.cash)
        ocr_result['data'].append(cash_item.to_dict())
        print(f"已添加现金资产: {args.cash_name} {args.cash}元")

    print("正在生成资产配置旭日图...")
    generate_portfolio_sunburst(ocr_result, args.output_html, verbose_classify=False)
    print(f"旭日图已生成: {args.output_html}")

if __name__ == "__main__":
    main()