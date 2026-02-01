# 获取股票数据的代码演示
# 参考 https://zhuanlan.zhihu.com/p/646740687

import warnings

import qlib
from qlib.config import REG_CN
from qlib.data import D
from qlib.data.filter import ExpressionDFilter, NameDFilter

if __name__ == '__main__':
	warnings.filterwarnings('ignore')

	# 初始化
	qlib.init(provider_uri='~/.qlib/qlib_data/cn_data', region=REG_CN)

	# 1. 加载给定时间范围和频率(day,min,week,month)的交易日历
	# 1.1. 获取 2025 年的所有交易日
	cal_2025 = D.calendar(start_time='2025-01-01', end_time='2025-12-31', freq='day')
	print('-' * 50)
	print(f'2025年共有 {len(cal_2025)} 个交易日')
	print(f'前3天: {cal_2025[:3]}')

	# 1.2. 包含未来日期（常用于生成预测用的索引）
	cal_future = D.calendar(start_time='2026-01-30', freq='day', future=True)
	print(f'未来3天: {cal_future[:3]}')

	# --------------------------------
	# 2. 将给定的市场名称解析为股票池
	# market = ['all', 'csi300', 'csi500', 'csi800', 'csi1000', 'csiall']
	# 2.1. 获取市场所有股票代码
	instruments = D.instruments(market='all')
	ins_2025 = D.list_instruments(instruments=instruments, start_time='2025-01-01', end_time='2025-12-31', as_list=True)
	print('-' * 50)
	print(f'2025年市场共有 {len(ins_2025)} 只股票')
	print(f'前6只股票: {ins_2025[:6]}')
	print(f'后6只股票: {ins_2025[-6:]}')

	# 2.2. 加载csi300特定股票池的所有股票代码
	instruments = D.instruments(market='csi300')
	ins_csi300 = D.list_instruments(instruments=instruments, start_time='2025-01-01', end_time='2025-12-31', as_list=True)
	print('-' * 50)
	print(f'2025年沪深300指数共有 {len(ins_csi300)} 只股票')
	print(f'前6只股票: {ins_csi300[:6]}')
	print(f'后6只股票: {ins_csi300[-6:]}')

	# 2.3. 加载csi800特定股票池的所有股票代码
	instruments = D.instruments(market='csi800')
	ins_csi300 = D.list_instruments(instruments=instruments, start_time='2025-01-01', end_time='2025-12-31', as_list=True)
	print('-' * 50)
	print(f'2025年沪深800指数共有 {len(ins_csi300)} 只股票')
	print(f'前6只股票: {ins_csi300[:6]}')
	print(f'后6只股票: {ins_csi300[-6:]}')

	# --------------------------------
	# 3. NameDFilter按照正则表达式编写, 筛选出csi300里所有以8结尾的股票
	nameDFilter = NameDFilter(name_rule_re='SH[0-9]{5}8')
	instruments = D.instruments(market='csi300', filter_pipe=[nameDFilter])
	ins_name = D.list_instruments(instruments=instruments, start_time='2025-01-01', end_time='2025-12-31', as_list=True)
	print('-' * 50)
	print(f"2025年沪深300指数共有 {len(ins_name)} 只股票代码结尾为'8'")
	print(f'前6只股票: {ins_name[:6]}')
	print(f'后6只股票: {ins_name[-6:]}')

	# --------------------------------
	# 4. 按条件表达式方式过滤(具体的字段设置动态条件),筛选出csi300里所有收盘价格大于70的股票
	expressionDFilter = ExpressionDFilter(rule_expression='$close>70')
	# 基本功能过滤器:   rule_expression = '$close/$open>5'
	# 横截面特征过滤器: rule_expression = '$rank（$close）<10'
	# 时序特征过滤器:   rule_expression = '$Ref（$close， 3）>100'

	instruments = D.instruments(
		market='csi300',
		filter_pipe=[expressionDFilter],
	)
	ins_expression = D.list_instruments(instruments=instruments, start_time='2025-01-01', end_time='2025-12-31', as_list=True)
	print('-' * 50)
	print(f'2025年沪深300指数共有 {len(ins_expression)} 只股票收盘价格大于70元')
	print(f'前6只股票: {ins_expression[:6]}')
	print(f'后6只股票: {ins_expression[-6:]}')

	# --------------------------------
	# 5. 按自定义特征获取符合条件的数据
	# 5.1 基本用法
	fields = ['$open', '$close', '$low', '$high', '$volume']
	ins_df = D.features(instruments=['SH600000'], fields=fields, start_time='2025-01-01', end_time='2025-12-31', freq='day')
	print('-' * 50)
	print(f"2025年股票代码 'SH600000' 符合基本特征数据 共有 {len(ins_df)} 条数据")
	print(f'前6条数据: {ins_df[:6]}')
	print(f'后6条数据: {ins_df[-6:]}')

	# 5.2 扩展用法
	# Ref($close, 1) = 昨日收盘价
	# 当日涨跌幅 (Return)  = ($close / Ref($close, 1)) - 1 或  ($close - Ref($close, 1)) / Ref($close, 1) 未验证
	# 3日收盘价均值        = Mean($close, 3)
	# 跳空缺口 (Gap)      = $open > Ref($close, 1)
	# 今日最高价-今日最低价 = $high-$low
	# 收阳或上涨           = $close>Ref($close,1)
	# 跳空高开            = $open > Ref($close, 1) （今日开盘价 > 昨日收盘价）
	# ##### 判断 Mean($close, 3) > Mean($close, 10) 来识别金叉趋势
	# ##### 判断 Mean($close, 3) < Mean($close, 10) 来识别死叉趋势
	# ##### 构造偏离度指标, 例如 ($close / Mean($close, 3)) - 1，用于衡量价格是否短期超涨或超跌
	# ##### 构造波动率指标, 例如 ($high-$low) / Mean($close, 3)，用于衡量价格波动范围
	fields = ['$close', '$volume', 'Ref($close, 1)', 'Mean($close, 3)', '$high-$low']
	ins_df = D.features(instruments=['SH600000'], fields=fields, start_time='2025-01-01', end_time='2025-12-31', freq='day')
	print('-' * 50)
	print(f"2025年股票代码 'SH600000' 符合扩展用法特征数据 共有 {len(ins_df)} 条数据")
	print(f'前6条数据: {ins_df[:6]}')
	print(f'后6条数据: {ins_df[-6:]}')

	# 5.3 组合用法, 按NameDFilter和ExpressionDFilter过滤器且输出自定义特征数据
	nameDFilter = NameDFilter(name_rule_re='SH[0-9]{5}8')
	expressionDFilter = ExpressionDFilter(rule_expression='$close>Ref($close,1)')  # 判断当日收盘价是否高于前一交易日的收盘价
	instruments = D.instruments(market='csi300', filter_pipe=[nameDFilter, expressionDFilter])
	fields = ['$close', '$volume', 'Ref($close, 1)', 'Mean($close, 3)', '$high-$low']
	ins_df = D.features(instruments, fields, start_time='2025-01-01', end_time='2025-12-31', freq='day')
	print('-' * 50)
	print(f"2025年沪深300指数共有 {len(ins_df)} 条交易记录中股票代码结尾为'8',且符合组合用法特征数据(上涨)")
	print(f'前6条数据: {ins_df[:6]}')
	print(f'后6条数据: {ins_df[-6:]}')
