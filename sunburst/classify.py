# 默认分类规则
import re

DEFAULT_CLASSIFICATION_RULES = {
    "rules": [
        # 其他特殊分类，提前匹配
        {"keywords": ["兴全合润", '交银施罗德定期支付双息平衡'], "match_any": True, "category": ["A股", "主动基金", "混合"]},
        
        # A股行业主题
        {"keywords": ["医疗", "中证医疗", "医药", "医药卫生", "大摩健康产业混合", '中证生物科技', '融通健康'],
         "match_any": True,
         "exclude": ["恒生", "海外", "全球"],
         "category": ["A股", "行业", "医药"]},
        {"keywords": ["环保"], "category": ["A股", "行业", "环保"]},
        {"keywords": ["养老"], "category": ["A股", "行业", "养老"]},
        {"keywords": ["消费", "食品饮料", '文体娱乐'],
         "exclude": ["恒生", "海外", "全球"],
         "match_any": True, "category": ["A股", "行业", "消费"]},
        {"keywords": ["信息", "信息技术"], "match_any": True, "category": ["A股", "行业", "信息"]},
        {"keywords": ["农业"], "category": ["A股", "行业", "农业"]},
        
        # 能源相关
        {"exact_match": ["国投电力", "盐湖股份", "淮北矿业"], "category": ["A股", "行业", "能源"]},
        {"keywords": ["能源", "电力"], 
         "match_any": True,
         "exclude": ["恒生", "海外", "全球"],
         "category": ["A股", "行业", "能源"]},

        # 红利分类规则
        {"keywords": ["红利"], "and_keywords": ["恒生", "港股", "央企"],
         "category": ["海外新兴", "策略", "红利"]},
        {"keywords": ["红利"],
         "exclude": ["恒生", "港股", "央企"],
         "category": ["A股", "策略", "红利"]},
        {"keywords": ["500行业中性低波动指"],
         "category": ["A股", "策略", "500低波动"]},

        # 海外分类规则 - 香港市场
        {"keywords": ["恒生科技"], "category": ["海外新兴", "海外科技", "恒生科技"]},
        {"keywords": ["恒生医疗", "博时恒生医疗"], "match_any": True, "category": ["海外新兴", "海外医疗", "恒生医疗"]},
        {"keywords": ["恒生消费"], "category": ["海外新兴", "香港", "恒生消费"]},
        {"keywords": ["恒生"], 
         "exclude": ["科技", "医疗", "消费", "红利"],
         "category": ["海外新兴", "香港", "恒生"]},

        # 海外分类规则 - 成熟市场
        {"keywords": ["全球医疗"], "match_any": True, "category": ["海外成熟", "全球", "全球医疗"]},

        # 海外互联网
        {"keywords": ["互联网", "中概"], "match_any": True, "category": ["海外新兴", "海外科技", "海外互联"]},

        # 证券行业
        {"keywords": ["证券", "非银"], "match_any": True, "and_keywords": ["港股"],
         "category": ["海外新兴", "行业", "非银"]},
        {"keywords": ["证券", "非银"], "match_any": True, "category": ["A股", "行业", "证券"]},

        # A股分类规则 - 宽基指数
        {"keywords": ["500", "中证500"], "match_any": True, "category": ["A股", "中小盘", "500"]},
        {"keywords": ["300", "沪深300"], "match_any": True, "category": ["A股", "大盘", "300"]},
        {"keywords": ["创业板"], "category": ["A股", "中小盘", "创业板"]},

        # 其他分类
        {"keywords": ["债"], "and_keywords": ["国开债"], "category": ["债券", "国内债券", "纯债"]},
        {"keywords": ["债"], "category": ["债券", "美债", "超长期债券"]},
        {"regex": r"货币|添益|宝货币|现金|天添宝|添利宝", "category": ["货币", "货币", "货币"]},

        # 默认分类
        {"default": True, "category": ["其他", "其他", "其他"]}
    ]
}

# 改进的股票/基金分类映射函数
def classify_holding(name, code=None, rules=None, verbose=False):
    """
    根据名称和代码判断持仓项的分类

    Args:
        name: 持仓项名称
        code: 持仓项代码
        rules: 分类规则，如果为None则使用默认规则
        verbose: 是否打印详细的分类过程信息

    Returns:
        tuple: (一级分类, 二级分类, 三级分类)
    """
    if rules is None:
        rules = DEFAULT_CLASSIFICATION_RULES["rules"]
    
    if verbose:
        print(f"\n正在分类: {name} (代码: {code if code else '无'})")
    
    for rule in rules:
        # 精确匹配
        if "exact_match" in rule and name in rule["exact_match"]:
            if verbose:
                print(f"  √ 精确匹配成功: {name} 匹配规则 {rule['exact_match']}")
            return tuple(rule["category"])

        # 关键词匹配
        if "keywords" in rule:
            keywords = rule["keywords"]
            # 使用any或all根据match_any参数决定匹配逻辑
            if rule.get("match_any", False):
                keywords_match = any(kw in name for kw in keywords)
                if verbose and keywords_match:
                    matched = [kw for kw in keywords if kw in name]
                    print(f"  - 关键词匹配(任一): 找到 {matched}")
            else:
                keywords_match = all(kw in name for kw in keywords)
                if verbose:
                    matched = [kw for kw in keywords if kw in name]
                    not_matched = [kw for kw in keywords if kw not in name]
                    if matched:
                        print(f"  - 关键词匹配: 找到 {matched}")
                    if not_matched:
                        print(f"  - 关键词不匹配: {not_matched}")
            
            # 必须同时包含的关键词
            if "and_keywords" in rule:
                and_keywords = rule["and_keywords"]
                and_match = any(kw in name for kw in and_keywords)
                
                if verbose:
                    matched_and = [kw for kw in and_keywords if kw in name]
                    if matched_and:
                        print(f"  - AND关键词匹配: 找到 {matched_and}")
                    else:
                        print(f"  - AND关键词不匹配: 需要 {and_keywords} 中的至少一个")
                
                if keywords_match and and_match:
                    if verbose:
                        print(f"  √ 规则匹配成功: 关键词匹配 和 AND关键词匹配")
                    return tuple(rule["category"])
                    
            # 必须排除的关键词
            elif "exclude" in rule:
                exclude_keywords = rule["exclude"]
                exclude_match = any(kw in name for kw in exclude_keywords)
                
                if verbose:
                    if exclude_match:
                        matched_exclude = [kw for kw in exclude_keywords if kw in name]
                        print(f"  - 排除关键词匹配: 找到 {matched_exclude}，将被排除")
                    else:
                        print(f"  - 排除关键词检查通过: 未找到 {exclude_keywords} 中的任何一个")
                
                if keywords_match and not exclude_match:
                    if verbose:
                        print(f"  √ 规则匹配成功: 关键词匹配且不包含排除词")
                    return tuple(rule["category"])
                    
            # 普通关键词匹配
            elif keywords_match:
                if verbose:
                    print(f"  √ 规则匹配成功: 关键词匹配")
                return tuple(rule["category"])

        # 正则表达式匹配
        if "regex" in rule and re.search(rule["regex"], name):
            if verbose:
                print(f"  √ 正则表达式匹配成功: {name} 匹配正则 {rule['regex']}")
            return tuple(rule["category"])

        # 默认规则
        if rule.get("default", False):
            if verbose:
                print(f"  √ 使用默认规则")
            return tuple(rule["category"])

    # 兜底返回
    if verbose:
        print(f"  ! 未找到匹配规则，使用兜底分类")
    return ("其他", "其他", "其他")
