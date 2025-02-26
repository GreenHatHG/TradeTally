# 统一的投资信息类
class InvestmentInfo:
    def __init__(self, name=None, code=None, quantity=None, market_value=None, 
                 cost_price=None, current_price=None, position_ratio=None, 
                 profit_ratio=None, profit_amount=None):
        # 通用字段
        self.name = name      # 名称
        self.code = code      # 代码
        self.quantity = quantity  # 持有数量/份额
        self.market_value = market_value  # 市值/资产情况
        self.cost_price = cost_price    # 成本价
        self.current_price = current_price # 现价/净值
        self.position_ratio = position_ratio  # 持仓比例
        self.profit_ratio = profit_ratio  # 盈亏比例
        self.profit_amount = profit_amount  # 盈亏金额

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items() if v is not None}
